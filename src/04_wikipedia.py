import hashlib
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pandas as pd
import requests
from babel.languages import get_territory_language_info

sys.dont_write_bytecode = True
sys.path.append("analysis")
from common import load

DUMP = Path("data/raw/musicbrainz/dump/artist.tar.xz")
CACHE = Path("data/raw/wikipedia")
OUT = Path("data/processed")
WIKIDATA = "https://www.wikidata.org/w/api.php"
USER_AGENT = "FestivalNetworkReach/1.0 (DTU 02805; https://github.com/miranda-dsc/02805-festival-network)"
PAUSE = 0.3
RETRIES = 6
ENTITY_BATCH = 50
EXTRACT_BATCH = 20
WIKI_LANGUAGE = {"gsw": "als", "fil": "tl", "nb": "no"}
LANGUAGE_STATUS = {"official": 3, "de_facto_official": 2, "official_regional": 1}
SESSION = requests.Session()
SESSION.headers["User-Agent"] = USER_AGENT


def save_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def fetch(url, **params):
    params.update(format="json", maxlag=5)
    key = hashlib.sha256(json.dumps([url, params], sort_keys=True).encode()).hexdigest()
    path = CACHE / f"{params['action']}-{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    for attempt in range(RETRIES):
        time.sleep(PAUSE)
        delay = 2 ** attempt
        try:
            response = SESSION.get(url, params=params, timeout=45)
            retry_after = response.headers.get("Retry-After", "")
            if retry_after.isdigit():
                delay = max(delay, int(retry_after))
            response.raise_for_status()
            value = response.json()
            if "error" not in value:
                save_json(path, value)
                return value
            error = value["error"]
            if error["code"] not in {"maxlag", "ratelimited", "readonly"}:
                raise RuntimeError(f"{url}: {error}")
        except requests.HTTPError as error:
            if error.response.status_code not in {429, 500, 502, 503, 504}:
                raise
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.JSONDecodeError):
            pass
        if attempt + 1 < RETRIES:
            time.sleep(delay)
    raise RuntimeError(f"{url}: request failed after {RETRIES} tries ({params['action']})")


def batches(values, size):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def dump_links(ids):
    signature = [DUMP.stat().st_size, DUMP.stat().st_mtime_ns,
                 hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()]
    path = CACHE / "artist_links.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved["signature"] == signature:
            return saved["links"]

    links = {}
    n = 0
    with subprocess.Popen(["tar", "-xJOf", str(DUMP), "mbdump/artist"],
                          stdout=subprocess.PIPE) as tar:
        for n, line in enumerate(tar.stdout, 1):
            if n % 100_000 == 0:
                print(f"{n:,} artists read", flush=True)
            artist = json.loads(line)
            if artist["id"] not in ids:
                continue
            urls = defaultdict(list)
            for rel in artist.get("relations") or []:
                if rel.get("target-type") == "url" and rel["type"] in {"wikidata", "wikipedia"}:
                    urls[rel["type"]].append(rel["url"]["resource"])
            qids = sorted({match.group() for url in urls["wikidata"]
                           if (match := re.search(r"\bQ[1-9]\d*\b", url))})
            links[artist["id"]] = {"qids": qids, "wikipedia": sorted(set(urls["wikipedia"]))}
        if tar.wait():
            raise RuntimeError(f"Could not stream {DUMP}")
    print(f"{n:,} artists read", flush=True)
    save_json(path, {"signature": signature, "links": links})
    return links


def scope():
    lineups, _ = load()
    festivals = lineups.groupby("act_key")["festival"].nunique()
    matches = pd.read_csv(OUT / "act_matches.csv", keep_default_na=False)
    return matches.loc[matches["act_key"].isin(festivals[festivals.ge(2)].index)
                       & matches["mbid"].ne("")].copy()


def wiki_sites():
    matrix = fetch(WIKIDATA, action="sitematrix", smtype="language",
                   smlangprop="site", smsiteprop="dbname|url")["sitematrix"]
    return {site["dbname"]: urlsplit(site["url"]).hostname.split(".")[0]
            for key, language in matrix.items() if key.isdigit()
            for site in language["site"]
            if site["dbname"].endswith("wiki") and site["url"].endswith(".wikipedia.org")
            and "closed" not in site}


def sitelinks(qids, sites):
    links = {}
    for batch in batches(sorted(qids), ENTITY_BATCH):
        result = fetch(WIKIDATA, action="wbgetentities", ids="|".join(batch),
                       props="sitelinks", redirects="yes")
        for qid in batch:
            entity = result["entities"][qid]
            links[qid] = {sites[site]: link["title"]
                          for site, link in entity.get("sitelinks", {}).items() if site in sites}
    return links


def direct_titles(urls, sites):
    for url in urls:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").replace(".m.wikipedia.org", ".wikipedia.org")
        lang = host.removesuffix(".wikipedia.org")
        if host == f"{lang}.wikipedia.org" and lang in sites and parsed.path.startswith("/wiki/"):
            yield lang, unquote(parsed.path[len("/wiki/"):]).replace("_", " ")


def extracts(titles, lang):
    pages = {}
    for batch in batches(sorted(titles), EXTRACT_BATCH):
        params = dict(action="query", prop="extracts|pageprops", exintro=1, explaintext=1,
                      exlimit=EXTRACT_BATCH, titles="|".join(batch), redirects=1,
                      ppprop="disambiguation", formatversion=2)
        continuation = {}
        aliases = {}
        resolved = {}
        while True:
            result = fetch(f"https://{lang}.wikipedia.org/w/api.php", **params, **continuation)
            query = result["query"]
            for entry in query.get("normalized", []) + query.get("redirects", []):
                aliases[entry["from"]] = entry["to"]
            for page in query["pages"]:
                if page.get("ns") == 0 and "missing" not in page and "disambiguation" not in page.get("pageprops", {}):
                    lead = page.get("extract", "").strip()
                    paragraph = re.split(r"\n\s*\n|\n", lead, maxsplit=1)[0]
                    resolved[page["title"]] = paragraph or resolved.get(page["title"], "")
            continuation = result.get("continue", {})
            if not continuation:
                break
        for title in batch:
            target = title
            seen = set()
            while target in aliases and target not in seen:
                seen.add(target)
                target = aliases[target]
            if target in resolved:
                pages[title] = resolved[target]
    return pages


def article_choices(titles, country):
    if "en" in titles:
        return "en"
    languages = get_territory_language_info(country)
    local = sorted(languages, key=lambda lang: (
        -LANGUAGE_STATUS.get(languages[lang].get("official_status"), 0),
        -languages[lang].get("population_percent", 0), lang))
    official = [lang for lang in local if languages[lang].get("official_status") in LANGUAGE_STATUS]
    local = [WIKI_LANGUAGE.get(lang, lang.split("_")[0]) for lang in official or local[:1]]
    return next((lang for lang in local if lang in titles), "")


def reach_rows(acts, artists):
    acts["qids"] = acts["mbid"].map(lambda mbid: artists.get(mbid, {}).get("qids", []))
    acts["direct"] = acts["mbid"].map(lambda mbid: artists.get(mbid, {}).get("wikipedia", []))
    multiple = acts["qids"].str.len().gt(1)
    acts["qid"] = acts["qids"].map(lambda ids: ids[0] if len(ids) == 1 else "")
    print(f"{acts['qid'].ne('').sum():,} acts with one Q-id, {multiple.sum():,} with multiple Q-ids",
          flush=True)
    print(f"{acts['direct'].str.len().gt(0).sum():,} acts with a direct Wikipedia URL", flush=True)
    sites = wiki_sites()
    links = sitelinks(set(acts.loc[acts["qid"].ne(""), "qid"]), sites)
    print(f"{len(links):,} unique Q-ids queried, {sum(bool(titles) for titles in links.values()):,} with language sitelinks",
          flush=True)

    titles_by_act = {}
    direct_queries = defaultdict(set)
    for act in acts.itertuples():
        titles = links.get(act.qid, {}).copy()
        direct = list(direct_titles(act.direct, sites.values())) if not titles else []
        for lang, title in direct:
            direct_queries[lang].add(title)
        titles_by_act[act.act_key] = (titles, direct)

    direct_pages = {lang: extracts(titles, lang) for lang, titles in sorted(direct_queries.items())}
    rows = []
    fallback = 0
    for act in acts.itertuples():
        titles, direct = titles_by_act[act.act_key]
        for lang, title in direct:
            if title in direct_pages[lang]:
                titles.setdefault(lang, title)
        fallback += bool(direct and titles)
        intro_lang = article_choices(titles, act.country)
        title = titles.get(intro_lang, "")
        rows.append(dict(act_key=act.act_key, mbid=act.mbid, qid=act.qid,
                         n_languages=len(titles), has_en="en" in titles,
                         langs=";".join(sorted(titles)), intro_lang=intro_lang, intro=title))
    print(f"{fallback:,} acts with reach from verified direct Wikipedia URLs", flush=True)
    return rows, direct_pages


def fill_leads(rows, direct_pages):
    queries = defaultdict(set)
    for row in rows:
        if row["intro_lang"]:
            queries[row["intro_lang"]].add(row["intro"])
    leads = {}
    for lang, titles in sorted(queries.items()):
        direct = direct_pages.get(lang, {})
        leads[lang] = direct | extracts(titles - direct.keys(), lang)
        print(f"{lang}: {sum(bool(leads[lang].get(title)) for title in titles):,} of {len(titles):,} leads",
              flush=True)

    for row in rows:
        row["intro"] = leads.get(row["intro_lang"], {}).get(row["intro"], "")
        if not row["intro"]:
            row["intro_lang"] = ""


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    acts = scope()
    print(f"{len(acts):,} matched acts at 2 or more festivals", flush=True)
    print(acts["method"].value_counts().to_string(), flush=True)
    artists = dump_links(set(acts["mbid"]))
    print(f"{len(artists):,} of {acts['mbid'].nunique():,} unique matched MBIDs found in the dump",
          flush=True)
    rows, direct_pages = reach_rows(acts, artists)
    fill_leads(rows, direct_pages)
    result = pd.DataFrame(rows)
    temporary = CACHE / "act_wiki.tmp"
    result.to_csv(temporary, index=False)
    temporary.replace(OUT / "act_wiki.csv")
    print(f"{len(result):,} rows, {result['n_languages'].gt(0).sum():,} with articles, "
          f"{result['has_en'].sum():,} with English, {result['intro'].ne('').sum():,} with an intro",
          flush=True)


if __name__ == "__main__":
    main()
