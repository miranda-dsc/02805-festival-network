We used 2,633 English introductions across bookings at 214 editions. Median edition coverage was 28% of booked acts, and 451 intros came from ambiguous MusicBrainz matches. The shared loader excludes Leeds, rebroadcasts, 2020 and 2021.

1. Wikipedia TF-IDF and strict MusicBrainz tag cosines had yearly Spearman correlations of 0.55 to 0.79 across 2,613 pairs, with festival deletion bounds of 0.45 to 0.81. The yearly null means ranged from 0.32 to 0.60, and the observed correlations exceeded those means by 0.18 to 0.40. Observed correlations exceeded all 200 draws in every year, giving the minimum attainable p of 0.005. The curveball null trades Wikipedia-covered acts within year and lineup-size thirds, keeping their booking counts within each third and every edition's number of covered acts. We remove shared acts before each cosine and hold the observed tag similarities fixed. This captures agreement between two text measures beyond what lineup size and intro coverage alone reproduce. It misses undocumented acts and cannot distinguish genre from the language of geography and careers. [Tokenization](https://sunelehmann.com/socialgraphs2026-web/weeks/week5.html) [TF-IDF](https://sunelehmann.com/socialgraphs2026-web/weeks/week6.html)

2. A 0.10 increase in Wikipedia cosine corresponded to 1.28 more shared acts above the 9,999-draw curveball mean, positive in all nine years and 0.96 to 1.82 after festival deletion with fixed pair baselines. Strict tags gave 1.36 on the same pairs. The fit excludes the three same-brand pairs and adjusts for country within year and day-gap bins. This captures whether lineups share more acts than expected when the acts unique to each lineup have similar intros. It misses whether genre, geography or editorial coverage drives that association.

3. We retained 15 of 18 proposed fills after hand reading (83%, 95% Wilson interval 61% to 94%). Only 28 of the 504 Wikipedia records without a MusicBrainz country had English text, so the retained fills cover 3.0% of the gap. The three unresolved fills remain blank. This captures where an intro supplies a single country missing from MusicBrainz. It misses acts without an English intro or a clear origin statement. [Named entities](https://sunelehmann.com/socialgraphs2026-web/weeks/week7.html)

   The demonym expansion added ten candidates. We hand-checked all ten and retained seven, including Enji and Sampa the Great, whose intros support countries different from MusicBrainz. We left Kiasmos, Salvatore Ganacci and Solomun blank because their intros give two countries without a clear tie-breaker. The exported CSV now has 2,110 country codes and agrees with MusicBrainz on 1,993 of 2,095 paired codes (95.1%, Cohen's kappa 0.939).

   The strict reading supported 27 of the original 30 random predictions (90%, 95% Wilson interval 74% to 97%). Among 50 sampled disagreements, it favored the Wikipedia extraction in 28 (56%, 95% Wilson interval 42% to 69%) and MusicBrainz in 4 (8%), with 18 unresolved. This measures support in the retrieved intro. It leaves biography and article matching outside the audit, and agreement with MusicBrainz alone counts some text-supported predictions as errors.

4. The original zero-foreign tier had English text for 256 of 1,884 acts. After narrowing home languages it has 231 of 1,856, compared with all 1,153 acts in the highest tier. We compared 165 GB intros in the lowest tier with 424 in the highest, using 7,641 and 29,345 words. Across 649 terms, 96 had raw permutation p below 0.05 and 21 had Benjamini-Hochberg q below 0.05. British, England and London were more frequent in the zero-foreign tier and passed that check. The max-gap test uses the largest raw rate gap per draw and is driven by frequent terms. This captures which terms have different rates within the GB subset. It misses acts without English intros and cannot separate reach from genre, career length or editorial coverage. [Group comparison](https://sunelehmann.com/socialgraphs2026-web/weeks/week6.html)

Uses per 10,000 words.

| Term | Zero foreign | 10 or more | Raw p | BH q | Max-gap p |
| --- | ---: | ---: | ---: | ---: | ---: |
| British | 75.9 | 44.6 | 0.0005 | 0.0203 | 0.1535 |
| known | 86.4 | 55.5 | 0.0005 | 0.0203 | 0.1615 |
| England | 36.6 | 7.5 | 0.0005 | 0.0203 | 0.2020 |
| DJ | 48.4 | 20.4 | 0.0005 | 0.0203 | 0.2410 |
| albums | 24.9 | 56.6 | 0.0015 | 0.0464 | 0.1425 |
| album | 69.4 | 97.1 | 0.0735 | 0.4077 | 0.2485 |
| studio | 17.0 | 39.9 | 0.0050 | 0.0983 | 0.4830 |
| vocals | 39.3 | 59.6 | 0.1115 | 0.5244 | 0.6330 |

We read examples ranked by each term's rate within the intro, breaking ties by longer text. Heartworms uses known to introduce a stage name, and Charlotte Devaney lists DJ among several roles. Hurts and Saxon enumerate albums, while Black Country, New Road lists vocals in its member credits.

Figure. Red and blue label the four largest rate gaps toward the zero-foreign and high tiers, respectively. None passed the 5% max-gap test using 1,999 GB tier-label shuffles.
