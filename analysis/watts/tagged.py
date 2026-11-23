"""country and sound effects with the null rerun on tagged acts only, and on untagged acts only"""
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from run import OUT, influence, load, load_editions, pair_data
from genre_profiles import MATCHED, tagged_acts
import sound

SAMPLES = 2_000


def split(lineups, methods):
    tags = tagged_acts()
    tagged = set(tags.loc[tags["method"].isin(methods), "act_key"])
    is_tagged = lineups["act_key"].isin(tagged)
    return {"tagged": lineups[is_tagged], "untagged": lineups[~is_tagged]}


def null_pairs(lineups, editions):
    def simulate(group):
        return pair_data(group, lineups[lineups["edition"].isin(group["edition"])], SAMPLES)[0]

    with ThreadPoolExecutor(max_workers=4) as pool:
        frames = pool.map(simulate, [group for _, group in editions.groupby("year")])
    return pd.concat(frames, ignore_index=True)


def country_gap(pairs):
    strata = [pairs["year"], pairs["days_bin"]]
    x = pairs["same_country"].astype(float)
    detail, _ = influence(pairs, x, strata, {})
    gap = detail[0]["full_excess"]
    deletions = [d["excess"] for d in detail]
    yearly = []
    for _, group in pairs.groupby("year"):
        detail, _ = influence(group, group["same_country"].astype(float),
                              [group["year"], group["days_bin"]], {})
        yearly.append(detail[0]["full_excess"])
    return gap, min(deletions), max(deletions), int((np.array(yearly) > 0).sum()), yearly


def national_share(lineups, matches, tags):
    """share of each act's dates in its most common country, by match status"""
    plays = lineups.groupby("act_key").agg(n=("edition", "size"), top=("country", lambda c: c.value_counts().iloc[0]))
    plays = plays[plays["n"] >= 2]
    method = matches.set_index("act_key")["method"]
    methods = method.reindex(plays.index)
    status = np.select(
        [plays.index.isin(set(tags["act_key"])), methods.isin(MATCHED),
         methods.eq("ambiguous"), methods.eq("ambiguous, too few votes"),
         methods.eq("conflicting")],
        ["tagged", "matched, no tags", "ambiguous", "too few votes", "conflicting"],
        default="unmatched",
    )
    plays["status"] = status
    plays["share"] = plays["top"] / plays["n"]
    rows = []
    for status, group in plays.groupby("status"):
        for label, selected in [("all", group), ("2 or more festivals", group),
                                ("3 or more festivals", group)]:
            if label != "all":
                festivals = lineups.groupby("act_key")["festival"].nunique()
                minimum = 2 if label == "2 or more festivals" else 3
                selected = group[pd.Series(group.index.map(festivals).fillna(0), index=group.index).ge(minimum)]
            if not selected.empty:
                rows.append(dict(status=status, control=label, acts=len(selected),
                                 mean_editions=selected["n"].mean(),
                                 one_country=selected["share"].mean(),
                                 all_one=(selected["share"] == 1).mean()))
        for n, selected in group.groupby("n"):
            rows.append(dict(status=status, control=f"exactly {n} editions", acts=len(selected),
                             mean_editions=float(n), one_country=selected["share"].mean(),
                             all_one=(selected["share"] == 1).mean()))
    return pd.DataFrame(rows)


def main():
    lineups, editions = load()
    editions = load_editions(editions).sort_values(["year", "edition"])
    full = pd.read_csv(OUT / "pairs.csv")
    full = full[~full["same_brand"]]
    rows = []
    for policy, methods in (("strict", MATCHED), ("with ambiguous", (*MATCHED, "ambiguous"))):
        for subset, part in split(lineups, methods).items():
            print(f"{policy}, {subset}: {part['act_key'].nunique()} acts, {len(part)} bookings", flush=True)
            pairs = null_pairs(part, editions)
            pairs = pairs[~pairs["same_brand"]].reset_index(drop=True)
            gap, low, high, years, yearly = country_gap(pairs)
            null_mean = pairs.loc[pairs["same_country"], "null_mean"].mean()
            excess_ratio = gap / null_mean if null_mean else np.nan
            genre = full.set_index(["edition_a", "edition_b"])["genre_similarity_strict"]
            pairs["genre_similarity_strict"] = genre.reindex(
                pd.MultiIndex.from_frame(pairs[["edition_a", "edition_b"]])).to_numpy()
            fit = sound.fit(pairs.dropna(subset=["genre_similarity_strict"]), "genre_similarity_strict")
            rows.append(dict(policy=policy, subset=subset, acts=part["act_key"].nunique(),
                             shared=pairs["shared_acts"].sum(), country_gap=gap, excess_over_null=excess_ratio,
                             null_mean=null_mean.mean(), deletion_min=low,
                             deletion_max=high, positive_years=years, country_after_genre=fit[1],
                             genre_per_0_1=fit[2], year_effects=";".join(f"{y}:{x:.3f}" for y,x in zip(sorted(pairs.year.unique()),yearly))))
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "tagged_split.csv", index=False)
    print(result.round(2).to_string(index=False))

    matches = pd.read_csv("data/processed/act_matches.csv", keep_default_na=False)
    tags = tagged_acts()
    tags = tags[tags["method"].isin(MATCHED)]
    share = national_share(lineups, matches, tags)
    share.to_csv(OUT / "national_share.csv")
    print(share.round(2).to_string())
    findings = f"""Tagged and untagged act-edition subsets use separate within-year curveball nulls with {SAMPLES:,} draws per year. Each null preserves the act edition counts and edition lineup sizes inside that subset.

1. Within strict tagged acts, the date-adjusted same-country excess was {result.iloc[0].country_gap:+.2f} shared acts per pair, with festival deletions from {result.iloc[0].deletion_min:+.2f} to {result.iloc[0].deletion_max:+.2f}. It was positive in {result.iloc[0].positive_years} of 9 years, with 2018 at {dict(item.split(':') for item in result.iloc[0].year_effects.split(';'))['2018']} acts.
   This measures the same-country gap within year and day-gap bins among tagged acts.
   It misses acts without usable MusicBrainz tags, and subset gaps do not sum to the full-lineup gap.

2. Within ambiguous-included tagged acts, the date-adjusted gap was {result.iloc[2].country_gap:+.2f}, positive in {result.iloc[2].positive_years} of 9 years, with 2018 at {dict(item.split(':') for item in result.iloc[2].year_effects.split(';'))['2018']} acts.
   This measures the same pattern when ambiguous act matches are included.
   It misses errors among ambiguous matches and does not establish that the ambiguous identities are correct.

3. National concentration by status and repeat-festival control is in national_share.csv. For acts at two or more festivals, tagged acts had mean one-country share {share[(share.status == 'tagged') & (share.control == '2 or more festivals')].one_country.iloc[0]:.2f}; too-few-vote acts had {share[(share.status == 'too few votes') & (share.control == '2 or more festivals')].one_country.iloc[0]:.2f}.
   This measures how much of an act's observed editions are in its most common country.
   It captures concentration across the observed editions and acts appearing at two or more festivals, with exact edition-count rows as a check. It misses festival-level booking opportunities.

### Open problems

Exact edition-count and distinct-festival controls are included in national_share.csv.
"""
    (OUT / "findings_tagged.md").write_text(findings)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    main()
