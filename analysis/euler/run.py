import hashlib
import json
import random
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from act_identity import candidate_groups, merge_map, resolve_acts, risky_key, valid_mbid

OUT = Path("analysis/euler")
DATA = Path("data/processed")
YEARS = (2019, 2023)
PANDEMIC = (2020, 2021)
SAMPLES = 200
SEED = 20261122
BAD = "\u2014\u2013\u2212\u2012\u2015\u2010\u2011"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
OUT.mkdir(parents=True, exist_ok=True)


def safe(value):
    if isinstance(value, str):
        return "".join("-" if ch in BAD else ch for ch in value)
    return value


def csv(frame, name):
    frame.map(safe).to_csv(OUT / name, index=False)


def projection(rows, n_acts):
    sizes = np.array([len(row) for row in rows])
    ri = np.repeat(np.arange(len(rows)), sizes)
    ci = np.concatenate([np.array(sorted(row), dtype=int) for row in rows])
    incidence = csr_matrix((np.ones(len(ci), dtype=np.int32), (ri, ci)), shape=(len(rows), n_acts))
    return (incidence @ incidence.T).toarray()


def graph(table, column, editions):
    acts = sorted(table[column].unique())
    index = {name: i for i, name in enumerate(acts)}
    groups = table.groupby("edition")[column].agg(set).to_dict()
    rows = [{index[key] for key in groups.get(edition, set())} for edition in editions]
    return rows, len(acts)


def stat(values):
    return {"shared_act_links": int(values.sum()), "positive_pairs": int(np.count_nonzero(values))}


def describe(observed, values):
    values = np.asarray(values, dtype=float)
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    return {"observed": float(observed), "null_mean": mean, "null_sd": sd,
            "z": float((observed - mean) / sd) if sd > 1e-10 else None}


def curveball(original, n_acts, seed, mask):
    samples = []
    diagnostics = []
    expected_rows = np.array([len(row) for row in original])
    expected_cols = np.bincount([act for row in original for act in row], minlength=n_acts)
    for chain, gap in enumerate((5, 10)):
        rng = random.Random(seed + chain * 100000)
        rows = [set(row) for row in original]
        trades = 0
        moved = 0
        def trade(count):
            nonlocal trades, moved
            for _ in range(count):
                a, b = rng.sample(range(len(rows)), 2)
                left, right = rows[a] - rows[b], rows[b] - rows[a]
                pool = sorted(left | right)
                if not left or not right:
                    continue
                rng.shuffle(pool)
                common = rows[a] & rows[b]
                new_left = set(pool[:len(left)])
                new_right = set(pool[len(left):])
                moved += int(new_left != left)
                rows[a], rows[b] = common | new_left, common | new_right
                trades += 1
        trade(50 * len(rows))
        chain_values = []
        for sample in range(SAMPLES // 2):
            trade(gap * len(rows))
            assert np.array_equal([len(row) for row in rows], expected_rows)
            assert np.array_equal(np.bincount([act for row in rows for act in row], minlength=n_acts), expected_cols)
            matrix = projection(rows, n_acts)
            samples.append(matrix)
            chain_values.append(int(np.count_nonzero(matrix[mask])))
        variance = np.std(chain_values)
        lag = float(np.corrcoef(chain_values[:-1], chain_values[1:])[0, 1]) if variance else None
        diagnostics.append({"chain": chain, "gap_sweeps": gap, "accepted_trades": trades,
                            "changed_trades": moved, "pair_mean": float(np.mean(chain_values)),
                            "pair_sd": float(np.std(chain_values, ddof=1)), "lag1": lag})
    return np.stack(samples), diagnostics


inputs = [DATA / "lineups_clean.csv", DATA / "editions_clean.csv", Path("data/clashfinder_ids.txt")]
hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
shows = pd.read_csv(inputs[0], keep_default_na=False)
editions = pd.read_csv(inputs[1], keep_default_na=False)
assert editions.edition.is_unique
festival = None
festivals = {}
for line in inputs[2].read_text().splitlines():
    line = line.strip()
    if line.startswith("#"):
        festival = line[1:].strip()
    elif line:
        assert festival and not festival.startswith("Generated")
        assert line not in festivals
        festivals[line] = festival
editions["festival"] = editions.edition.map(festivals)
assert editions.festival.notna().all()
assert set(shows.edition) <= set(editions.edition)
rebroadcast = shows.rebroadcast.astype(str).str.lower()
assert rebroadcast.isin(["true", "false"]).all()
raw_count = len(shows)
shows = shows[rebroadcast == "false"].copy()
shows = shows.merge(editions[["edition", "festival", "year"]], on="edition", how="left", validate="many_to_one")
pandemic_rows = int(shows.year.isin(PANDEMIC).sum())
shows = shows[~shows.year.isin(PANDEMIC)].copy()
assert not shows.duplicated(["edition", "act_key"]).any()
shows["mbid"] = shows.mbid.str.strip().str.lower()
valid = shows[shows.mbid.map(valid_mbid)]
mbid_groups = candidate_groups(shows, "mbid")
spelling_groups = candidate_groups(shows, "spelling")
keys = sorted(shows.act_key.unique())
risk_keys = {key for key in keys if risky_key(key)}
conflict_keys = set(valid.groupby("act_key").mbid.nunique().loc[lambda x: x > 1].index)
fixed, fix_map, approved = resolve_acts(shows)
print(f"{raw_count} input rows; {raw_count - len(shows) - pandemic_rows} rebroadcast rows removed; {pandemic_rows} pandemic rows excluded")
print(f"{len(keys)} act keys; {len(mbid_groups)} shared-ID groups; {len(spelling_groups)} spelling groups; {len(risk_keys)} risk keys; {len(conflict_keys)} keys with conflicting IDs")
print(f"{len(approved)} approved spelling groups; removed-stages file present: {(DATA / 'removed_stages.csv').exists()}")

csv(valid.groupby("mbid").agg(n_keys=("act_key", "nunique"),
    keys=("act_key", lambda x: " | ".join(sorted(set(x))))).reset_index().query("n_keys > 1"), "mbid_groups.csv")
csv(pd.DataFrame([{"group": group, "n_keys": len(members), "keys": " | ".join(members),
                  "approved_fix": group in approved} for group, members in spelling_groups.items()]), "spelling_groups.csv")
csv(shows[shows.act_key.isin(risk_keys)].groupby("act_key").agg(
    n_editions=("edition", "nunique"), names=("act", lambda x: " | ".join(sorted(set(x)))),
    n_valid_mbids=("mbid", lambda x: len({v for v in x if valid_mbid(v)}))).reset_index(), "risk_keys.csv")
csv(valid[valid.act_key.isin(conflict_keys)][["edition", "year", "festival", "act_key", "act", "mbid"]], "conflicting_ids.csv")
csv(pd.DataFrame([{"act_key": key, "identity_key": value} for key, value in fix_map.items() if key != value]), "proposed_mapping.csv")
csv(fixed, "proposed_lineups.csv")
assert set(fixed.edition) == set(shows.edition)
assert not fixed.duplicated(["edition", "act_key"]).any()

scenario_tables = {"baseline": shows.assign(identity_key=shows.act_key)}
for label, groups in [("all_shared_mbids", mbid_groups), ("all_spellings", spelling_groups)]:
    mapping = merge_map(keys, groups)
    scenario_tables[label] = shows.assign(identity_key=shows.act_key.map(mapping))
scenario_tables["short_generic_split"] = shows.assign(identity_key=[
    f"{key}@@{fest}" if key in risk_keys else key for key, fest in zip(shows.act_key, shows.festival)])
scenario_tables["conflicting_id_split"] = shows.assign(identity_key=[
    f"{key}@@{mbid if valid_mbid(mbid) else 'unresolved'}" if key in conflict_keys else key
    for key, mbid in zip(shows.act_key, shows.mbid)])
scenario_tables["proposed_fix"] = fixed
summary_rows, changes, pair_rows, group_rows, diagnostics = [], [], [], [], []
nulls_by_year = {}
for year in YEARS:
    ids = sorted(editions.loc[editions.year == year, "edition"])
    names = editions.set_index("edition").loc[ids, "festival"].to_numpy()
    assert len(set(names)) == len(names)
    mask = np.triu(np.ones((len(ids), len(ids)), dtype=bool), 1) & (names[:, None] != names[None, :])
    originals, nulls = {}, {}
    for si, (scenario, table) in enumerate(scenario_tables.items()):
        subset = table[table.year == year]
        rows, n_acts = graph(subset, "identity_key", ids)
        original = projection(rows, n_acts)
        samples, checks = curveball(rows, n_acts, SEED + year * 100 + si * 10000, mask)
        originals[scenario], nulls[scenario] = original, samples
        observed = stat(original[mask])
        for metric, value in observed.items():
            draws = samples[:, mask].sum(axis=1) if metric == "shared_act_links" else np.count_nonzero(samples[:, mask], axis=1)
            summary_rows.append({"year": year, "scenario": scenario, "metric": metric, **describe(value, draws)})
        diagnostics.extend({"year": year, "scenario": scenario, **check} for check in checks)
        print(f"{year} {scenario}: {len(ids)} editions; {n_acts} acts; {observed}; {len(samples)} checked nulls", flush=True)
    base, base_samples = originals["baseline"], nulls["baseline"]
    for scenario in list(scenario_tables)[1:]:
        current, samples = originals[scenario], nulls[scenario]
        a, b = base[mask], current[mask]
        an, bn = base_samples[:, mask], samples[:, mask]
        metrics = {
            "weight_added": (int(np.maximum(b-a, 0).sum()), np.maximum(bn-an, 0).sum(axis=1)),
            "weight_removed": (int(np.maximum(a-b, 0).sum()), np.maximum(an-bn, 0).sum(axis=1)),
            "weight_net": (int((b-a).sum()), (bn-an).sum(axis=1)),
            "pairs_added": (int(np.sum((a == 0) & (b > 0))), np.sum((an == 0) & (bn > 0), axis=1)),
            "pairs_removed": (int(np.sum((a > 0) & (b == 0))), np.sum((an > 0) & (bn == 0), axis=1)),
            "weights_changed": (int(np.sum(a != b)), np.sum(an != bn, axis=1))}
        for metric, (value, draws) in metrics.items():
            changes.append({"year": year, "scenario": scenario, "metric": metric, **describe(value, draws)})
        for i, j in zip(*np.where(mask & (base != current))):
            pair_rows.append({"year": year, "scenario": scenario, "edition_a": ids[i], "edition_b": ids[j],
                              "festival_a": names[i], "festival_b": names[j], "before": int(base[i,j]), "after": int(current[i,j])})
    subset = shows[shows.year == year]
    for kind, groups in [("shared_mbid", mbid_groups), ("spelling", spelling_groups)]:
        for label, members in groups.items():
            selected = subset[subset.act_key.isin(members)]
            if selected.empty:
                continue
            before, n = graph(selected.assign(identity_key=selected.act_key), "identity_key", ids)
            after, m = graph(selected.assign(identity_key="merged"), "identity_key", ids)
            a, b = projection(before, n)[mask], projection(after, m)[mask]
            group_rows.append({"year": year, "kind": kind, "group": label, "keys": " | ".join(members),
                               "weight_added": int(np.maximum(b-a, 0).sum()),
                               "weight_removed": int(np.maximum(a-b, 0).sum()), "weight_net": int((b-a).sum())})
    for key in sorted(risk_keys | conflict_keys):
        selected = subset[subset.act_key == key]
        counts = selected.groupby("festival").edition.nunique().to_numpy()
        contribution = int((counts.sum()**2 - (counts**2).sum())//2)
        group_rows.append({"year": year, "kind": "short_generic" if key in risk_keys else "conflicting_id",
                           "group": key, "keys": key, "weight_added": 0, "weight_removed": contribution, "weight_net": -contribution})
    np.savez_compressed(OUT / f"nulls_{year}.npz", **nulls)
    nulls_by_year[year] = {"ids": ids, "mask": mask, "originals": originals}

csv(pd.DataFrame(summary_rows), "projection_summary.csv")
csv(pd.DataFrame(changes), "projection_changes.csv")
csv(pd.DataFrame(pair_rows), "changed_pairs.csv")
contributions = pd.DataFrame(group_rows)
contributions["net_null_mean"] = contributions.weight_net
contributions["net_null_sd"] = 0
contributions["net_z"] = None
csv(contributions, "problem_contributions.csv")
csv(pd.DataFrame(diagnostics), "null_diagnostics.csv")
summary = {"input_rows": raw_count, "retained_rows": len(shows), "pandemic_rows_excluded": pandemic_rows,
           "rebroadcast_rows_removed": raw_count-len(shows)-pandemic_rows,
           "years_excluded": list(PANDEMIC), "n_act_keys": len(keys), "valid_mbid_rows": len(valid), "shared_mbid_groups": len(mbid_groups),
           "spelling_groups": len(spelling_groups), "short_generic_keys": len(risk_keys),
           "conflicting_id_keys": len(conflict_keys), "approved_groups": approved,
           "samples_per_scenario_year": SAMPLES, "input_sha256": hashes,
           "removed_stages_present": (DATA / "removed_stages.csv").exists(),
           "null_interpretation": "each scenario has its own fixed margins; change nulls compare independent draws, not known identity errors"}
if summary["removed_stages_present"]:
    removed = pd.read_csv(DATA / "removed_stages.csv", keep_default_na=False)
    csv(removed, "removed_stages_audit.csv")
    summary["removed_stage_shows"] = int(removed.n_shows.sum())
else:
    summary["removed_stage_shows"] = None
for path in inputs:
    assert hashes[str(path)] == hashlib.sha256(path.read_bytes()).hexdigest()
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True))

from figures import write_figures
write_figures(OUT)
from report import write_report
write_report(OUT)
print("analysis tables and figures saved", flush=True)
