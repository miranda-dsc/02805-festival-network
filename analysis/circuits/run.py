"""Two circuits: is the same-country effect carried by small acts, with "small" defined without tags?

watts/ found that festivals in the same country share more acts than chance, and that the gap
is larger among untagged acts. Untagged is used there as a stand-in for small. Tag coverage
depends on MusicBrainz, so here size is the act's reach: the number of distinct festivals it
played in 2015-2025. Reach uses only the lineups.

Two tests, both against a within-year curveball null that keeps every edition's lineup size
and every act's number of editions that year (same rules as watts/ and newman/):

A. National share. For acts with two or more editions, the share of their editions in their
   most common country, observed vs null, by reach class.
B. Same-country gap by reach class. For each pair of editions in a year, shared acts are split
   by reach class. Gap = mean excess (observed - null) for same-country pairs minus that for
   different-country pairs, computed within each year and averaged over years.

Run from the repo root:  python analysis/circuits/run.py
"""
import random
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load, same_brand  # noqa: E402

OUT = Path(__file__).resolve().parent
SAMPLES = 200
BURN_IN, GAP = 50, 5          # sweeps; one sweep = one trade attempt per edition
SEED = 2805
CLASSES = ["1 festival", "2 festivals", "3-4 festivals", "5+ festivals"]


def reach_class(n):
    return CLASSES[0] if n == 1 else CLASSES[1] if n == 2 else CLASSES[2] if n <= 4 else CLASSES[3]


def curveball_draws(rows, year):
    """yield SAMPLES lineups (list of sets), keeping row sizes and act degrees"""
    rng = random.Random(SEED + year)
    state = [set(r) for r in rows]
    n = len(state)
    for draw in range(SAMPLES):
        for _ in range((BURN_IN if draw == 0 else GAP) * n):
            i, j = rng.sample(range(n), 2)
            left, right = state[i] - state[j], state[j] - state[i]
            if left and right:
                pool = sorted(left | right)
                rng.shuffle(pool)
                common = state[i] & state[j]
                state[i] = common | set(pool[:len(left)])
                state[j] = common | set(pool[len(left):])
        yield [r.copy() for r in state]


def check_margins(draw, rows):
    if [len(r) for r in draw] != [len(r) for r in rows]:
        raise ValueError("lineup size changed")
    before = pd.Series([a for r in rows for a in r]).value_counts().sort_index()
    after = pd.Series([a for r in draw for a in r]).value_counts().sort_index()
    if not before.equals(after):
        raise ValueError("act degree changed")


def national_share(bookings):
    """share of each act's editions in its most common country (acts with 2+ editions)"""
    counts = bookings.groupby(["act_key", "country"]).size()
    total = counts.groupby(level=0).sum()
    share = counts.groupby(level=0).max() / total
    return share[total >= 2]


def main():
    lineups, editions = load()
    country = editions.set_index("edition")["country"]
    festival = editions.set_index("edition")["festival"]
    reach = lineups.groupby("act_key")["festival"].nunique()
    act_class = reach.map(reach_class)

    # observed national share
    obs_share = national_share(lineups[["act_key", "edition", "country"]])

    null_shares = []                 # one Series per draw, filled across years
    pair_rows = []
    draws_by_year = {}
    for year, group in lineups.groupby("year"):
        eds = sorted(group["edition"].unique())
        rows = [set(group.loc[group["edition"] == e, "act_key"]) for e in eds]
        draws = list(curveball_draws(rows, year))
        check_margins(draws[0], rows)
        check_margins(draws[-1], rows)
        draws_by_year[year] = (eds, draws)

        # B. shared acts by reach class, observed and null
        for i, j in combinations(range(len(eds)), 2):
            a, b = eds[i], eds[j]
            if same_brand(festival[a], festival[b]):
                continue
            obs = pd.Series([act_class[k] for k in rows[i] & rows[j]], dtype=object).value_counts()
            null = np.zeros(len(CLASSES))
            for d in draws:
                c = pd.Series([act_class[k] for k in d[i] & d[j]], dtype=object).value_counts()
                null += c.reindex(CLASSES, fill_value=0).values
            null /= SAMPLES
            for k, cls in enumerate(CLASSES):
                pair_rows.append(dict(year=year, edition_a=a, edition_b=b,
                                      festival_a=festival[a], festival_b=festival[b],
                                      country_a=country[a], country_b=country[b],
                                      same_country=country[a] == country[b],
                                      uk_pair=(country[a] == "GB") & (country[b] == "GB"),
                                      reach=cls, observed=int(obs.get(cls, 0)), null_mean=null[k]))
        print(f"{year}: {len(eds)} editions, {len(group)} bookings, {SAMPLES} draws", flush=True)

    # A. null national share: combine the same draw index across years
    for s in range(SAMPLES):
        rows = [(act, e) for year, (eds, draws) in draws_by_year.items()
                for e, lineup in zip(eds, draws[s]) for act in lineup]
        b = pd.DataFrame(rows, columns=["act_key", "edition"])
        b["country"] = b["edition"].map(country)
        null_shares.append(national_share(b))
    null_mat = pd.concat(null_shares, axis=1).reindex(obs_share.index)

    share_rows = []
    for cls in CLASSES[1:]:          # one-festival acts are national by construction
        idx = obs_share.index[act_class.reindex(obs_share.index) == cls]
        per_draw = null_mat.loc[idx].mean(axis=0)
        share_rows.append(dict(reach=cls, acts=len(idx), observed=obs_share[idx].mean(),
                               null_mean=per_draw.mean(), null_low=per_draw.quantile(0.025),
                               null_high=per_draw.quantile(0.975),
                               excess=obs_share[idx].mean() - per_draw.mean()))
    share = pd.DataFrame(share_rows)
    share.to_csv(OUT / "national_share_by_reach.csv", index=False)

    pairs = pd.DataFrame(pair_rows)
    pairs["excess"] = pairs["observed"] - pairs["null_mean"]
    pairs.to_csv(OUT / "pairs_by_reach.csv", index=False)

    def gap(frame, same_mask):
        """same-country minus different-country mean excess, within year, averaged over years"""
        per_year = []
        for _, g in frame.groupby("year"):
            same, diff = g[same_mask(g)], g[~g["same_country"]]
            if len(same) and len(diff):
                per_year.append(same["excess"].mean() - diff["excess"].mean())
        return np.mean(per_year), per_year

    gap_rows = []
    for cls in CLASSES:
        g = pairs[pairs["reach"] == cls]
        for label, mask in [("same country", lambda f: f["same_country"]),
                            ("GB with GB", lambda f: f["uk_pair"]),
                            ("same country abroad", lambda f: f["same_country"] & ~f["uk_pair"])]:
            value, yearly = gap(g, mask)
            # festival deletion range: drop every pair involving one festival, recompute
            dels = [gap(g[(g.festival_a != f) & (g.festival_b != f)], mask)[0]
                    for f in sorted(set(g.festival_a) | set(g.festival_b))]
            gap_rows.append(dict(reach=cls, contrast=label, gap=value,
                                 deletion_low=np.nanmin(dels), deletion_high=np.nanmax(dels),
                                 years_positive=int((np.array(yearly) > 0).sum()), years=len(yearly),
                                 pairs=int(mask(g).sum())))
    gaps = pd.DataFrame(gap_rows)
    gaps.to_csv(OUT / "country_gap_by_reach.csv", index=False)

    # share of the total same-country gap carried by each class
    total = gaps[gaps.contrast == "same country"].set_index("reach")["gap"]
    gaps_share = (total / total.sum()).round(3)

    # Relative version: an act at k festivals makes k(k-1)/2 pair links, so absolute gaps grow
    # with reach by construction. Compare observed/null within each class instead.
    ratios = ratio_table(pairs)
    ratios.to_csv(OUT / "country_ratio_by_reach.csv", index=False)

    write_findings(share, gaps, gaps_share, ratios, reach, lineups, editions)


def ratio_table(pairs):
    def ratio(f):
        return f["observed"].sum() / f["null_mean"].sum() if f["null_mean"].sum() > 0 else np.nan

    rows = []
    for cls in CLASSES[1:]:
        g = pairs[pairs["reach"] == cls]
        yearly = []
        for _, gy in g.groupby("year"):
            yearly.append(ratio(gy[gy["same_country"]]) / ratio(gy[~gy["same_country"]]))
        dels = []
        for f in sorted(set(g.festival_a) | set(g.festival_b)):
            h = g[(g.festival_a != f) & (g.festival_b != f)]
            dels.append(ratio(h[h["same_country"]]) / ratio(h[~h["same_country"]]))
        rows.append(dict(reach=cls,
                         same_country=ratio(g[g["same_country"]]), different_country=ratio(g[~g["same_country"]]),
                         gb_with_gb=ratio(g[g["uk_pair"]]),
                         same_country_abroad=ratio(g[g["same_country"] & ~g["uk_pair"]]),
                         relative=ratio(g[g["same_country"]]) / ratio(g[~g["same_country"]]),
                         deletion_low=np.nanmin(dels), deletion_high=np.nanmax(dels),
                         years_above_1=int(np.sum(np.array(yearly) > 1)), years=len(yearly)))
    return pd.DataFrame(rows)


def write_findings(share, gaps, gaps_share, ratios, reach, lineups, editions):
    sc = gaps[gaps.contrast == "same country"].set_index("reach")
    uk = gaps[gaps.contrast == "GB with GB"].set_index("reach")
    ab = gaps[gaps.contrast == "same country abroad"].set_index("reach")
    sh = share.set_index("reach")
    lines = [
        f"We used the shared loader (Leeds, rebroadcasts, 2020 and 2021 excluded): {len(editions)} editions, "
        f"{lineups['act_key'].nunique():,} acts. Reach is the number of distinct festivals an act played in "
        f"2015-2025; {(reach == 1).mean():.0%} of acts played one. The null is a within-year curveball with "
        f"{SAMPLES} draws per year, keeping lineup sizes and act degrees (checked on the first and last draw). "
        "Same-brand pairs are excluded from the pair test.",
        "",
        "1. National share. " + "; ".join(
            f"{r}: {sh.at[r, 'observed']:.2f} observed vs {sh.at[r, 'null_mean']:.2f} null "
            f"({sh.at[r, 'null_low']:.2f} to {sh.at[r, 'null_high']:.2f}), {int(sh.at[r, 'acts']):,} acts"
            for r in sh.index) + ".",
        "   This measures how much more acts stay in one country than random lineups of the same sizes would make them.",
        "   It misses acts' home countries and treats every edition of an act as equal.",
        "",
        "2. Same-country gap by reach (excess shared acts per pair, same country minus different country). "
        + "; ".join(f"{r}: {sc.at[r, 'gap']:+.2f} ({sc.at[r, 'deletion_low']:+.2f} to {sc.at[r, 'deletion_high']:+.2f} "
                    f"after festival deletions, positive in {int(sc.at[r, 'years_positive'])} of {int(sc.at[r, 'years'])} years)"
                    for r in CLASSES) + ".",
        "   Share of the total gap by class: " + ", ".join(f"{r} {v:.0%}" for r, v in gaps_share.items()) + ".",
        "   This measures which acts carry the country effect, with size defined from lineups only.",
        "   It misses calendar and genre, which watts/ controls for, and deletions drop pairs without rerunning the null.",
        "",
        "3. Same-country tilt relative to chance, by reach (observed/null shared acts in same-country pairs "
        "divided by the same ratio in different-country pairs). "
        + "; ".join(f"{r.reach}: {r.relative:.2f} ({r.deletion_low:.2f} to {r.deletion_high:.2f} after festival deletions, "
                    f"above 1 in {r.years_above_1} of {r.years} years)" for r in ratios.itertuples()) + ". "
        "Outside GB, same-country pairs share " + ", ".join(
            f"{r.reach} {r.same_country_abroad:.2f}x" for r in ratios.itertuples()) + " the null.",
        "   This measures the national tilt of each class, which the absolute gaps in 2 hide: an act at k "
        "festivals makes k(k-1)/2 pair links, so wide acts dominate absolute counts.",
        "   It misses calendar and genre, and the ratios outside GB rest on 57 pairs.",
        "",
        "4. UK and elsewhere, absolute gaps. GB with GB: " + ", ".join(f"{r} {uk.at[r, 'gap']:+.2f}" for r in CLASSES)
        + f" ({int(uk.at[CLASSES[0], 'pairs'])} pairs). Same country outside GB: "
        + ", ".join(f"{r} {ab.at[r, 'gap']:+.2f}" for r in CLASSES)
        + f" ({int(ab.at[CLASSES[0], 'pairs'])} pairs, positive in "
        + ", ".join(f"{int(ab.at[r, 'years_positive'])}/{int(ab.at[r, 'years'])}" for r in CLASSES) + " years).",
        "   This measures whether the pattern is only a UK pattern.",
        "   It misses precision outside GB, where few same-country pairs exist.",
    ]
    (OUT / "findings.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
