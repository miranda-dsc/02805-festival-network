import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.append("analysis")
from common import load

CACHE = Path("data/raw/musicbrainz/acts.json")
OUT = Path("data/processed/act_tags.csv")
BASE = "https://musicbrainz.org/ws/2/artist"
HEADERS = {"User-Agent": "DTU-02805-festival-project/1.0 (gmaglehoej3@gmail.com)"}
MBID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
COLUMNS = ["act_key", "act", "mbid", "matched_name", "match_method", "score_100_hits",
           "country", "disambiguation", "tag", "tag_count", "genre_count"]


def save():
    temp = CACHE.with_suffix(".tmp")
    temp.write_text(json.dumps(results, ensure_ascii=True), encoding="utf-8")
    temp.replace(CACHE)


def get(mbid="", **params):
    delay = 5
    while True:
        time.sleep(1.1)
        response = session.get(f"{BASE}/{mbid}" if mbid else BASE,
                               params={"fmt": "json", **params}, timeout=30)
        if response.status_code in (503, 429):
            print(f"HTTP {response.status_code}: retry in {delay}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 300)
        else:
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()


parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, help="process only the first n eligible acts")
args = parser.parse_args()
if args.limit is not None and args.limit < 1:
    parser.error("--limit must be positive")
lineups, editions = load()
n_festivals = lineups.groupby("act_key")["festival"].nunique()
keys = n_festivals[n_festivals >= 2].index
print(f"Eligible: {len(keys)} acts across at least two festivals", flush=True)
CACHE.parent.mkdir(parents=True, exist_ok=True)
results = json.loads(CACHE.read_text()) if CACHE.exists() else {}
results = {key: r for key, r in results.items() if key in keys and "status" not in r}
print(f"Cached: {len(results)} acts", flush=True)
session = requests.Session()
session.headers.update(HEADERS)
groups = lineups.groupby("act_key")
processed = 0
try:
    for key in keys[:args.limit]:
        if key in results:
            continue
        rows = groups.get_group(key)
        name = rows["act"].value_counts().index[0].strip()
        clean = re.sub(r"\s+(?:-\s*)?[\[(]?(?:live|dj\s+set)[\])]?$", "", name, flags=re.I)
        ids = rows["mbid"].dropna().str.strip().str.lower()
        ids = sorted(ids[ids.str.fullmatch(MBID)].unique())
        r = dict(name=name, matched=False, mbid=None, matched_name=None, match_method="unmatched",
                 score_100_hits=0, clashfinder_mbids=ids, candidates=[], country=None,
                 disambiguation="", tags=[], genres=[])
        mid = None
        if len(ids) > 1:
            r["match_method"] = "conflicting"
        elif ids:
            mid, r["match_method"] = ids[0], "clashfinder id"
        else:
            query = clean.replace("\\", "\\\\").replace('"', '\\"')
            hits = get(query=f'artist:"{query}"', limit=5).get("artists", [])
            perfect = [hit for hit in hits if int(hit.get("score", 0)) == 100]
            r["score_100_hits"] = len(perfect)
            if len(perfect) > 1:
                r["match_method"] = "ambiguous"
                r["candidates"] = [{field: hit.get(field) for field in
                                    ("id", "name", "country", "disambiguation")} for hit in perfect]
            elif hits and int(hits[0].get("score", 0)) == 100 and hits[0]["name"].casefold() in (name.casefold(), clean.casefold()):
                mid, r["match_method"] = hits[0]["id"], "search"
        if mid:
            data = get(mid, inc="tags+genres")
            if data:
                r.update(matched=True, mbid=data["id"], matched_name=data["name"], country=data.get("country"),
                         disambiguation=data.get("disambiguation", ""), tags=data.get("tags") or [], genres=data.get("genres") or [])
            else:
                r["match_method"] = "unmatched"
        results[key] = r
        processed += 1
        if processed % 50 == 0:
            save()
            print(f"Cached: {len(results)}/{len(keys)} acts", flush=True)
finally:
    save()
    session.close()
    tags = []
    for key, r in results.items():
        tag_counts = {tag["name"]: tag["count"] for tag in r["tags"]}
        genre_counts = {tag["name"]: tag["count"] for tag in r["genres"]}
        for tag in sorted(tag_counts.keys() | genre_counts.keys()):
            tags.append(dict(act_key=key, act=r["name"], **{c: r[c] for c in COLUMNS[2:8]},
                             tag=tag, tag_count=tag_counts.get(tag), genre_count=genre_counts.get(tag)))
    pd.DataFrame(tags, columns=COLUMNS).to_csv(OUT, index=False)
    print(f"Completed: {len(results)}/{len(keys)} acts; saved {len(tags)} act-tag rows", flush=True)
    for method in ("clashfinder id", "search", "unmatched", "ambiguous", "conflicting"):
        print(f"{method}: {sum(r['match_method'] == method for r in results.values())}", flush=True)
    print(f"With at least one tag: {sum(bool(r['tags']) for r in results.values())}", flush=True)
