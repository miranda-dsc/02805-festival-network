"""group acts by wikipedia editions outside their home languages"""
from functools import lru_cache
from pathlib import Path

import pandas as pd
from babel.languages import get_territory_language_info

OUT = Path(__file__).resolve().parent
UNKNOWN_COUNTRY = "Unknown artist country"
UNKNOWN_MBID = "Unknown MBID"
TIERS = ["0 foreign", "1 foreign", "2 to 4 foreign", "5 to 9 foreign",
         "10 or more foreign", UNKNOWN_COUNTRY, UNKNOWN_MBID]
NON_ENGLISH_TIERS = ["0 non-English", "1 to 4 non-English", "5 or more non-English",
                     UNKNOWN_COUNTRY, UNKNOWN_MBID]
NATIONAL_STATUS = {"official", "de_facto_official"}
HOME_STATUS = NATIONAL_STATUS | {"official_regional"}
WIKI_LANGUAGE = {"gsw": "als", "fil": "tl", "nb": "no", "yue": "zh-yue"}
ENGLISH_EDITIONS = {"en", "simple"}
EXPORT_COLS = ["act_key", "home_country", "n_languages", "n_foreign", "tier"]


@lru_cache(maxsize=None)
def home_editions(country):
    languages = get_territory_language_info(country)
    home = {WIKI_LANGUAGE.get(lang, lang.split("_")[0])
            for lang, info in languages.items()
            if info.get("official_status") in HOME_STATUS}
    if "en" in home:
        home.add("simple")
    return frozenset(home)


def assign_tiers(acts):
    acts = acts.copy()
    if "home_country" not in acts:
        acts["home_country"] = acts["country"]
    matched = acts["mbid"].fillna("").ne("")
    acts["home_country"] = acts["home_country"].fillna("").str.strip().str.upper().where(matched, "")
    wiki = acts["langs"].fillna("").map(lambda langs: set(filter(None, langs.split(";"))))
    if not acts.loc[matched, "n_languages"].eq(wiki[matched].map(len)).all():
        raise ValueError("Wikipedia language counts differ from the edition lists")
    home = acts["home_country"].map(home_editions)
    acts["n_foreign"] = pd.array([
        len(editions - domestic) if domestic else None
        for editions, domestic in zip(wiki, home)
    ], dtype="Int64")
    acts["tier"] = pd.cut(acts["n_foreign"], [-1, 0, 1, 4, 9, float("inf")],
                          labels=TIERS[:5]).astype(object)
    acts["tier"] = acts["tier"].fillna(UNKNOWN_COUNTRY).where(matched, UNKNOWN_MBID)
    acts["n_non_english"] = wiki.map(lambda editions: len(editions - ENGLISH_EDITIONS))
    acts["n_non_english"] = acts["n_non_english"].astype("Int64").where(
        matched & acts["tier"].ne(UNKNOWN_COUNTRY))
    acts["non_english_tier"] = pd.cut(acts["n_non_english"], [-1, 0, 4, float("inf")],
                                      labels=NON_ENGLISH_TIERS[:3]).astype(object)
    acts["non_english_tier"] = acts["non_english_tier"].fillna(UNKNOWN_COUNTRY).where(matched, UNKNOWN_MBID)
    return acts


def export_tiers(acts):
    exported = acts[EXPORT_COLS].sort_values("act_key").copy()
    exported["n_languages"] = exported["n_languages"].astype("Int64")
    exported.to_csv(OUT / "tiers.csv", index=False)


def coverage_bias(acts):
    matched = acts[acts["mbid"].fillna("").ne("")].copy()
    countries = matched["home_country"].map(get_territory_language_info)
    known = countries.map(bool)
    english_home = countries.map(lambda languages: languages.get("en", {}).get("official_status")
                                 in NATIONAL_STATUS)
    rows = []
    for label, group in [("English official or de facto", matched[english_home]),
                         ("Other known country", matched[known & ~english_home]),
                         ("Unknown or unmapped country", matched[~known])]:
        one = group["n_languages"].eq(1)
        english = group["has_en"].eq(True)
        rows.append(dict(group=label, acts=len(group), english=english.sum(),
                         any_article=group["n_languages"].gt(0).sum(),
                         one_language=one.sum(), english_only=(one & english).sum()))
    return pd.DataFrame(rows)
