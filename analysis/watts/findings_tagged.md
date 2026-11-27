Tagged and untagged act-edition subsets use separate within-year curveball nulls with 2,000 draws per year. Each null preserves the act edition counts and edition lineup sizes inside that subset.

1. Within strict tagged acts, the date-adjusted same-country excess was +1.03 shared acts per pair, with festival deletions from +0.72 to +1.27. It was positive in 9 of 9 years, with 2018 at 0.030 acts.
   This measures the same-country gap within year and day-gap bins among tagged acts.
   It misses acts without usable MusicBrainz tags, and subset gaps do not sum to the full-lineup gap.

2. Within ambiguous-included tagged acts, the date-adjusted gap was +1.25, positive in 9 of 9 years, with 2018 at 0.009 acts.
   This measures the same pattern when ambiguous act matches are included.
   It misses errors among ambiguous matches and does not establish that the ambiguous identities are correct.

3. National concentration by status and repeat-festival control is in national_share.csv. For acts at two or more festivals, tagged acts had mean one-country share 0.70; too-few-vote acts had 0.85.
   This measures how much of an act's observed editions are in its most common country.
   It captures concentration across the observed editions and acts appearing at two or more festivals, with exact edition-count rows as a check. It misses festival-level booking opportunities.

### Open problems

Exact edition-count and distinct-festival controls are included in national_share.csv.
