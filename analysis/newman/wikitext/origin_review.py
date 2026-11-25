"""apply the demonym audit and export blind second-reader cases"""

from pathlib import Path

import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score

OUT = Path(__file__).resolve().parent
DATA = OUT.parents[2] / "data" / "processed"
FIELDS = ["origin_text", "origin_country", "method"]


def apply_demonym_audit(export, changes):
    labels = pd.read_csv(OUT / "origin_demonym_audit.csv", keep_default_na=False)
    assert labels.act_key.is_unique
    assert labels.hand_country.str.fullmatch(r"(?:[A-Z]{2})?").all()
    assert set(labels.act_key) == set(changes.act_key)
    audit = changes.merge(labels, on="act_key", validate="one_to_one")
    supported = audit.hand_country.ne("") & audit.hand_country.eq(audit.origin_country)
    audit = audit.assign(supported=supported)
    audit.to_csv(OUT / "origin_demonym_review.csv", index=False)
    export = export.copy()
    export.loc[export.act_key.isin(audit.loc[~supported, "act_key"]), FIELDS] = ""
    return export


def write_checks(export):
    matches = pd.read_csv(DATA / "act_matches.csv", keep_default_na=False)
    found = export.loc[export.origin_country.ne("")].merge(
        matches[["act_key", "country"]], on="act_key", validate="one_to_one"
    )
    paired = found.loc[found.country.ne("")]
    pd.DataFrame([{
        "country_predictions": len(found), "paired_countries": len(paired),
        "country_agreements": paired.origin_country.eq(paired.country).sum(),
        "agreement_share": paired.origin_country.eq(paired.country).mean(),
        "cohen_kappa": cohen_kappa_score(paired.country, paired.origin_country),
        "filled_mb_country": found.country.eq("").sum(),
    }]).to_csv(OUT / "origin_export_summary.csv", index=False)

    summary = pd.read_csv(OUT / "origin_summary.csv").set_index("version").loc["revised"]
    intervals = []
    for group, successes, trials in [
        ("random", summary.random_audit_correct, summary.random_audit_n),
        ("disagreements", summary.disagreement_audit_correct, summary.disagreement_audit_n),
        ("fills", summary.fills_hand_supported, summary.filled_mb_country),
    ]:
        n, k = int(trials), int(successes)
        ci = binomtest(k, n).proportion_ci(method="wilson")
        intervals.append({"group": group, "supported": k, "checked": n,
                          "share": k / n, "wilson_low": ci.low, "wilson_high": ci.high})
    pd.DataFrame(intervals).to_csv(OUT / "origin_wilson.csv", index=False)

    audited = pd.read_csv(OUT / "origin_hand_audit.csv", usecols=["act_key"]).drop_duplicates()
    wiki = pd.read_csv(DATA / "act_wiki.csv", keep_default_na=False, usecols=["act_key", "intro"])
    sample = audited.sort_values("act_key").sample(n=20, random_state=735)
    sample = sample.merge(wiki, on="act_key", validate="one_to_one")
    sample["intro"] = sample.intro.str.translate(dict.fromkeys(
        map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-"
    ))
    path = OUT / "second_reader.csv"
    if not path.exists():
        sample.assign(hand_country="", note="").to_csv(path, index=False)


if __name__ == "__main__":
    path = DATA / "act_wiki_origin.csv"
    export = pd.read_csv(path, keep_default_na=False, dtype=str)
    changes = pd.read_csv(OUT / "origin_changes.csv", keep_default_na=False)
    export = apply_demonym_audit(export, changes)
    export.to_csv(path, index=False)
    write_checks(export)
