# Round 4: analysis/watts/tagged.py

Short answer: the split is valid and the deletion range is right. The years-positive count uses a different estimand from the headline gap, and the status label in national_share is too loose.

## Restricting lineups before the null

Valid. Tagged status is a property of the act, not of the outcome. Curveball on the subset keeps each act's number of editions and each lineup's size inside that subset, so it answers "do same-country pairs share more tagged (untagged) acts than chance, given how many each lineup has". Two cautions:

- The two parts do not add up. Strict gaps are 1.03 and 1.90, which sum to 2.93, against about 2.5 for the full null. The subset null fixes how many tagged acts each lineup holds; the full null does not. Say "within the tagged acts" and do not add the parts.
- The gaps are in excess acts, and the two parts differ in size (6,365 and 4,707 shared acts). Excess divided by null mean would be a fairer comparison of strength.

The genre similarity comes from pairs.csv, which uses the full tagged lineups. For the tagged part the sound predictor and the outcome use the same acts (the circularity from the earlier review). For the untagged part it is a different set of acts. Both are fine, but the untagged sound row means "sound of known acts predicts shared obscure acts", and the text should say that. All 2,613 pairs merge with no missing similarity.

## influence()

Used right. I passed the same arguments and checked: x is the same_country float on the reset index, strata are [year, days_bin], and the deletions come from detail[i]["excess"] with the null held fixed. The deletion range is the fixed-effect slope with each festival removed. No deletion came out undefined (44 festivals, 0 NaN), so min and max are safe. Recomputed at 400 draws: tagged 0.71 to 1.27, untagged 1.54 to 2.19, same as the file.

## Years positive

Not the same estimand. country_gap takes a raw difference of means by year, while the headline gap and sound.fit use within-day-bin slopes. At 400 draws I computed both:

| subset | raw positive | within day bins positive |
| :--- | ---: | ---: |
| strict tagged | 9 | 9 |
| strict untagged | 9 | 9 |
| ambiguous tagged | 8 | 9 |
| ambiguous untagged | 9 | 9 |

The counts barely differ, but 2018 is close to zero for tagged acts (0.03 strict, 0.00 ambiguous, raw -0.02). So "9 of 9" for tagged is true only by a hair, and the 8 versus 9 in the ambiguous row is a sign flip around zero. Use the within-day-bin slope per year so the count matches the headline, and report 2018 as about 0. The other eight tagged years run 0.5 to 1.8.

## national_share status logic

Mostly matches genre_profiles MATCHED: tags are filtered to id, name and alias, and "matched, no tags" uses the same tuple. Two problems:

- "not matched" is really "not strictly matched". It holds 1,710 ambiguous acts (815 with tags, 895 with too few votes), 12 conflicting, 1,413 unmatched. Share of dates in one country is 0.77 for the ambiguous group, 0.90 for the vote-poor ones and 0.98 for unmatched, so the pooled 0.90 hides a spread. Rename the row or split it.
- "dates" are editions, so an act at one festival in two years counts as one country twice. Tagged acts have more editions (4.3 against 3.1). I checked at fixed counts: at 2 editions the share is 0.90 (matched, no tags) against 0.79 (tagged), at 5 or more 0.89 against 0.70. Among acts at two or more festivals the share is 0.83 to 0.85 untagged against 0.69 to 0.73 tagged. The gap holds, so the claim stands. Add one of these controls to the file; the plain means would not survive a reader who asks about repeat festivals.

## Smaller points

- SAMPLES is 2,000 here against 9,999 in run.py. Fine for means; do not quote tails from this file.
- The null is run per year with the seed from run.py, so tagged_split.csv is reproducible.
