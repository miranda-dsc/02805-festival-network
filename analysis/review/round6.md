# Round 6: Wikipedia reach

Checked `src/04_wikipedia.py`, `act_wiki.csv`, the cached API replies, `analyze.py`, the findings, `audit.csv` and the PNG. The checker passes on the reach folder.

## Fixes, most important first

1. **The 1 language tier does not mean national.** 245 of its 330 acts have the English article. 230 of the 330 have an artist country where English is the home language (171 GB, 28 US, rest IE, AU, CA, NZ). For a UK act an English article says nothing about reach abroad. So 1 language is "English only", the same as the no-article tier for reach beyond home. Build tiers from articles outside the act's home languages instead. Counts among the 4,311 acts with a known artist country, using official or majority languages from babel as home: 0 foreign: 1,884; 1: 292; 2 to 4: 545; 5 to 9: 448; 10 or more: 1,142. A cheaper version is non-English sitelinks (0, 1 to 4, 5 or more), counts 2,263, 304, 226, 208, 161 and 1,653 for 0, 1, 2, 3, 4 and 5 or more. Rerun the gap on either. Acts with no artist country (504) need a stated rule.
2. **Excess per pair is not comparable across tiers; lead with the ratios.** Every tier uses the same 2,610 pairs, including pairs where one edition has no act from the tier. Expected same-country overlap is 2.00, 0.37, 1.49, 1.41 and 0.81 acts, so the excess scales with how many tier acts there are. The figure ranks tiers by absolute excess, and the deletion ranges are as narrow as the tier is thin (1 language and Unknown look tight for that reason). Put observed over expected and gap over expected first, and plot one of them. Even the ratios are not monotone (0.41, 0.53, 0.57, 0.11, 0.32). The supported claim is only that the 10 or more tier is lower, with 6 of 9 years positive and a deletion range of -0.02 to +0.30.
3. **Unknown MBID is a match-failure group, not a reach tier.** It holds the 897 acts with no MBID (unmatched, conflicting, low-vote ambiguous). Its 0.0% strict tagging is true by construction. Show it on its own line, apart from the ordered tiers in the table and the figure.
4. **Audit precision is for the Q-id join only.** The draw of 30 reproduces from seed 2805: 29 correct, 1 wrong (Wilson 83.3% to 99.4%). The mix is 14 name, 12 clashfinder id and 4 ambiguous, so it says almost nothing about ambiguous matches. The one wrong act is a clashfinder id match. Nothing checks the no-article side, which is 2,018 acts. Hand check about 20 of them for an article we missed and report that rate as the miss check.
5. **Q-id join and sitelink filter hold.** Findings:
   - All 4,792 MBIDs are in the dump.
   - 23 acts share an MBID, so 23 Q-ids repeat across act keys.
   - Wikidata redirects work: 8 cached entities carry a redirect and are keyed by the requested id, so the lookup finds them. 3 Q-ids are missing and 68 have no language sitelinks. Together with 5 multiple Q-ids they fall into No article.
   - The filter counts 364 language Wikipedias. 16 of those are closed, but no act has one. `simple` is counted (610 acts); dropping it moves 5 acts across a tier boundary.
   - Say the last two points in the Methods text.
6. **The null per tier is the same as `tagged.py`.** It imports `null_pairs` and `country_gap`, uses 2,000 draws, drops same-brand pairs as `tagged.py` does, and gets Leeds removed through `common.load`. Tier membership follows fame, which follows edition count, and curveball keeps each act's count, so the fixed-degree null is fair within a tier. The strict rerun changes who is in each tier (2,018 to 1,828 in No article), so call it a sensitivity check and not a second method.
7. **Text and style.**
   - Name the null once in the caption of the gap table, not in four column headers. The one-country share has a two-edition control but no null; say that.
   - Line 3 says "four language tiers" above a five-row table.
   - The Majestic paragraph is a fragment. Join it to the audit paragraph and add that it was a clashfinder id match.
   - Add the audit method mix.
   - Say "five acts with several Q-ids" instead of "the script leaves multiple Q-ids unresolved".
   - Give the PNG a caption sentence: the bars are a festival-deletion range, not an interval.

## Course page checks

- Every measurement has a check: the null, the exact-2-edition control, strict matching and the audit.
- Every section has a capture sentence and a miss sentence, except the sentence added under the table after fix 1.
- The voice is participant style, with no dashes and no grading talk.
