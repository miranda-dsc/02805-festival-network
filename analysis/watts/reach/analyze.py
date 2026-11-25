"""compare wikipedia reach, tag coverage and same-country overlap"""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from scipy.stats import binomtest

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent))
from run import load, load_editions, plt
from tagged import SAMPLES, country_gap
from reach_null import tier_null
from reach_tiers import (NON_ENGLISH_TIERS, TIERS, UNKNOWN_COUNTRY, UNKNOWN_MBID,
                         assign_tiers, coverage_bias, export_tiers, home_editions)
from genre_profiles import DATA, MATCHED, tagged_acts

NULL = "Within-year curveball"
AUDIT_SEED = 2805
AUDIT_SIZE = 30
MISS_SEED = 2806
MISS_SIZE = 20
LEAKAGE_SEED = 2808
LEAKAGE_RATES = (22, 45)
CACHE = Path("data/raw/wikipedia")
SHARE_NULL_COLS = [f"{measure}_null_{stat}"
                   for measure in ("one_country", "one_country_distinct")
                   for stat in ("mean", "sd", "low", "high")]


def load_acts(lineups, wiki_path=DATA / "act_wiki.csv"):
    matches = pd.read_csv(DATA / "act_matches.csv", keep_default_na=False)
    wiki = pd.read_csv(wiki_path, keep_default_na=False)
    acts = (lineups.groupby("act_key")["festival"].nunique().rename("festivals")
            .loc[lambda n: n.ge(2)].reset_index())
    acts = acts.merge(matches[["act_key", "mbid", "method", "country"]], on="act_key", how="left",
                      validate="one_to_one").fillna({"mbid": "", "method": "no match row", "country": ""})
    matched = acts.loc[acts["mbid"].ne(""), ["act_key", "mbid"]]
    if set(matched.itertuples(index=False, name=None)) != set(
            wiki[["act_key", "mbid"]].itertuples(index=False, name=None)):
        raise ValueError("wiki rows do not match eligible act keys and mbids")
    acts = acts.merge(wiki, on=["act_key", "mbid"], how="left", validate="one_to_one")
    languages = acts["n_languages"]
    acts["any_article"] = languages.gt(0)
    acts["qid_found"] = acts["qid"].fillna("").ne("")
    acts["has_en"] = acts["has_en"].eq(True)
    tags = tagged_acts()
    strict = tags.loc[tags["method"].isin(MATCHED), "act_key"]
    acts["status"] = np.where(acts["act_key"].isin(strict), "Tagged", "Untagged")
    acts["status_any"] = np.where(acts["act_key"].isin(tags["act_key"]), "Tagged", "Untagged")
    return assign_tiers(acts)


def apply_recovered_articles(acts):
    audit = pd.read_csv(OUT / "miss_audit.csv", keep_default_na=False)
    recovered = audit.loc[audit["verdict"].eq("missed")].set_index("act_key", verify_integrity=True)
    acts = acts.copy().set_index("act_key", verify_integrity=True)
    rows = acts.loc[recovered.index]
    if not rows["mbid"].eq(recovered["mbid"]).all() or not rows["n_languages"].eq(0).all():
        raise ValueError("recovered articles must match original zero-article rows")
    hosts = recovered["article_url"].map(lambda url: urlsplit(url).hostname or "")
    if not hosts.str.fullmatch(r"[a-z0-9-]+\.wikipedia\.org").all():
        raise ValueError("expected a language Wikipedia article")
    langs = hosts.str.split(".").str[0]
    acts.loc[recovered.index, "langs"] = langs
    acts.loc[recovered.index, "n_languages"] = 1
    acts.loc[recovered.index, "has_en"] = langs.eq("en")
    acts.loc[recovered.index, "any_article"] = True
    return assign_tiers(acts.reset_index())


def coverage_table(acts):
    matched = acts[acts["mbid"].ne("")]
    rows = []
    for name, groups in [
        ("All", [("All matched acts", matched)]),
        ("Match method", matched.groupby("method")),
        ("Strict tag status", matched.groupby("status")),
        ("Any usable tag", matched.groupby("status_any")),
    ]:
        for label, group in groups:
            rows.append(dict(group=name, label=label, acts=len(group),
                             qid=group["qid_found"].mean(), any_article=group["any_article"].mean(),
                             english=group["has_en"].mean()))
    return pd.DataFrame(rows)


def national_share(lineups, acts, tiers):
    plays = lineups.groupby("act_key").agg(
        n=("edition", "size"), top=("country", lambda countries: countries.value_counts().iloc[0]))
    acts = acts.join(plays, on="act_key", validate="one_to_one")
    acts["share"] = acts["top"] / acts["n"]
    distinct = lineups.drop_duplicates(["act_key", "festival"])
    country_festivals = distinct.groupby(["act_key", "country"]).size()
    festival_share = country_festivals.groupby("act_key").max() / distinct.groupby("act_key").size()
    acts = acts.join(festival_share.rename("festival_share"), on="act_key", validate="one_to_one")
    rows = []
    for tier in tiers:
        group = acts[acts["tier"].eq(tier)]
        controls = [
            ("2 or more festivals", group),
            ("3 or more festivals", group[group["festivals"].ge(3)]),
            *((f"Exactly {n} editions", part) for n, part in group.groupby("n")),
        ]
        for label, part in controls:
            if part.empty:
                continue
            rows.append(dict(tier=tier, control=label, acts=len(part),
                             mean_editions=part["n"].mean(), one_country=part["share"].mean(),
                             one_country_distinct=part["festival_share"].mean(),
                             all_one=part["share"].eq(1).mean()))
    return pd.DataFrame(rows)


def country_gaps(lineups, editions, acts, tiers, column="tier"):
    rows, years = [], []
    for tier in tiers:
        names = acts.loc[acts[column].eq(tier), "act_key"]
        part = lineups[lineups["act_key"].isin(names)]
        if part.empty:
            continue
        print(f"{tier}: {len(names):,} acts, {len(part):,} bookings", flush=True)
        pairs, summary, yearly = tier_null(part, editions)
        gap, low, high, positive, gap_yearly = country_gap(pairs)
        same = pairs[pairs["same_country"]]
        expected = same["null_mean"].mean()
        rows.append(dict(tier=tier, acts=len(names), bookings=len(part), null=NULL,
                         pairs=len(pairs), country_gap=gap, expected_same=expected,
                         gap_over_expected=gap / expected if expected else np.nan,
                         observed_over_expected=same["shared_acts"].mean() / expected if expected else np.nan,
                         deletion_min=low, deletion_max=high, positive_years=positive, **summary))
        years.append(yearly.assign(tier=tier, country_gap=gap_yearly))
    return pd.DataFrame(rows), pd.concat(years, ignore_index=True)


def plot_gaps(gaps):
    y = np.arange(len(gaps)) + gaps["tier"].eq(UNKNOWN_COUNTRY).cumsum() * 0.45
    y += gaps["tier"].eq(UNKNOWN_MBID).cumsum() * 0.45
    labels = [f"{row.tier} ({row.acts:,})" for row in gaps.itertuples()]
    fig, ax = plt.subplots(figsize=(8.1, 4.1), layout="constrained")
    ax.axvline(0, color="#b0b6bb", lw=1)
    ax.hlines(y, gaps["r_null_low"], gaps["r_null_high"], color="#8aa5ac", lw=5,
              label="Within-year curveball, central 95%")
    ax.scatter(gaps["r_null_mean"], y, color="#566c73", marker="|", s=85, zorder=3,
               label="Curveball mean")
    ax.scatter(gaps["r"], y, color="#174859", zorder=4, label="Observed")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_title("Country assortativity by reach", loc="left")
    ax.set_xlabel("Weighted country assortativity, r")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3)
    fig.savefig(OUT / "country_gap.png", dpi=180)
    plt.close(fig)


def leakage_gaps(lineups, editions, acts):
    eligible = acts.loc[acts["tier"].eq(TIERS[0]) & acts["n_languages"].eq(0), "act_key"]
    ordered = eligible.sort_values().sample(frac=1, random_state=LEAKAGE_SEED)
    results = []
    for rate in LEAKAGE_RATES:
        n_moved = (len(ordered) * rate + 50) // 100
        part = acts.assign(tier=acts["tier"].mask(acts["act_key"].isin(ordered.iloc[:n_moved]), TIERS[1]))
        result, _ = country_gaps(lineups, editions, part, TIERS[:2])
        results.append(result.assign(leakage_pct=rate, eligible=len(ordered), moved=n_moved,
                                     seed=LEAKAGE_SEED))
    return pd.concat(results, ignore_index=True)


def cache_notes(acts):
    matched = acts[acts["mbid"].ne("")]
    repeats = (f"There were {matched['mbid'].duplicated().sum()} repeat MBID rows and "
               f"{matched.loc[matched['qid_found'], 'qid'].duplicated().sum()} repeat Q-id rows across act keys.")
    matrix_path = next(CACHE.glob("sitematrix-*.json"), None)
    artist_path = CACHE / "artist_links.json"
    if matrix_path is None or not artist_path.is_file():
        return repeats
    entities = {}
    for path in CACHE.glob("wbgetentities-*.json"):
        entities.update(json.loads(path.read_text())["entities"])
    qids = set(acts.loc[acts["qid_found"], "qid"])
    if qids - entities.keys():
        return repeats
    matrix = json.loads(matrix_path.read_text())["sitematrix"]
    sites = {site["dbname"]: site for key, language in matrix.items() if key.isdigit()
             for site in language["site"] if site["dbname"].endswith("wiki")
             and site["url"].endswith(".wikipedia.org")}
    closed = {name for name, site in sites.items() if "closed" in site}
    items = [entities[qid] for qid in qids]
    artist_links = json.loads(artist_path.read_text())["links"]
    several = matched["mbid"].map(lambda mbid: len(artist_links.get(mbid, {}).get("qids", [])) > 1)
    simple = matched["langs"].str.split(";").map(lambda langs: "simple" in langs)
    total_cuts = [-1, 0, 1, 9, np.inf]
    shifted_total = pd.cut(matched["n_languages"], total_cuts).ne(
        pd.cut(matched["n_languages"] - simple, total_cuts)).sum()
    open_sites = sites.keys() - closed
    no_sitelink = sum(not open_sites.intersection(item.get("sitelinks", {})) for item in items)
    missing = sum("missing" in item for item in items)
    redirects = sum("redirects" in item for item in items)
    closed_hits = sum(bool(closed.intersection(item.get("sitelinks", {}))) for item in items)
    without_simple = acts.copy()
    without_simple["langs"] = acts["langs"].fillna("").map(
        lambda value: ";".join(lang for lang in value.split(";") if lang != "simple"))
    without_simple.loc[simple.index, "n_languages"] -= simple.astype(int)
    shifted = assign_tiers(without_simple)["tier"].ne(acts["tier"]).sum()
    known = acts["n_foreign"].notna()
    cuts = [-1, 0, 1, 4, 9, np.inf]
    foreign = acts.loc[known, "n_foreign"]
    separate_simple = acts.loc[known, "langs"].str.split(";").map(lambda langs: "simple" in langs)
    english_at_home = acts.loc[known, "home_country"].map(
        lambda country: "simple" in home_editions(country))
    count_simple = foreign + (separate_simple & english_at_home).astype(int)
    shifted_if_foreign = pd.cut(foreign, cuts).ne(pd.cut(count_simple, cuts)).sum()
    several_text = "Five" if several.sum() == 5 else str(several.sum())
    return (
        f"The dump contained {matched.loc[matched['mbid'].isin(artist_links), 'mbid'].nunique():,} "
        f"of {matched['mbid'].nunique():,} distinct MBIDs. {repeats} "
        f"We followed {redirects} Wikidata redirects. Of {no_sitelink} Q-ids without a language sitelink, "
        f"{missing} were missing from Wikidata. Direct Wikipedia URLs can recover an article without a sitelink. "
        f"{several_text} acts with several Q-ids were left unresolved. "
        f"The site list contains {len(sites)} language Wikipedias. We excluded {len(closed)} closed editions, "
        f"which carried {closed_hits} of the queried items. Simple English counts as a separate "
        f"edition in the raw data for {simple.sum()} acts. Dropping it moves {shifted_total} acts across "
        f"the total-edition cutoffs (0, 1, 2 to 9, and 10 or more) and {shifted} across the foreign-tier "
        f"cutoffs. Treating it as foreign everywhere would move {shifted_if_foreign} acts across "
        "the foreign-tier cutoffs."
    )


def audit_notes(acts):
    keys = ["act_key", "mbid", "qid", "method"]
    audit = pd.read_csv(OUT / "audit.csv", keep_default_na=False)
    sample = acts[acts["qid_found"]].sort_values("act_key").sample(n=AUDIT_SIZE, random_state=AUDIT_SEED)
    audit = audit.merge(sample[keys + ["any_article"]], on=keys, validate="one_to_one")
    if len(audit) != AUDIT_SIZE or not audit["verdict"].isin(["correct", "wrong", "uncertain"]).all():
        raise ValueError("qid audit does not match its random draw")
    decided = audit[audit["verdict"].ne("uncertain")]
    correct = decided["verdict"].eq("correct").sum()
    ci = binomtest(correct, len(decided)).proportion_ci(method="wilson")
    mix = ", ".join(f"{n} {m}" for m, n in audit["method"].value_counts().items())
    article = decided[decided["any_article"]]
    article_correct = article["verdict"].eq("correct").sum()
    wrong = " ".join(f"The {row.method} match for `{row.act_key}` was wrong. {row.evidence}"
                     for row in decided[decided["verdict"].eq("wrong")].itertuples())
    positive = (
        f"The random Q-id audit confirmed {correct} of {len(decided)} identities "
        f"({correct / len(decided):.1%}, 95% Wilson interval {ci.low:.1%} to {ci.high:.1%}). "
        f"It confirmed {article_correct} of {len(article)} among acts with articles. "
        f"The sample mix was {mix}. {wrong} "
        "This measures join precision conditional on a Q-id. It gives limited precision by match method "
        "and misses acts without a Q-id. [Q-id audit](audit.csv)"
    )
    misses = pd.read_csv(OUT / "miss_audit.csv", keep_default_na=False)
    candidates = acts[acts["n_languages"].eq(0)].sort_values("act_key")
    draw = candidates.sample(n=MISS_SIZE, random_state=MISS_SEED)
    if set(draw["act_key"]) != set(misses["act_key"]) or len(misses) != MISS_SIZE:
        raise ValueError("miss audit does not match its random draw")
    recovered = misses[misses["verdict"].eq("missed")].merge(
        draw[["act_key", "home_country", "n_foreign"]], on="act_key", validate="one_to_one")
    known = recovered[recovered["n_foreign"].notna()]
    audited_zero = draw["tier"].eq(TIERS[0]).sum()
    known_foreign = sum(urlsplit(row.article_url).hostname.split(".")[0] not in home_editions(row.home_country)
                        for row in known.itertuples())
    found = misses["verdict"].eq("missed").sum()
    uncertain = misses["verdict"].eq("uncertain").sum()
    miss_ci = binomtest(found, len(misses)).proportion_ci(method="wilson")
    foreign_ci = binomtest(known_foreign, audited_zero).proportion_ci(method="wilson")
    negative = (
        f"We found a missed foreign article for {known_foreign} of {audited_zero} sampled acts in the "
        f"zero-foreign tier ({known_foreign / audited_zero:.1%}, 95% Wilson interval "
        f"{foreign_ci.low:.1%} to {foreign_ci.high:.1%}). "
        f"Across all {len(misses)} sampled acts with no linked article, we recovered "
        f"an article of any language for {found} "
        f"({found / len(misses):.1%}, 95% Wilson interval {miss_ci.low:.1%} to {miss_ci.high:.1%}). "
        f"All recovered articles existed before the crawl. We marked {uncertain} cases uncertain. "
        "We searched across Wikipedias and checked candidate titles against festival or artist sources. "
        "This checks how often a manual search "
        "recovers an article from the no-article group. It misses articles the search did not surface "
        "and gives a wide estimate from a small draw. [Miss audit](miss_audit.csv)"
    )
    return positive, negative


def gap_table(gaps):
    lines = [
        "| Group | Acts | Observed r | Null r mean (SD) | Overlap O/E | Gap / expected | Years above null | r excess deletion (fixed draws) | OLS deletion, acts per pair (fixed baselines) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in gaps.itertuples():
        if row.tier in (UNKNOWN_COUNTRY, UNKNOWN_MBID):
            lines.append("| **Separate group** | | | | | | | | |")
        lines.append(f"| {row.tier} | {row.acts:,} | {row.r:+.3f} | {row.r_null_mean:+.3f} ({row.r_null_sd:.3f}) | "
                     f"{row.observed_over_expected:.2f} | {row.gap_over_expected:+.2f} | "
                     f"{row.r_positive_years} of {row.r_defined_years} | "
                     f"{row.r_deletion_min:+.3f} to {row.r_deletion_max:+.3f} | "
                     f"{row.deletion_min:+.2f} to {row.deletion_max:+.2f} |")
    return "\n".join(lines)


def write_findings(acts, coverage, share, gaps, strict, non_english, recovered, repeated, leakage):
    matched = acts[acts["mbid"].ne("")]
    bias = coverage_bias(acts).set_index("group")
    english = bias.loc["English official or de facto"]
    other = bias.loc["Other known country"]
    bias_text = (
        f"English Wikipedia covered {english.english:,} of {english.acts:,} acts "
        f"({english.english / english.acts:.1%}) from countries with nationally official or de facto "
        f"English, and {other.english:,} of {other.acts:,} ({other.english / other.acts:.1%}) "
        "from other countries with a language mapping. Among acts with one article, English was "
        f"the only edition for {english.english_only} of {english.one_language} in the first group "
        f"and {other.english_only} of {other.one_language} in the second."
    )
    pos, neg = audit_notes(acts)
    table = [
        "| Group | Acts | Q-id | Any article | English |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in coverage.itertuples():
        label = f"{row.group}, {row.label}" if row.group.endswith(("status", "tag")) else row.label
        table.append(f"| {label} | {row.acts:,} | {row.qid:.1%} | {row.any_article:.1%} | {row.english:.1%} |")
    concentration = [
        "| Group | Strict tagged | Editions observed | Editions null | Distinct festivals observed | Distinct festivals null | Observed at 2 editions |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    exact = share[share["control"].eq("Exactly 2 editions")].set_index("tier")
    for row in gaps.itertuples():
        if row.tier in (UNKNOWN_COUNTRY, UNKNOWN_MBID):
            concentration.append("| **Separate group** | | | | | | |")
        group = acts[acts["tier"].eq(row.tier)]
        tag = f"{group['status'].eq('Tagged').mean():.1%}" if row.tier != UNKNOWN_MBID else "NA"
        concentration.append(
            f"| {row.tier} | {tag} | {row.one_country:.1%} | {row.one_country_null_mean:.1%} | "
            f"{row.one_country_distinct:.1%} | {row.one_country_distinct_null_mean:.1%} | "
            f"{exact.at[row.tier, 'one_country']:.1%} |"
        )
    sources = {
        "null": "[Week 3, part 6](https://sunelehmann.com/socialgraphs2026-web/weeks/week3.html#compared-to-what)",
        "r": "[Week 3, part 7](https://sunelehmann.com/socialgraphs2026-web/weeks/week3.html#mixing-patterns-do-the-important-stick-together) and [Network Atlas, section 30.2](https://www.networkatlas.eu/files/sna_book.pdf)",
        "bias": "[Week 7, part 7](https://sunelehmann.com/socialgraphs2026-web/weeks/week7.html#bias)",
    }
    coverage_md = "\n".join(table)
    concentration_md = "\n".join(concentration)
    known = gaps[~gaps["tier"].isin([UNKNOWN_COUNTRY, UNKNOWN_MBID])]
    zero = known.iloc[0]
    high = known.iloc[-1]
    high_band = "inside" if high.r_null_low <= high.r <= high.r_null_high else "outside"
    ratio_peak = known.loc[known["observed_over_expected"].idxmax()]
    strict_known = strict[~strict["tier"].isin([UNKNOWN_COUNTRY, UNKNOWN_MBID])]
    strict_high = strict_known.iloc[-1]
    strict_lowest = strict_known["r_excess"].idxmin() == strict_high.name
    strict_result = (
        f"The highest foreign-reach tier had observed r {strict_high.r:+.3f} and null mean "
        f"{strict_high.r_null_mean:+.3f}"
        + (", the smallest excess r among the five foreign tiers." if strict_lowest else ".")
    )
    old = pd.read_csv(OUT / "country_gap_previous_rule.csv")
    comparison = old[["tier", "acts", "r"]].merge(
        gaps[["tier", "acts", "r"]], on="tier", suffixes=("_previous", ""), validate="one_to_one")
    comparison["act_change"] = comparison["acts"] - comparison["acts_previous"]
    comparison["r_change"] = comparison["r"] - comparison["r_previous"]
    comparison.to_csv(OUT / "tier_rule_comparison.csv", index=False)
    changes = ["| Group | Earlier acts | Acts | Earlier r | r |", "|---|---:|---:|---:|---:|"]
    for row in comparison.itertuples():
        changes.append(f"| {row.tier} | {row.acts_previous:,} | {row.acts:,} | {row.r_previous:+.3f} | {row.r:+.3f} |")
    changes_md = "\n".join(changes)
    excess = pd.DataFrame({"Official status": gaps.set_index("tier")["r_excess"],
                           "Earlier home rule": old.set_index("tier")["r_excess"],
                           "Strict matching": strict.set_index("tier")["r_excess"]}).reindex(TIERS[:5])
    excess_lines = [
        "| Foreign tier | Official status | Earlier home rule | Strict matching |",
        "|---|---:|---:|---:|",
    ]
    for tier, row in excess.iterrows():
        excess_lines.append(f"| {tier} | " + " | ".join(f"{value:+.3f}" for value in row) + " |")
    excess_md = "\n".join(excess_lines)
    high_rules = pd.concat([gaps, old, strict]).loc[lambda x: x["tier"].eq(TIERS[4])]
    inside = high_rules["r"].between(high_rules["r_null_low"], high_rules["r_null_high"]).sum()
    band_rules = "all three rules" if inside == 3 else f"{inside} of three rules"
    leakage_lines = [
        "| Leakage | Acts moved | Tier | Acts | Observed r | Null mean r | r excess |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in leakage.itertuples():
        leakage_lines.append(
            f"| {row.leakage_pct}% | {row.moved:,} | {row.tier} | {row.acts:,} | "
            f"{row.r:+.3f} | {row.r_null_mean:+.3f} | {row.r_excess:+.3f} |")
    leakage_md = "\n".join(leakage_lines)
    baseline = gaps.set_index("tier")["r_excess"]
    baseline_gap = baseline[TIERS[0]] - baseline[TIERS[1]]
    leakage_gap = leakage.pivot(index="leakage_pct", columns="tier", values="r_excess")
    leakage_gap = leakage_gap[TIERS[0]] - leakage_gap[TIERS[1]]
    leakage_contrasts = " and ".join(f"{value:.3f} at {rate}%" for rate, value in leakage_gap.items())
    recovery = gaps[["tier", "acts", "r", "r_excess"]].merge(
        recovered[["tier", "acts", "r", "r_excess"]], on="tier",
        suffixes=("", "_recovered"), validate="one_to_one")
    moved = recovery[recovery["acts"].ne(recovery["acts_recovered"])]
    recovery_text = " ".join(
        f"The {row.tier} group moved from {row.acts:,} to {row.acts_recovered:,} acts "
        f"and from r {row.r:+.4f} to {row.r_recovered:+.4f}."
        for row in moved.itertuples())
    zero_recovered = recovered.set_index("tier").loc[TIERS[0]]
    unmapped = acts.loc[acts["tier"].eq(UNKNOWN_COUNTRY), "home_country"].ne("").sum()
    unmapped_label = "code" if unmapped == 1 else "codes"
    report = f"""# Wikipedia reach

We used {len(acts):,} acts at two or more festivals. Foreign reach counts Wikipedia editions outside the act's home languages, using MusicBrainz artist country and Babel's language data. We used five tiers for mapped artist countries. Zero foreign includes {acts.loc[acts['tier'].eq(TIERS[0]), 'any_article'].sum():,} acts with home-language articles and the rest have no linked article. The unknown artist country group contains {acts.loc[acts['tier'].eq(UNKNOWN_COUNTRY), 'home_country'].eq('').sum():,} blank country codes and {unmapped:,} unmapped {unmapped_label}, all with blank foreign counts. The {acts['tier'].eq(UNKNOWN_MBID).sum():,} acts without an MBID form a match-failure group.

## Country mixing

The null in the table is within-year curveball, with {SAMPLES:,} draws per year and group. It fixes each act's yearly edition count and each edition's lineup size within the group. Leeds and the pandemic years are excluded by the shared loader. Same-brand pairs are excluded from the projected statistics.

{gap_table(gaps)}

The zero-foreign tier had observed r {zero.r:+.3f} against {zero.r_null_mean:+.3f} under within-year curveball. The tier with 10 or more foreign editions had r {high.r:+.3f} against {high.r_null_mean:+.3f} and was {high_band} its central null band. Same-country overlap relative to within-year curveball expectation peaked in the {ratio_peak.tier} tier at {ratio_peak.observed_over_expected:.2f}. For the unknown artist country group, r is undefined in 2015 because all observed overlap was between British editions.

Each projection edge is weighted by the number of shared acts in the group. We count its weight once in each direction in the country mixing matrix and compute categorical assortativity as (diagonal share minus marginal agreement) divided by (one minus marginal agreement). The pooled estimate sums the yearly mixing matrices. We recompute r for every curveball projection. The r deletion range drops each festival's edges from the observed and shuffled projections, then recomputes observed r minus null mean r. The observed/expected ratio uses same-country pair overlap and includes pairs with zero overlap. Gap/expected divides the year and day-bin adjusted same-country contrast by that same null expectation. The raw excess has units of shared acts per pair and depends on tier lineup sizes. {sources['r']}

Country assortativity captures whether more of the shared-act edge weight falls within countries than the weighted country marginals imply. It misses which booking decisions and genres produce those ties. The ratios capture the size of overlap and the adjusted gap relative to the tier baseline. They miss differences between individual festivals within a tier.

![Country assortativity and within-year curveball band](country_gap.png)

The horizontal bands show the central 95% of pooled curveball r draws. The null means are below zero for these loopless projections. The shuffle can place a shared act only on distinct editions, while the marginal agreement in r allows independently drawn edge ends. The bands use draws from one post-burn-in state per year and omit variation across such states. The fixed-draw r deletion removes a festival's edges from every observed and shuffled projection. The fixed-baseline OLS deletion refits the gap after dropping its pairs and uses the original pair expectations. [Yearly r and null spread](assortativity_yearly.csv) · [Raw gap per pair](country_gap.csv)

## One-country share

The table uses the same within-year curveball null for both measures. We pool bookings over years and give each edition or distinct festival one vote per act. For each act we take the share in its most-played country, then average over acts. We apply both measures to every shuffled booking draw. The observed repeat-festival cohort stays fixed. {sources['null']}

{concentration_md}

The zero-foreign tier was {zero.one_country_excess * 100:.1f} percentage points above its edition-based null and {zero.one_country_distinct_excess * 100:.1f} points above its distinct-festival null. The corresponding excesses for the highest foreign tier were {high.one_country_excess * 100:.1f} and {high.one_country_distinct_excess * 100:.1f} points. Its observed distinct-festival share was {high.one_country_distinct:.1%}, with a central null band of {high.one_country_distinct_null_low:.1%} to {high.one_country_distinct_null_high:.1%}. In the observed cohort, {repeated:.1%} of acts return to a festival in another year.

This comparison captures national booking concentration beyond the observed edition counts and lineup sizes. The yearwise shuffle has no festival memory and can change both the number of distinct festivals and the pattern of return bookings. Even with one vote per festival, it cannot distinguish a national circuit from loyalty to festivals that book the same act again. It also misses bookings outside the sample. [Share estimates and null spread](national_share.csv)

## Coverage and audit

{coverage_md}

Coverage captures how often the MusicBrainz join supplies Wikipedia evidence and how that varies with tagging. It misses unlinked articles and shares errors in the upstream act matches.

{bias_text} Counting articles outside each act's home languages removes the automatic reach credit for a home-language article. It still reflects unequal editing and MusicBrainz linkage across language communities. {sources['bias']}

{pos}

{neg}

The seven-page sensitivity adds the verified Wikipedia edition for each recovered act. {recovery_text} Zero-foreign observed r was {zero_recovered.r:+.3f} against {zero_recovered.r_null_mean:+.3f} under within-year curveball in that rerun. This check measures the effect of the seven documented pages and misses unsearched acts and further language editions of the recovered pages. [Recovered-page sensitivity](country_gap_recovered.csv)

We moved 22% and 45% of the {leakage['eligible'].iloc[0]:,} zero-foreign acts without a linked article into the one-foreign tier. We sorted act keys and drew one random order with seed {LEAKAGE_SEED}, rounded each count to the nearest act, and used nested samples. We reran the within-year curveball null with {SAMPLES:,} draws per year for each resulting tier.

{leakage_md}

Using unrounded estimates, the zero-minus-one difference in r excess fell from {baseline_gap:.3f} before reassignment to {leakage_contrasts}. The zero-foreign excess stayed above +0.21 in both scenarios, compared with {high.r_excess:+.3f} for the 10-or-more tier, whose membership is fixed in this test. This measures sensitivity to random reassignment at two specified leakage rates. It misses systematic differences in which acts lack links and the possibility that recovered acts belong in tiers above one foreign edition. The scenarios give no numerical bound on the contrast. [Leakage results](country_gap_leakage.csv)

## Methods and sensitivity

{cache_notes(acts)}

Babel home languages include official, de facto official, and regional official languages. Simple English shares the home status of English. Acts with an unmapped code such as XE for Europe go in the unknown artist country group regardless of article coverage. The comparison shows the effect on counts and pooled r of dropping the majority-speaker rule and reassigning unmapped codes. It misses the languages a particular act uses.

{changes_md}

The non-English sensitivity excludes both English editions and uses 0, 1 to 4, and 5 or more non-English editions, with the two unknown groups kept separate.

{gap_table(non_english)}

The same within-year curveball baseline and mixing statistics apply in this sensitivity. It checks how the result changes when English is excluded for every act. It misses whether each remaining language is local to the act. [Non-English results, including one-country shares](country_gap_non_english.csv)

The strict-match sensitivity keeps Clashfinder ID, name and alias matches and reruns the within-year curveball on those acts. The main analysis includes {matched['method'].eq('ambiguous').sum():,} ambiguous matches. {strict_result} This checks whether the main pattern survives a stricter join. It changes group composition and skips the Unknown MBID group. [Strict-match results](country_gap_strict.csv)

The table shows observed r minus mean within-year curveball r. The excess falls across all five tiers under each rule. The 10-or-more tier sits inside its central 95% null band under {band_rules}. Under the official-status rule, the overlap ratio peaks at one foreign edition.

{excess_md}
"""
    (OUT / "findings_reach.md").write_text(report, encoding="utf-8")


def main():
    lineups, editions = load()
    editions = load_editions(editions).sort_values(["year", "edition"])
    acts = load_acts(lineups)
    export_tiers(acts)
    print(acts["tier"].value_counts().reindex(TIERS).to_string(), flush=True)
    coverage = coverage_table(acts)
    coverage.to_csv(OUT / "coverage.csv", index=False)
    share = national_share(lineups, acts, TIERS)
    gaps, years = country_gaps(lineups, editions, acts, TIERS)
    strict, strict_years = country_gaps(lineups, editions, acts[acts["method"].isin(MATCHED)],
                                       [tier for tier in TIERS if tier != UNKNOWN_MBID])
    non_english, non_english_years = country_gaps(lineups, editions, acts, NON_ENGLISH_TIERS,
                                                  column="non_english_tier")
    supplemented = apply_recovered_articles(acts)
    changed = acts["tier"].ne(supplemented["tier"])
    affected = set(acts.loc[changed, "tier"]) | set(supplemented.loc[changed, "tier"])
    recovered, recovered_years = country_gaps(
        lineups, editions, supplemented, [tier for tier in TIERS if tier in affected])
    recovered = pd.concat([gaps[~gaps["tier"].isin(affected)], recovered], ignore_index=True)
    recovered = recovered.set_index("tier").loc[TIERS].reset_index()
    recovered_years = pd.concat([years[~years["tier"].isin(affected)], recovered_years], ignore_index=True)
    for result, name in [(gaps, "country_gap"), (strict, "country_gap_strict"),
                         (non_english, "country_gap_non_english"), (recovered, "country_gap_recovered")]:
        result.to_csv(OUT / f"{name}.csv", index=False)
    pd.concat([years.assign(policy="foreign"), strict_years.assign(policy="strict foreign"),
               non_english_years.assign(policy="non-English"),
               recovered_years.assign(policy="recovered")], ignore_index=True).to_csv(
        OUT / "assortativity_yearly.csv", index=False)
    share = share.merge(gaps[["tier", *SHARE_NULL_COLS]], on="tier",
                        how="left", validate="many_to_one")
    share.loc[share["control"].ne("2 or more festivals"), SHARE_NULL_COLS] = np.nan
    share.to_csv(OUT / "national_share.csv", index=False)
    plot_gaps(gaps)
    repeat_years = (lineups[lineups["act_key"].isin(acts["act_key"])]
                    .groupby(["act_key", "festival"])["year"].nunique())
    repeated = repeat_years.gt(1).groupby("act_key").any().mean()
    leakage = leakage_gaps(lineups, editions, acts)
    leakage.to_csv(OUT / "country_gap_leakage.csv", index=False)
    write_findings(acts, coverage, share, gaps, strict, non_english, recovered, repeated, leakage)
    print(gap_table(gaps))


if __name__ == "__main__":
    main()
