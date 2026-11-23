We kept Reading, dropped Leeds and rebroadcasts before shuffling, and excluded 2020 and 2021. The 2,613 pairs use venue countries and a baseline of 9,999 degree-preserving draws per year. The excess was +0.18 acts at 0 to 7 days and +0.69 at 8 to 14 days. We gave each tagged act equal total weight, used genre counts where present and tag counts otherwise, and removed shared acts before comparing the two edition TF-IDF profiles.

We flagged 127 of 214 editions below 50% tag coverage with ambiguous matches and 175 without them, and kept them when both sides had tags after removing shared acts. Median full-lineup coverage was 47% and 35%, respectively. The models compare excess shared acts within year and day-gap bins on 2,610 and 2,610 pairs, excluding same-brand pairs. The country comparisons before and after adjustment use the same pairs within each match policy.

1. The same-country gap moved from +2.52 to +2.05 (+1.68 to +2.48 after festival deletions, positive in 9 of 9 years) with ambiguous matches and from +2.52 to +2.04 (+1.66 to +2.47 after festival deletions, positive in 9 of 9 years) without them.
   This measures the country gap at the same genre similarity within year and date-gap bins.
   It misses finer timing, touring routes and untagged acts.

2. Each 0.10 higher cosine similarity corresponded to +1.34 (+1.21 to +1.40 after festival deletions, positive in 9 of 9 years) excess acts with ambiguous matches and +1.36 (+1.24 to +1.42 after festival deletions, positive in 9 of 9 years) without them.
   This measures the association between overlap and the sound of the acts unique to each lineup after accounting for country.
   It misses shifts in an act's sound over time and underrepresents acts booked at only one festival.

### Open problems

Audit ambiguous artist matches and test whether broader tag coverage changes the estimates. Genre profiles use the available MusicBrainz tags for each act across the full study period.
