# Euler

Run from the repo root with pandas, numpy, scipy and matplotlib installed.

```
python analysis/euler/run.py
```

The audit reads the cleaned lineups, editions and festival headers. It also reads `removed_stages.csv` when available. The script checks input hashes after the run and writes outputs here without network requests.

We drop rebroadcasts and exclude 2020 and 2021 before learning mappings. This audit retains Leeds. CSV reads preserve literal values such as `NA`, and the script checks joins and edition-act uniqueness.

`resolve_acts` merges a spelling group when every key has the same sole valid UUID and clears the short-name and ID-conflict screens. It retains the original keys for audit and deduplicates each edition, preferring rows with valid IDs. `proposed_lineups.csv` and `proposed_mapping.csv` record the result. The group and key tables record the candidates and their individual effects.

The other scenarios are separate sensitivity checks. They merge all shared IDs, merge all spelling groups, split short or common names by festival, or split conflicting IDs. Their effects can overlap.

The edition projection connects different festivals. `projection_summary.csv` gives the number of pairs with shared acts and the sum of their weights. `projection_changes.csv` gives additions, removals and net changes. `changed_pairs.csv` records every changed weight.

Each year and scenario has 200 curveball draws over two chains with 50 burn-in sweeps and gaps of 5 or 10 sweeps. Every draw preserves both margins. `null_diagnostics.csv` gives chain checks, and the `nulls_*.npz` files contain the projected draws.

The change null compares independent draws for the original and alternative identities. It measures structural variation. The fixed act margins determine total pair weight and signed net change in these years, giving both zero null SD.

`run.py` regenerates the figures and findings. CSV display names use plain hyphens for dash characters, while calculations use the input keys.
