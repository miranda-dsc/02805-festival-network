"""infer origin countries from english wikipedia leads"""

import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd
import spacy
from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "data/processed"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(OUT / ".deps"))

from common import load
from en_core_web_sm import load as load_model
from geonamescache import GeonamesCache

from origin_review import apply_demonym_audit, write_checks

SAMPLE_SIZE = 30
SEED = 731
DISAGREEMENTS = 50
DISAGREEMENT_SEED = 734
DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
DEMONYMS = {
    "DZ": "algerian", "AR": "argentine argentinian", "AM": "armenian", "AU": "australian",
    "AT": "austrian", "BD": "bangladeshi", "BE": "belgian flemish walloon",
    "BR": "brazilian", "BG": "bulgarian", "CA": "canadian",
    "CL": "chilean", "CN": "chinese", "CO": "colombian", "HR": "croatian",
    "CU": "cuban", "CY": "cypriot", "CZ": "czech", "DK": "danish",
    "DO": "dominican", "EG": "egyptian", "EE": "estonian", "ET": "ethiopian",
    "FI": "finnish", "FR": "french", "GE": "georgian", "DE": "german",
    "GH": "ghanaian", "GR": "greek", "HK": "hongkonger", "HU": "hungarian",
    "IS": "icelandic", "IN": "indian", "ID": "indonesian", "IR": "iranian",
    "IQ": "iraqi", "IE": "irish", "IL": "israeli", "IT": "italian",
    "JM": "jamaican", "JP": "japanese", "JO": "jordanian", "KE": "kenyan",
    "KR": "south_korean korean", "XK": "kosovar", "LV": "latvian", "LB": "lebanese",
    "LT": "lithuanian", "LU": "luxembourgish", "MY": "malaysian",
    "MX": "mexican", "MA": "moroccan", "NL": "dutch", "NZ": "new_zealand",
    "NG": "nigerian", "NO": "norwegian", "PK": "pakistani", "PE": "peruvian",
    "PH": "filipino philippine", "PL": "polish", "PT": "portuguese",
    "PR": "puerto_rican", "RO": "romanian", "RU": "russian", "RS": "serbian",
    "SG": "singaporean", "SK": "slovak slovakian", "SI": "slovene slovenian",
    "ZA": "south_african", "ES": "spanish catalan", "LK": "sri_lankan",
    "SE": "swedish", "CH": "swiss", "SY": "syrian", "TW": "taiwanese",
    "TH": "thai", "TT": "trinidadian", "TN": "tunisian", "TR": "turkish",
    "UA": "ukrainian", "GB": "british english scottish welsh northern_irish",
    "US": "american", "UY": "uruguayan", "VE": "venezuelan",
    "VN": "vietnamese", "PS": "palestinian",
}
EXTRA_DEMONYMS = {
    "BA": "bosnian herzegovinian", "CD": "dr_congolese congolese-kinshasa",
    "CI": "ivorian", "EC": "ecuadorian ecuadorean", "FO": "faroese",
    "GY": "guyanese", "MD": "moldovan moldavian", "ML": "malian",
    "MN": "mongolian", "NE": "nigerien", "TZ": "tanzanian zanzibari",
    "UG": "ugandan", "AE": "emirati", "ZM": "zambian",
}
EXTRA_COUNTRY_ALIASES = {
    "democratic republic of the congo": "CD", "dr congo": "CD",
    "congo-kinshasa": "CD", "congo-brazzaville": "CG", "republic of the congo": "CG",
    "ivory coast": "CI",
}
COUNTRY_ALIASES = {
    "britain": "GB", "great britain": "GB", "uk": "GB", "u.k.": "GB",
    "england": "GB", "scotland": "GB", "wales": "GB", "northern ireland": "GB",
    "us": "US", "u.s.": "US", "usa": "US", "u.s.a.": "US", "united states of america": "US",
    "the netherlands": "NL", "holland": "NL", "republic of ireland": "IE",
    "czech republic": "CZ", "turkiye": "TR",
}
ORIGIN_CUE = re.compile(
    r"\b(?:born\s+in|(?:formed|founded|established)(?:\s+in\s+\d{4})?\s+in"
    r"|(?:originally\s+)?from)\s+(?:the\s+)?(?:city\s+of\s+)?$",
    re.IGNORECASE,
)
ROLE_CUE = re.compile(r"\b(?:is|are|was|were)\s+(?:an?\s+|the\s+)?$", re.IGNORECASE)


def normalize(text):
    return "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    ).strip()


def countries():
    gazetteer = GeonamesCache(min_city_population=15000)
    country = {normalize(item["name"]): code for code, item in gazetteer.get_countries().items()}
    country.update(COUNTRY_ALIASES)
    state = {normalize(item["name"]): "US" for item in gazetteer.get_us_states().values()}
    cities = defaultdict(dict)
    for item in gazetteer.get_cities().values():
        key, code = normalize(item["name"]), item["countrycode"]
        cities[key][code] = max(cities[key].get(code, 0), item["population"])
    demonym = {
        word.replace("_", " "): code
        for code, words in DEMONYMS.items() for word in words.split()
    }
    extra = {
        word.replace("_", " "): code
        for code, words in EXTRA_DEMONYMS.items() for word in words.split()
    }
    revised = {**country, **EXTRA_COUNTRY_ALIASES}
    revised.pop("congo", None)
    return (country, state, cities, demonym), (revised, state, cities, {**demonym, **extra})


def infer(doc, country, state, cities, demonym):
    entities = list(doc.ents)
    nationality = None
    for entity in entities:
        prefix = doc.text[:entity.start_char]
        if not ROLE_CUE.search(prefix):
            continue
        key = normalize(entity.text)
        if entity.label_ == "NORP" and key in demonym:
            nationality = (entity.text, demonym[key], "norp")
        elif entity.label_ == "GPE" and key in country and key not in state:
            nationality = (entity.text, country[key], "gpe_country")
        if nationality:
            break
    for i, entity in enumerate(entities):
        prefix = doc.text[:entity.start_char]
        if entity.label_ != "GPE" or not ORIGIN_CUE.search(prefix):
            continue
        key = normalize(entity.text)
        if key in country and key not in state:
            return entity.text, country[key], "gpe_country"
        last = entity
        for following in entities[i + 1:]:
            if (following.label_ != "GPE"
                    or doc.text[last.end_char:following.start_char].strip() != ","):
                break
            last = following
            qualifier = normalize(following.text)
            code = country.get(qualifier) if qualifier not in state else None
            if code is None and qualifier in state and qualifier != "georgia":
                code = state[qualifier]
            if code:
                return doc.text[entity.start_char:following.end_char], code, "gpe_qualified"
        if nationality:
            return nationality
        if key in state and key not in country:
            return entity.text, state[key], "gpe_state"
        candidates = sorted(cities.get(key, {}).items(), key=lambda item: -item[1])
        if len(candidates) == 1 or (len(candidates) > 1 and candidates[0][1] >= 4 * candidates[1][1]):
            return entity.text, candidates[0][0], "gpe_city"
    return nationality or ("", "", "")


def main():
    lineups, _ = load()
    festivals = lineups.groupby("act_key").festival.nunique()
    wiki = pd.read_csv(DATA / "act_wiki.csv", keep_default_na=False)
    wiki = wiki.loc[wiki.act_key.isin(festivals[festivals.ge(2)].index)].copy()
    english = wiki.loc[wiki.intro_lang.eq("en") & wiki.intro.str.strip().ne("")].copy()
    english = english.sort_values("act_key").reset_index(drop=True)
    assert english.act_key.is_unique
    nlp = load_model()
    original_names, revised_names = countries()
    segmenter = spacy.blank("en")
    segmenter.add_pipe("sentencizer")
    first_sentences = (next(doc.sents).text for doc in segmenter.pipe(english.intro))
    docs = nlp.pipe(first_sentences, batch_size=128,
                    disable=["parser", "tagger", "attribute_ruler", "lemmatizer"])
    predictions = [(infer(doc, *original_names), infer(doc, *revised_names)) for doc in docs]
    fields = ["origin_text", "origin_country", "method"]
    original = [f"original_{field}" for field in fields]
    for columns, index in ((original, 0), (fields, 1)):
        english[columns] = pd.DataFrame([pair[index] for pair in predictions], columns=columns)
        english[columns[0]] = english[columns[0]].str.translate(DASHES)
    print(f"{len(wiki):,} Wikipedia records and {len(english):,} English intros", flush=True)
    matches = pd.read_csv(DATA / "act_matches.csv", keep_default_na=False)
    mb = matches[["act_key", "mbid", "country"]].rename(columns={"country": "mb_country"})
    wiki = wiki.merge(mb, on=["act_key", "mbid"], how="left", validate="one_to_one",
                      indicator=True)
    assert wiki._merge.eq("both").all()
    english = english.merge(wiki[["act_key", "mb_country"]], on="act_key",
                            validate="one_to_one")
    original_found = english.loc[english.original_origin_country.ne("")]
    original_disagreements = original_found.loc[
        original_found.mb_country.ne("")
        & original_found.original_origin_country.ne(original_found.mb_country)
    ]
    original_fills = original_found.loc[original_found.mb_country.eq("")]
    extra_fills = english.loc[
        english.mb_country.eq("") & english.origin_country.ne("")
        & english.original_origin_country.eq("")
    ]
    samples = {
        "original_random": original_found.sample(n=SAMPLE_SIZE, random_state=SEED),
        "original_fill": original_fills,
        "original_disagreement": original_disagreements.sample(
            n=min(DISAGREEMENTS, len(original_disagreements)), random_state=DISAGREEMENT_SEED
        ),
        "additional_fill": extra_fills,
    }
    sample = pd.concat([frame.assign(audit_group=group) for group, frame in samples.items()])
    sample = sample.sort_values(["audit_group", "act_key"])
    labels = pd.read_csv(OUT / "origin_hand_labels.csv", keep_default_na=False)
    assert labels.act_key.is_unique
    assert labels.hand_country.str.fullmatch(r"(?:[A-Z]{2})?").all()
    audit = sample.merge(labels, on="act_key", how="left", validate="many_to_one")
    missing = audit.note.isna()
    if missing.any():
        missing_acts = audit.loc[missing, ["act_key", "qid", "audit_group"]]
        raise ValueError(f"missing hand labels:\n{missing_acts.to_string(index=False)}")
    assert set(labels.act_key) == set(sample.act_key)
    audit["original_correct"] = (
        audit.hand_country.ne("") & audit.original_origin_country.eq(audit.hand_country)
    )
    audit["correct"] = audit.hand_country.ne("") & audit.origin_country.eq(audit.hand_country)
    audit["mb_correct"] = audit.hand_country.ne("") & audit.mb_country.eq(audit.hand_country)
    audit[["audit_group", "act_key", "qid", *original, *fields, "mb_country", "hand_country",
           "original_correct", "correct", "mb_correct", "note"]].to_csv(
        OUT / "origin_hand_audit.csv", index=False
    )

    audited_fills = audit.loc[
        audit.audit_group.isin(["original_fill", "additional_fill"])
    ].drop_duplicates("act_key")
    rejected = audited_fills.loc[~audited_fills.correct, "act_key"]
    export = english[["act_key", *fields]].copy()
    export.loc[export.act_key.isin(rejected), fields] = ""
    changes = english.loc[english.original_origin_country.ne(english.origin_country)]
    changes[["act_key", *original, *fields, "mb_country"]].to_csv(
        OUT / "origin_changes.csv", index=False
    )
    export = apply_demonym_audit(export, changes)
    export.to_csv(DATA / "act_wiki_origin.csv", index=False)
    print(f"{export.origin_country.ne('').sum():,} exported countries, "
          f"{len(rejected)} unsupported fills blanked", flush=True)
    stats = []
    for version, column, checked in (
        ("original", "original_origin_country", "original_correct"),
        ("revised", "origin_country", "correct"),
    ):
        found = english.loc[english[column].ne("")]
        paired = found.loc[found.mb_country.ne("")]
        agrees = paired[column].eq(paired.mb_country).sum()
        filled = found.mb_country.eq("").sum()
        fills = audited_fills.loc[audited_fills[column].ne("")]
        assert len(fills) == filled
        random_check = audit.loc[audit.audit_group.eq("original_random")]
        disagree_check = audit.loc[audit.audit_group.eq("original_disagreement")]
        stats.append({
            "version": version,
            "wiki_records": len(wiki),
            "english_intros": len(english),
            "country_predictions": len(found),
            "paired_countries": len(paired),
            "country_agreements": agrees,
            "agreement_share": agrees / len(paired),
            "cohen_kappa": cohen_kappa_score(paired.mb_country, paired[column]),
            "wiki_missing_mb_country": int(wiki.mb_country.eq("").sum()),
            "english_missing_mb_country": int(english.mb_country.eq("").sum()),
            "filled_mb_country": filled,
            "fills_hand_supported": int(fills[checked].sum()),
            "potential_countries_after_fill_audit": len(found) - int((~fills[checked]).sum()),
            "fills_hand_abstain": int(fills.hand_country.eq("").sum()),
            "random_audit_n": len(random_check),
            "random_audit_correct": int(random_check[checked].sum()),
            "random_audit_abstain": int(random_check.hand_country.eq("").sum()),
            "random_audit_precision": random_check[checked].mean(),
            "disagreement_audit_n": len(disagree_check),
            "disagreement_audit_correct": int(disagree_check[checked].sum()),
            "disagreement_audit_abstain": int(disagree_check.hand_country.eq("").sum()),
            "disagreement_audit_precision": disagree_check[checked].mean(),
            "disagreement_audit_mb_correct": int(disagree_check.mb_correct.sum()),
        })
    summary = pd.DataFrame(stats)
    summary.to_csv(OUT / "origin_summary.csv", index=False)
    write_checks(export)
    print(summary.T.to_string(header=False))


if __name__ == "__main__":
    main()
