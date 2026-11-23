We used the shared loader with site countries, excluding Leeds, rebroadcasts, 2020 and 2021.
We checked both margins in 200 curveball draws per year and used 5 fixed Louvain seeds.
Deletion ranges give observed values after dropping one festival at a time and refitting. The flagged Tomorrowland pair stays in the graphs.

1. In 2019, 5,679 acts and 30 editions made 6,930 bookings, with both margins checked against the input and every draw.
This counts the scale of the sampled lineups.
It misses repeated sets within an edition.

2. In 2019, 4,883 acts played one festival and the highest count was 9 for IDLES, with every degree bin matching its null mean exactly and SD 0 because each festival has one edition per year.
This measures how widely acts were booked across sampled festivals.
It misses bookings outside the sample.

3. The mean shared lineup fraction exceeded the null mean in 8 of 9 years, with 2019 at 36.7% and a deletion range of 34.6 to 37.6%.
It measures repeat bookings, weighting editions equally.
It misses which other festivals share those acts.

4. Edition links fell below the null mean in 9 of 9 years and act links in 9 of 9, with 2019 deletion ranges of 252 to 275 and 58,711 to 94,672 links.
These counts measure how broadly bookings connect editions and acts.
They miss how often individual pairs recur, which the edge weights record.

5. Modularity exceeded the null mean in 9 of 9 years, with a 2019 deletion range of 0.100 to 0.195 and mean seed agreement of 0.694 NMI.
They measure within-community concentration and agreement across runs.
They miss why editions cluster.

6. Country NMI exceeded the mean of 200 country label shuffles in 7 of 9 years, with 2019 at 0.416 and a deletion range of 0.340 to 0.459.
It measures how much the edition partitions align with host countries.
It misses the separate effects of geography, calendar and genre.

7. Co-membership exceeded the curveball mean in 17 of 36 year pairs, with pooled Jaccard 0.322 versus 0.286 and a deletion range of 0.291 to 0.383.
It measures repeat co-membership among pairs together at least once, using common festivals and matching seeds.
It misses festivals observed once and leaves repeat bookings as a possible explanation.

Open problems

Check country, calendar, genre, ownership and act identity as explanations for recurrence.
