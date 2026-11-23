import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.append("analysis")
from common import load

DUMP = Path("data/raw/musicbrainz/dump/artist.tar.xz")
OUT = Path("data/processed")
MIN_FESTIVALS = 1
MIN_VOTES = 3  # ambiguous picks with fewer votes were mostly wrong in the hand check
MBID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"


def act_key(name: str) -> str:
    """same key as in 02_clean_lineups.py"""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    without_brackets = re.sub(r"\(.*?\)|\[.*?\]", " ", text)
    if re.search(r"[a-z0-9]", without_brackets):
        text = without_brackets
    text = re.sub(r"\s+(dj set|live set|live|dj)$", "", text.strip())
    text = re.sub(r"^the\s+", "", text.strip())
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


lineups, editions = load()
n_festivals = lineups.groupby("act_key")["festival"].nunique()
keys = set(n_festivals[n_festivals >= MIN_FESTIVALS].index)
ids = lineups[lineups["act_key"].isin(keys)].dropna(subset=["mbid"])
ids = ids[ids["mbid"].str.lower().str.fullmatch(MBID)]
clash_ids = ids.groupby("act_key")["mbid"].agg(lambda m: sorted(set(m.str.lower())))
print(f"Eligible: {len(keys)} acts, {len(clash_ids)} with a Clashfinder id")

# one pass over the dump, keep artists whose name or alias gives an eligible key
wanted_ids = {i for v in clash_ids for i in v}
artists = {}
candidates = {}
tar = subprocess.Popen(["tar", "-xJOf", str(DUMP), "mbdump/artist"], stdout=subprocess.PIPE)
for n, line in enumerate(tar.stdout):
    if n % 500000 == 0:
        print(f"{n} artists read", flush=True)
    a = json.loads(line)
    names = [a["name"]] + [alias["name"] for alias in a.get("aliases") or []]
    hits = {act_key(x) for x in names} & keys
    if not hits and a["id"] not in wanted_ids:
        continue
    artists[a["id"]] = {
        "name": a["name"],
        "country": a.get("country"),
        "disambiguation": a.get("disambiguation", ""),
        "tags": {t["name"]: t["count"] for t in a.get("tags") or []},
        "genres": {g["name"]: g["count"] for g in a.get("genres") or []},
        "votes": sum(t["count"] for t in a.get("tags") or []) + (a.get("rating") or {}).get("votes-count", 0),
        "primary": act_key(a["name"]),
    }
    for key in hits:
        candidates.setdefault(key, []).append(a["id"])
tar.wait()
print(f"Kept {len(artists)} artists")

rows = []
for key in sorted(keys):
    from_clash = [i for i in clash_ids.get(key, []) if i in artists]
    found = candidates.get(key, [])
    by_name = [i for i in found if artists[i]["primary"] == key]
    if len(from_clash) == 1:
        mbid, method = from_clash[0], "clashfinder id"
    elif len(from_clash) > 1:
        mbid, method = None, "conflicting"
    elif len(by_name) == 1:
        mbid, method = by_name[0], "name"
    elif len(found) == 1:
        mbid, method = found[0], "alias"
    elif found:
        # several artists share the name, take the most tagged and flag it
        pool = by_name or found
        mbid = max(pool, key=lambda i: artists[i]["votes"])
        method = "ambiguous"
        if artists[mbid]["votes"] < MIN_VOTES:
            mbid, method = None, "ambiguous, too few votes"
    else:
        mbid, method = None, "unmatched"
    rows.append({"act_key": key, "mbid": mbid, "method": method, "n_candidates": len(found)})

matches = pd.DataFrame(rows)
matches["n_festivals"] = matches["act_key"].map(n_festivals)
matches["matched_name"] = matches["mbid"].map(lambda i: artists[i]["name"] if i else None)
matches["country"] = matches["mbid"].map(lambda i: artists[i]["country"] if i else None)
matches["disambiguation"] = matches["mbid"].map(lambda i: artists[i]["disambiguation"] if i else None)
matches.to_csv(OUT / "act_matches.csv", index=False)

tags = []
for m in matches.dropna(subset=["mbid"]).itertuples():
    a = artists[m.mbid]
    for tag in sorted(a["tags"].keys() | a["genres"].keys()):
        tags.append({"act_key": m.act_key, "mbid": m.mbid, "tag": tag,
                     "tag_count": a["tags"].get(tag), "genre_count": a["genres"].get(tag)})
tags = pd.DataFrame(tags)
tags.to_csv(OUT / "act_tags.csv", index=False)

print(matches["method"].value_counts().to_string())
print(f"With at least one tag: {tags['act_key'].nunique()} of {len(keys)}")
print(f"With at least one genre: {tags.dropna(subset=['genre_count'])['act_key'].nunique()}")
