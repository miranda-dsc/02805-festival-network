"""shared loader for the analysis, so every agent applies the same rules"""
import html
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
IDS_FILE = ROOT / "data" / "clashfinder_ids.txt"
COORDS = ROOT / "analysis" / "watts" / "festival_coords.csv"

PANDEMIC = [2020, 2021]
DROP_FESTIVALS = {"leeds"}  # same lineup as reading, on a second site
SAME_BRAND = [{"tomorrowland weekend 1", "tomorrowland winter"}]


def festival_map():
    festivals = {}
    festival = None
    for line in IDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#"):
            if not line.lower().startswith("# generated"):
                festival = line[1:].strip()
        elif line:
            festivals[line] = festival
    return festivals


def fix_key(key, act):
    # act_key was built before html unescaping, so "&amp;" became "and amp"
    if "&" in act and re.search(r"&[a-z]+;|&#\d+;", act):
        key = re.sub(r"\band amp\b", "and", key)
        key = re.sub(r"\s+", " ", key).strip()
    return key


def load(pandemic=False):
    """lineups (one row per edition and act) and editions, with the shared rules applied"""
    lineups = pd.read_csv(PROCESSED / "lineups_clean.csv", keep_default_na=False, na_values=[""])
    editions = pd.read_csv(PROCESSED / "editions_clean.csv")
    festivals = festival_map()

    lineups = lineups.dropna(subset=["act_key"])
    lineups = lineups[lineups["rebroadcast"].astype(str) != "True"]
    lineups["act"] = lineups["act"].fillna("")
    lineups["act_key"] = [fix_key(k, a) for k, a in zip(lineups["act_key"], lineups["act"])]
    lineups["act"] = lineups["act"].map(html.unescape)

    editions["festival"] = editions["edition"].map(festivals)
    editions = editions[~editions["festival"].isin(DROP_FESTIVALS)]
    # timezone country is wrong for 13 editions, the site country is not
    sites = pd.read_csv(COORDS).set_index("festival")
    editions["tz_country"] = editions["country"]
    editions["country"] = editions["festival"].map(sites["site_country"]).fillna(editions["country"])
    editions["lat"] = editions["festival"].map(sites["latitude"])
    editions["lon"] = editions["festival"].map(sites["longitude"])
    if not pandemic:
        editions = editions[~editions["year"].isin(PANDEMIC)]

    lineups = lineups.merge(editions[["edition", "festival", "year", "country"]], on="edition")
    lineups = lineups.drop_duplicates(["edition", "act_key"])
    return lineups, editions.reset_index(drop=True)


def same_brand(a, b):
    return {a, b} in SAME_BRAND


if __name__ == "__main__":
    lineups, editions = load()
    print(f"{len(editions)} editions, {editions['festival'].nunique()} festivals, "
          f"{len(lineups)} bookings, {lineups['act_key'].nunique()} acts")
    n = lineups.groupby("act_key")["festival"].nunique()
    print(f"acts at two or more festivals: {(n >= 2).sum()}")
