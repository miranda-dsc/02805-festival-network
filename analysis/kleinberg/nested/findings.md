# Lineup nestedness

We used 214 editions across 9 years, excluding 2020 and 2021. NODF uses acts booked at two or more editions in the same year. We compared observed scores with 400 curveball draws per year that preserve full lineup sizes and act booking counts, then applied the same act filter to each draw. Each festival deletion used 200 new draws for each affected year and kept the original result for unaffected years. The largest gap between deletion-chain means was 0.28 NODF points, so some small differences are sensitive to Monte Carlo variation. We retained Tomorrowland Winter and Weekend 1 as separate editions of the same brand. [NODF](https://doi.org/10.1111/j.0030-1299.2008.16644.x) [curveball](https://doi.org/10.1038/ncomms5114)

The yearly samples range from 11 to 35 editions, so the observed scores should not be read as a time trend.

| Year | Editions | Repeat acts | Matrix NODF obs / null mean / SD / z | Edition NODF obs / null mean / SD / z |
| --- | ---: | ---: | --- | --- |
| 2015 | 11 | 290 | 17.64 / 15.91 / 0.60 / 2.87 | 21.68 / 21.05 / 0.46 / 1.39 |
| 2016 | 20 | 433 | 13.53 / 13.26 / 0.49 / 0.57 | 11.68 / 12.30 / 0.24 / -2.52 |
| 2017 | 26 | 695 | 11.80 / 12.46 / 0.34 / -1.94 | 9.99 / 10.65 / 0.19 / -3.49 |
| 2018 | 35 | 614 | 7.21 / 7.98 / 0.21 / -3.69 | 6.93 / 7.80 / 0.13 / -6.74 |
| 2019 | 30 | 796 | 10.25 / 12.95 / 0.35 / -7.77 | 8.99 / 9.92 / 0.15 / -6.15 |
| 2022 | 22 | 714 | 10.92 / 13.82 / 0.36 / -7.94 | 11.47 / 12.21 / 0.22 / -3.34 |
| 2023 | 23 | 529 | 7.28 / 9.53 / 0.37 / -6.12 | 8.60 / 9.47 / 0.16 / -5.29 |
| 2024 | 24 | 577 | 10.36 / 13.13 / 0.44 / -6.35 | 9.93 / 11.29 / 0.24 / -5.78 |
| 2025 | 23 | 662 | 11.02 / 13.96 / 0.43 / -6.85 | 10.72 / 12.45 / 0.28 / -6.21 |

1. The matrix was less nested than the shuffle in 7 of 9 years, or 6 to 8 years after deleting any one of 44 festivals across all its editions. The count was 5 of 9 years when the null fixed repeat-act lineup sizes. Matrix NODF measures how often the smaller of two lineups, or the less booked of two acts, shares its partners with the larger one. It misses one-off acts and gives little weight to edition pairs.

2. Edition NODF was below the null mean in 8 of 9 years, or 7 to 9 after festival deletion, and in 8 of 9 years when the null fixed each edition's repeat-act lineup size. Lower scores indicate less nesting than expected under the shuffle. Edition NODF measures the fraction of the smaller repeat-act lineup contained in the larger one, giving equal-size pairs a score of zero. It leaves out one-off acts and cannot identify what drives the booking differences.

The top 5% of repeat acts accounted for 20.0% to 28.8% of shared-act counts across edition pairs, or 15.7% to 29.5% after festival deletion, a descriptive share fixed by act booking counts.

Open problems

Test whether the most booked acts disproportionately connect festivals across countries or genres given their booking counts.
