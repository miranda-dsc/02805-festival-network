### National share with a matched exact-k null

We used `analysis/common.py` and 200 draws per year from `analysis/circuits/run.py` at commit `ead7208`. We checked lineup sizes and act degrees on the first and last draws and reproduced the original edition-weighted results. We counted each festival once per act and measured the share of its festivals in its most-played country.

The exact-k cohort comprised acts booked at k editions across k distinct festivals in the observed data. For each act we accepted only pooled draws with k distinct festivals. We averaged accepted shares within act, then averaged acts equally. Acceptance was per act, so these are conditional marginal means. The CSV gives accepted counts and leaves the joint null band blank for exact k. Observed no-return acts may differ from returners.

| Festivals | All acts | Observed | Null mean | Excess | Exact k acts | Observed | Matched mean | Excess |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 3,144 | 0.785 | 0.716 | +0.069 | 2,263 | 0.777 | 0.717 | +0.060 |
| 3 to 4 | 1,681 | 0.734 | 0.658 | +0.076 | 927 | 0.718 | 0.657 | +0.061 |
| 5 or more | 887 | 0.667 | 0.615 | +0.053 | 239 | 0.654 | 0.618 | +0.035 |

The matched null gave positive excess in all three classes and the smallest excess in the broadest class. Matching raised that class's exact-k excess from +2.3 to +3.5 percentage points. The median accepted count was 111 of 200 for that class, with a minimum of 8. The two narrower classes were nearly tied on the exact-k check. These are point estimates of booking concentration, with limited precision for high k. [National share](national_share.csv)

### Tilt within tag status

We used strict tags from `analysis/watts/genre_profiles.py` and held observed reach and tag assignments fixed. We counted each stratum's shared acts in the same observed and shuffled lineups. Tilt divided the same-country observed-to-expected ratio by the different-country ratio. Festival deletions kept pair expectations fixed.

| Festivals | Untagged tilt | Deletion range | Strict-tagged tilt | Deletion range |
| --- | ---: | ---: | ---: | ---: |
| 2 | 3.20 | 2.90 to 3.92 | 1.07 | 0.97 to 1.26 |
| 3 to 4 | 2.81 | 2.65 to 3.38 | 1.22 | 1.10 to 1.32 |
| 5 or more | 2.46 | 2.19 to 2.87 | 1.15 | 1.03 to 1.29 |

Untagged acts had stronger relative tilt within each reach class. Their same-country ratios were close, at 1.52 to 1.57, and their different-country ratio rose from 0.48 to 0.64. The falling tilt mainly reflected the shrinking different-country deficit. Strict-tagged tilt showed no monotone reach gradient. The original result that the broadest class generated 49% of the absolute gap used shared-act counts and still applied. [Tilt and counts](tilt_by_tags.csv) [Circuits findings](../../circuits/findings.md)

Strict tag coverage rose from 34% to 46% to 65% across reach classes. Among acts with mapped artist country and an MBID, the share with 10 or more foreign Wikipedia editions rose from 21% to 27% to 41%. Missing MBIDs accounted for 20.5%, 11.8% and 6.1% of the full classes. All 5,712 repeat-festival act keys joined to the tier export, including both unknown categories. [Tag cross-tab](reach_by_tags.csv) [Wikipedia cross-tab](reach_by_wikipedia.csv)

### Outside GB

We checked observed overlaps against the shared loader and used the fixed expected counts from `analysis/circuits/pairs_by_reach.csv`. Pooled ratios covered 57 pair-years and 21 distinct festival pairs. For each deletion we removed that country's same-country pair-years. Columns give observed-to-expected shared-act ratios among the pairs that remained.

| Country removed | Pair-years | Distinct festival pairs | 2 festivals | 3 to 4 | 5 or more |
| --- | ---: | ---: | ---: | ---: | ---: |
| None | 57 | 21 | 6.92 | 3.07 | 0.60 |
| Belgium | 28 | 11 | 13.87 | 5.36 | 1.00 |
| Germany | 55 | 20 | 6.80 | 3.15 | 0.58 |
| Spain | 40 | 15 | 4.83 | 2.35 | 0.54 |
| France | 50 | 18 | 6.29 | 2.72 | 0.51 |
| Poland | 55 | 20 | 7.00 | 3.10 | 0.60 |

The pooled observed and expected counts were 80 and 11.56, 89 and 29.02, and 52 and 87.13. Both narrower classes stayed above chance under every country deletion. Removing Belgium left 29 observed against 28.89 expected for the broadest class. Its pooled deficit was specific to Belgium's contribution. With only 21 distinct pairs, the remaining estimates described this sample. [Country deletions and counts](outside_gb_country_deletions.csv) [Pooled totals](outside_gb.csv) [Festival deletions](outside_gb_deletions.csv)

### Glastonbury 2025

The coverage outlier was `g2025`, one Glastonbury edition starting 25 June 2025 in `common.load()`. The Clashfinder ID and official lineup described the festival-wide programme for that edition. The loader retained 2,194 distinct billing keys, including entries such as Soho School of Burlesque Class. The median was 162.5 keys per edition. The 2,194 keys included 224 with English intros. The original raw JSON was unavailable, so the precise source revision and stage-level cleaning could not be checked. [Coverage export](../../newman/wikitext/edition_coverage.csv) [Clashfinder page](https://clashfinder.com/s/g2025/) [Official Glastonbury programme](https://glastonburyfestivals.co.uk/line-up/line-up-2025/)

The edition was in 22 of 2,610 retained full-lineup pair rows (0.84%) and 22 of 253 in 2025 (8.70%). Its pairs supplied 386 of 11,072 observed shared-act counts overall (3.49%), including 386 of 1,468 in 2025 (26.3%). The fixed null expected 559.45 shared acts across these 22 pairs. Excluding those rows, the 2025 raw same-country minus different-country mean excess moved from +2.99 to +2.98 acts per pair. This held pair expectations fixed and measured the contribution of the edition's rows. [Pair influence](largest_edition_pairs.csv)
