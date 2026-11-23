import html
import re
import unicodedata
from collections import defaultdict

MBID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
TRANSLATE = str.maketrans({"ø": "o", "æ": "ae", "œ": "oe", "ß": "ss", "ł": "l", "đ": "d", "ı": "i"})
GENERIC = frozenset("air ash blue blood cake death ghost goat her home hope jungle live love low nothing peace rain red ride sleep space stars temple tool war who wolf yes support opening unknown various guests friends".split())


def valid_mbid(value):
    return bool(MBID.fullmatch(str(value).strip().lower()))


def spelling_key(value):
    text = html.unescape(html.unescape(str(value))).casefold().translate(TRANSLATE)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    plain = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    if any(c.isalnum() for c in plain):
        text = plain
    text = re.sub(r"\s+(dj set|live set|live|dj)$", "", text.strip())
    text = re.sub(r"^the\s+", "", text)
    text = re.sub(r"[+&]", " and ", text)
    return "".join(c for c in text if c.isalnum())


def risky_key(key):
    return len(re.sub(r"[^a-z0-9]", "", key)) <= 3 or key in GENERIC


def candidate_groups(shows, kind):
    groups = defaultdict(set)
    if kind == "mbid":
        for key, mbid in shows[["act_key", "mbid"]].itertuples(index=False, name=None):
            if valid_mbid(mbid):
                groups[mbid.lower()].add(key)
    else:
        for key, name in shows[["act_key", "act"]].itertuples(index=False, name=None):
            token = spelling_key(name)
            if token:
                groups[token].add(key)
    return {label: sorted(keys) for label, keys in groups.items() if len(keys) > 1}


def merge_map(keys, groups):
    parent = {key: key for key in keys}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for members in groups.values():
        roots = sorted({root(key) for key in members})
        for key in roots[1:]:
            parent[key] = roots[0]
    return {key: root(key) for key in keys}


def resolve_acts(shows):
    """merge spelling matches only when every key carries the same sole valid mbid"""
    keys = sorted(shows.act_key.unique())
    ids = {key: {v.lower() for v in group.mbid if valid_mbid(v)}
           for key, group in shows.groupby("act_key", sort=True)}
    approved = {}
    for token, members in candidate_groups(shows, "spelling").items():
        sets = [ids[key] for key in members]
        if not any(risky_key(key) for key in members) and all(len(s) == 1 for s in sets):
            if len(set.union(*sets)) == 1:
                approved[token] = members
    mapping = merge_map(keys, approved)
    out = shows.copy()
    out["original_act_key"] = out.act_key
    out["act_key"] = out.act_key.map(mapping)
    out["identity_key"] = out.act_key
    out["has_id"] = out.mbid.map(valid_mbid)
    out = out.sort_values("has_id", ascending=False, kind="stable").drop_duplicates(["edition", "act_key"])
    return out.drop(columns="has_id"), mapping, approved
