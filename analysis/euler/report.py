import json
from pathlib import Path

import pandas as pd


def write_report(out):
    summary = json.loads((out / "summary.json").read_text())
    projections = pd.read_csv(out / "projection_summary.csv")
    editions = pd.read_csv("data/processed/editions_clean.csv")
    counts = {year: editions.loc[editions.year == year, "edition"].nunique() for year in (2019, 2023)}
    changes = pd.read_csv(out / "projection_changes.csv")

    def change(year, scenario, metric="weight_net"):
        row = changes[(changes.year == year) & (changes.scenario == scenario) & (changes.metric == metric)].iloc[0]
        return int(row.observed)

    def score(year):
        return projections[(projections.year == year) & (projections.scenario == "baseline") & (projections.metric == "positive_pairs")].iloc[0]

    table = ["| Year | Observed pairs | Null mean | SD | z |", "| :--- | ---: | ---: | ---: | ---: |"]
    for year in (2019, 2023):
        row = score(year)
        table.append(f"| {year} | {int(row.observed)} | {row.null_mean:.2f} | {row.null_sd:.2f} | {row.z:.2f} |")
    if summary["removed_stages_present"]:
        stage = f"The stage audit lists {summary['removed_stage_shows']} removed shows. Their music status still needs checking."
    else:
        stage = "The missing stage audit leaves the number of removed music shows unknown."

    text = f'''We audited {summary['n_act_keys']:,} act keys after dropping {summary['rebroadcast_rows_removed']} rebroadcast rows and excluding 2020 and 2021. This audit retains Leeds. The two projections have {counts[2019]} editions in 2019 and {counts[2023]} in 2023. Each scenario has 200 curveball draws across two chains, with both margins checked.

{chr(10).join(table)}

Pair counts record whether editions share an act. Pair weights count how many they share. The fixed margins determine total pair weight for each scenario in these years.

1. We found {summary['shared_mbid_groups']} IDs used by multiple keys. Rebuilding the 2019 projection after merging all of them added {change(2019, 'all_shared_mbids')} shared-act links. This measures sensitivity to reused IDs. It leaves the validity of individual IDs unresolved.

2. Merging the {summary['spelling_groups']} spelling groups added {change(2019, 'all_spellings', 'pairs_added')} pair edge in 2019 and {change(2023, 'all_spellings', 'pairs_added')} in 2023, checked against the changed pairs. This measures sensitivity to spelling normalization. It can also merge distinct acts with similar names.

3. Splitting short or common names by festival removed {-change(2019, 'short_generic_split')} links in 2019. Splitting conflicting IDs removed {-change(2019, 'conflicting_id_split')}. Rebuilding the projection checks how much sharing could come from ambiguous keys. The split cannot recover distinct acts already collapsed within an edition.

4. The guarded fix accepted {len(summary['approved_groups'])} spelling groups and added {change(2019, 'proposed_fix')} weighted links in 2019. The changed pairs record {change(2019, 'proposed_fix', 'pairs_added')} new and {change(2019, 'proposed_fix', 'pairs_removed')} removed pair edges. This measures a correction supported by a shared ID. It misses aliases without matching IDs.

{stage}

Open problems

Verify suspect IDs, hand-label ambiguous names and recover the stage audit and raw shows. The candidate groups overlap, so their effects cannot be added.
'''
    (out / "findings.md").write_text(text)


if __name__ == "__main__":
    write_report(Path("analysis/euler"))
