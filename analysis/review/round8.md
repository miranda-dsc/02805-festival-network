# Round 8: open fixes

The checker passes on `analysis/watts/reach` and `analysis/newman/wikitext`, with no dashes. I rebuilt r from the lineups on the new `tiers.csv` (14:03:27). All seven groups match `country_gap.csv` in act count and r: +0.194, +0.137, +0.081, +0.057, -0.029, +0.207 and +0.178.

## Part A: analysis/watts/reach

Landed: official-only home languages, XE and blank codes in the unknown group, the distinct-festival null with its band, table headers for r excess and OLS units, the shared-burn-in and below-zero null notes, the raw gap per pair moved to a CSV, and the monotone r excess sentence (it holds: 0.226, 0.165, 0.116, 0.087, 0.009 in the main run).

Open:
1. **Miss leakage has no bounded rerun.** The text now says 4 of 18 sampled 0 foreign acts had a foreign article, which is right, but the seven-page rerun still moves only 4 acts. Move a random 22% and a random 45% of the 1,550 no-article acts into 1 foreign, rerun the 0 foreign and 1 foreign tiers, and report r. Until then, drop "more mobile acts" or label it a guess. The headline 35% also still counts home-language articles that do not change a tier.
2. **The monotone sentence has no numbers.** Give the r excess values for the three rules, and say the 10 or more tier is inside its band.

## Part B: analysis/newman/wikitext

Landed: GB-only term comparison with a label permutation, examples ranked by rate, the tag-agreement null (stratified by lineup size), the 18 fills checked, the 50 disagreements checked, and a stricter random audit. `findings.md`, `tier_terms.csv` and `origin_notes.md` are unchanged since my last read (14:05), so the follow-up points from that read are still open:

1. **"None passed" misleads.** The max-gap test uses raw rate gaps, which frequent words dominate. Per term, 96 of 649 words have p below 0.05, and a Benjamini-Hochberg pass over the stored p values keeps 21 at q below 0.05 (british, known, england, dj, london, based, radio and others). Show raw p and q next to the max-gap p, rename the "Adjusted p" column to "Max-gap p", and state the reading: within GB, the zero-foreign tier says British, England and London more.
2. **Tag agreement needs its excess.** Observed minus null mean is 0.18 to 0.40 by year. The null alone reaches 0.32 to 0.60. Say p = 0.005 is the floor for 200 draws.
3. **Single reader and no intervals.** Add Wilson intervals (27 of 30: about 74% to 97%; 28 of 50: 42% to 69%; 15 of 18 fills: 61% to 94%) and have a second member label about 20 intros blind.
4. **Ten new demonym predictions are unchecked.** Four disagree with MusicBrainz (enji, kiasmos, salvatore ganacci, sampa the great), and agreement fell from 95.2% to 95.0%. Check the ten or revert.
5. **MusicBrainz agreement understates the extractor.** About 56% of sampled disagreements favour Wikipedia and 8% favour MusicBrainz. Say so, and split item 3 (nine numbers in one paragraph).
6. **`tier_terms.png` has no caption.** Explain the red and blue labels (the four largest gaps per side, none significant after the max-gap test) and fix the axis that mixes a 0 tick with 10^0.

Fixes open: Part A 2, Part B 6.
