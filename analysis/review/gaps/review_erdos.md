Review of erdos's reconciliation: `analysis/review/gaps/erdos.md`, `analysis/erdos/reconcile/run.py`, `comparison.csv`. Reviewed 2026-11-25. No files of theirs were edited. GVMH checker passes on `erdos.md` and `run.py`.

## Checked and fine

- **Full rerun.** I ran a copy of `run.py` with the output redirected to the scratchpad (otherwise it overwrites `comparison.csv`). The new `comparison.csv` is byte-identical to the committed one.
- **Cross-checks.** The festival-count gap, observed/expected and tilt equal Nandini's circuits csv to nine decimals (2 festivals: 0.454104361, 1.351771678, 2.148655164). The Wikipedia r values equal Watts's `country_gap.csv` for all seven groups (0.1943, 0.1372, 0.0806, 0.0566, -0.0286, 0.2075, 0.1778).
- **Figures in `erdos.md`.** All recompute from `comparison.csv`. Foreign-Wikipedia gaps sum to 2.716, so zero foreign is +1.51 (56%) and 10+ is -0.58. Watts's gaps sum to 2.302, so zero foreign is +0.88 (38%) and 10+ is +0.12. The unknown-country and unknown-MBID excess under Watts's null (+0.236, +0.202) is observed r minus null mean, as stated.
- **Code.** Both class schemes share the same 200 draws with observed as row 0; pair totals are asserted equal across the schemes; same-brand pairs are dropped; margins are checked on the first and last draw; mixing matrices are pooled over years and r is recomputed per draw.
- **Links in `erdos.md`** to circuits and Watts findings land on the right lines today (`#L12`, `#L7`, `#L75`, `#L3`).

## Actionable, ranked

1. **The new r excess values have no check beyond the null.** `comparison.csv` has no years-above-null count and no festival-deletion range for either scheme. The festival-count r excess (+0.315, +0.218, +0.066) and the Wikipedia r excess under the shared shuffle are new numbers, and the course page wants every measurement to carry a check with its result. Add per-year counts and deletion ranges (the pieces `stats` already computes per year) before any figure or paper sentence cites them.

2. **The 10+ tier is a negative gap, not "no effect".** Its same-country observed/expected is 0.77 against 1.12 across countries (tilt 0.69, gap -0.58, gap share -21%). Pair totals are conserved under the null, so this is the mirror of the zero-foreign excess. `erdos.md` says only that the tier is "inside the null band". Say that same-country pairs share fewer widely reached acts than chance, and that this follows from the totals, so a reader does not take it for an anti-national effect.

3. **"The analyses agree" mixes two shuffles.** The reconcile null uses 200 draws and full-lineup margins; Watts uses 2,000 draws and tier-specific margins. Null r means differ (-0.036 against -0.031) and the zero-foreign share is 56% against 38%. `erdos.md` mentions the baselines differ, but the opening sentence should limit "agree" to direction (strong at the narrow end, near zero at the wide end), not size.

4. **The gap shares are fragile as quoted.** They divide by a sum that includes the negative 10+ contribution and both unknown groups. If a share is quoted in the paper, state that denominator; otherwise drop the shares and keep the gaps.

5. **Reads the reach-1 class as a bin in the Wikipedia scheme.** The 26,581 single-festival acts are a zero-gap "1 festival" row in both schemes, so `gap_share` sums over a class that cannot contribute. Harmless, but exclude it from the table or label it as the zero-overlap bin so nobody reads the 0%.

6. **Import fragility.** `run.py` finds `common` only because importing `circuits/run.py` puts `analysis/` on `sys.path`. Add `ANALYSIS` to `sys.path` explicitly.

7. **Stale after Nandini's rerun.** `comparison.csv` still carries "3-4 festivals" and takes classes from `circuits.CLASSES`. When she relabels or drops the one-festival class (`review_circuits.md` points 4 and 6), rerun this script and the numbers in `erdos.md`.

8. **Line-anchored links.** The `#L` anchors break whenever the linked findings files are regenerated; link the file and quote the number.

## Round 2 (follow-up checked 2026-11-25, after the 12:01 `run.py` and 12:02 `comparison.csv` and `erdos.md`)

Checker passes on `erdos.md` and `run.py`.

Checked:
- The new columns are defined as stated. `r_positive_years` counts years where observed r exceeds that year's mean null r, over `r_defined_years`. `r_deletion_min` and `r_deletion_max` drop every pair involving one festival from the observed projection and from all fixed shuffles, then recompute pooled r minus the pooled null mean, over all 44 festivals (the same "fixed draws" rule as Watts).
- Independent recomputation (my own code, using only the circuits curveball sampler, with the same seed): festival-count "5+ festivals" gives r 0.0309, null -0.0348, excess 0.0657, positive in 9 of 9 years, deletion range 0.0555 to 0.0761. Foreign-Wikipedia "10 or more foreign" gives r -0.0286, null -0.0352, excess 0.0067, positive in 4 of 9 years, deletion range -0.0077 to 0.0289. All match `comparison.csv` to the printed digits.
- The numbers quoted in the revised `erdos.md` match the csv: 9 of 9 years and positive after every deletion for the three repeat-festival bins (minima 0.278, 0.191, 0.056); zero foreign 9 of 9 with +0.199 to +0.261; 10+ in 4 of 9 with -0.008 to +0.029; same-country 0.77 and cross-country 1.12 times expected; the 26,581-act row has undefined r.

Items from round 1:
- Point 1 (checks on the new r excess): closed.
- Point 2 (negative 10+ gap): closed; the text now explains it as an allocation within a fixed total.
- Point 3 ("agree"): closed; the opening sentence is limited to direction and the draw counts differ in plain view.
- Point 4 (gap shares): closed; shares are no longer quoted.
- Point 5 (one-festival row): closed; described as the zero-overlap accounting row.
- Point 6 (import path): closed; `ANALYSIS` is now on `sys.path`.
- Point 8 (line anchors): closed; links go to files.

Still open:
- **Label drift (point 7).** `comparison.csv` still carries "3-4 festivals", because `circuits/run.py` still defines `CLASSES` with the hyphen. Rerun after Nandini's relabel so the csv matches `erdos.md`, which already writes "3 to 4".
- **Minor.** The `gap` column has no per-year count or deletion range of its own in this csv (the circuits csv carries them for the festival-count scheme; the Wikipedia scheme's gap has none). Fine if the paper quotes r excess, not this gap, for the Wikipedia tiers; say so if it quotes the gap.

Verdict: pass, with the label rerun still to do after circuits changes.
