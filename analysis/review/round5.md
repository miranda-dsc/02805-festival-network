# Review round 5

The checker passes on all eight files (the three analyses, watts/tagged.py and their findings). Numbers below are recomputed from the output files unless I say otherwise.

## 1. granovetter/launch

**The UK result is mostly UK coverage and a country-blind null.**
- GB is 114 of 214 editions (53%), 67% of bookings and 55% of the 2,077 breakouts.
- The launch null trades only inside a country and year, so excess sums to zero within every country (checked: GB 1,141 observed, 1,141 expected). It ranks GB festivals against each other. It cannot show that GB launches acts more than other countries.
- 42 of 72 country-years have one edition, so those festivals score zero by construction. Reading, Great Escape and Download rank high partly because GB has 23 festivals to compete with. Say "within GB" in the text.
- Lead and lag: the year-swap null ignores country. GB festivals sum to +1,038 net-lead excess under it and +232 under the calendar null. GB has 15 of 23 festivals positive, non-GB 7 of 21. Use the calendar null, or add a year swap restricted to country, for any claim about the UK. Great Escape is +712 under one null and +1,320 under the other, so name which null each number uses.

**Fairness of the nulls.**
- The year swap keeps each act's years and each festival's total, but not edition sizes (I measured a mean change of 7.9 acts on a mean of 252, up to 36%). The findings now say so; keep that sentence.
- Net leads count every festival pair of an act, so heavy acts weigh quadratically. Say what the unit is.
- The ratio to expected is the fairer ranking (Download 2.8 times, Reading 2.1 times). Add it next to the excess.
- Tomorrowland weekend 1 is still unmasked in the launch table (rank 4, +40, 3 of 5 years). Flag it.

## 2. newman/text

- **Circularity, checked.** I reran the tag clustering against the Louvain partitions with only acts booked at one edition in the year, so no act that creates an edge. Agreement still beats the shuffle at p below 0.05 in 6 of 9 years (2016, 2017, 2018, 2022, 2023, 2025; 2019 at 0.09, 2024 at 0.10, 2015 at 1.0). Shared acts only give 7 of 9. Report this in the findings; it answers the "shared artists" caveat.
- **Deletions are weaker than the text suggests.** Pooling the min and max across years ("-0.05 to 0.58") hides that only 4 of 9 years stay positive under every deletion (2016, 2018, 2019, 2023). Give the per-year count. Country agreement is never significant (0 of 9) and below the null in 5 years; say it plainly.
- **Cluster quality.** Silhouette is 0.22 to 0.39 (weak). Clusters are lopsided (2015: 10 and 1; 2024: 4 and 20; 2023 has 6 clusters of 23 editions). Add cluster sizes to the table.
- **Tag Jaccard of 0.50.** With three tags, 0.50 means one tag swapped in the worst deletion. It is a coarse measure. The top tags are the common ones (indie rock 98, electronic 80, rock 60 of the community lists), so "distinctive" is too strong. Take the idf from edition profiles.
- **Bridges.** 4 of 8 year pairs have p below 0.05. 2022/23 is -0.06 and 2015/16 rests on 7 festivals. "7 of 8 beat the mean" is nearly uninformative; lead with the 4. Rock for People tops the list partly because the list sorts by top years; show its 8 years beside the rest.
- The figure is readable and the titles are short.

## 3. kleinberg/nested

- NODF reproduced by brute force earlier; margins fixed; the repeat-act null (5 of 9 for matrix NODF, 8 of 9 for edition NODF) and the chain gap (0.28) are now in the text. Good.
- **The top-5% column is degenerate**: SD 0 and z undefined in every row, as the text says. Move it out of the NODF table into one descriptive sentence, or drop it. It is not a test, so it carries no check.
- Observed NODF is not comparable across years (11 to 35 editions); say not to read a trend.
- Item 1 still reads awkwardly ("smaller lineups and less-booked acts share their partners with larger lineups and more booked acts"). Say "less nested than the shuffle".

## 4. watts/tagged.py

- **Fix verified.** The yearly gaps now use the within-day-bin slope. Tagged acts are positive in 9 of 9 years, with 2018 at +0.03 (strict) and +0.01 (with ambiguous). Report 2018 as about zero. Deletions use the fixed null correctly.
- `excess_over_null` divides the gap by the mean of the same-country and different-country null means. Use the same-country null mean, and name the column.
- `findings_tagged.md` item 3 says the shares do not control for edition counts, and the open problem asks for exact edition counts, but `national_share.csv` already has both. Update both sentences.
- The exact-count controls hold the earlier result: at 2 editions, 0.79 tagged against 0.90 matched without tags; at 5 editions, 0.73 against 0.90.

## 5. GVMH

Passes everywhere. Things the checker cannot see: the awkward wording in nested item 1 and the "distinctive tags" claim in newman/text item 1. Scripts still print capitalised messages ("Loaded", "Scored"), which matches Miranda's style.
