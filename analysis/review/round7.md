# Round 7: reach tiers and Wikipedia text

The checker passes on `analysis/watts/reach` and `analysis/newman/wikitext`. The course anchors cited in both findings exist on the week 3, week 5, week 6 and week 7 pages.

## Part A: analysis/watts/reach

Verified:
- **Weighted r.** I rebuilt the observed r from the lineups: sum the shared acts of each same-year, non-same-brand pair into a symmetric country matrix, then (trace minus marginal agreement) over (1 minus marginal agreement). It gives +0.203 for 0 foreign and -0.029 for 10 or more, matching `country_gap.csv`.
- **Null.** It reuses the watts trades with the observed lineup as row zero. Each draw asserts that every act's degree and total pair overlap are unchanged, which matches `tagged.py`. The null r is about -0.03 in every tier.
- **Round 6 fixes.** All seven landed: foreign-language tiers, ratios first, unknown groups apart, the miss audit, the Methods paragraph, strict rerun as sensitivity, and the text tidy. The one-country share also uses the null, and its observed values match `national_share.csv`.

Fixes, most important first:

1. **English counts as home for most acts, and unevenly.** `home_editions` adds languages with population over 50%, and babel counts second-language speakers. English becomes home for 29 countries, including DE, NL, BE, SE, DK, AT, CH, FI and GR, which covers 3,815 of 4,311 acts with a known country. A Dutch act's English article is free, a French act's counts as foreign. Use official, de facto and regional status only, or say plainly what the tiers mean.
2. **The 0 foreign tier is partly mislabelled.** The miss audit found an article for 7 of 20 no-article acts (35%, Wilson about 18% to 57%). They are name and clashfinder-id matches with articles in de, sv and en that MusicBrainz does not link. So roughly a third of the 0 foreign tier would sit in 1 or more foreign. This pulls the 0 versus 10 or more contrast toward zero. The tier ordering is probably unchanged, but the 0 foreign figure (r +0.203, share 83%) is a floor on the contrast, not a clean one. Say that in the text, and add one line on the search procedure used.
3. **The one-country share null has no festival memory.** 40% of acts repeat the same festival in several years. Counting distinct festivals instead of editions lowers the observed share from 0.773 to 0.752, a drop of 0.021. The excess over the null is 0.028 in the 10 or more tier, so it can be explained by recurrence alone. Give an observed share over distinct festivals beside the edition-based one, and say the null cannot tell a national circuit from loyal return bookings.
4. **Unknown country rule is asymmetric.** An act with a known but unmapped country (for example XE) and no article lands in 0 foreign, while the same act with an article lands in Unknown artist country. Put both in the unknown row or count the acts affected.
5. **Minor.**
   - Every draw branches from one post-burn-in state, so the null SD is slightly understated. This is inherited from `watts/run.py`.
   - Move the gap per pair column to a CSV.
   - Add a caption line that the null r is below zero by construction.
   - The deletion range for r uses the shuffled projections with the festival's edges removed, so name it "fixed draws" next to the OLS gap range, which uses fixed baselines.

## Part B: analysis/newman/wikitext

Verified:
- **TF-IDF.** The definition matches week 6, part 1: tf is count over intro length, idf is the natural log of N over df, and the stopword zeroing is an extra, documented step.
- **Shared-act leave-out.** The cosine uses summed vectors with shared acts removed from both lineups, and the code asserts shared counts equal `watts/pairs.csv`.
- **Kappa.** It reproduces: 1,988 of 2,088 paired codes agree (95.2%, kappa 0.939), against the 2,106 predicted codes. The hand check gives 29 of 30. The one miss, Monarchy, is a base-versus-origin error, which the text names.
- **Regression.** The estimate is +1.28 acts per 0.10 cosine, against +1.36 for tags on the same pairs.

Fixes, most important first:

1. **Origin extraction does not fill the unknown-country gap.** Only 28 of the 504 acts without a MusicBrainz country have an English intro, and 18 were filled (3.6%). Say so, and do not present it as the fix for that tier.
2. **The hand check samples the wrong cases.** 29 of 30 is 96.7%, Wilson about 83% to 99%. The draw comes from all predictions, and only one of the 30 disagrees with MusicBrainz. Check all 18 fills and the roughly 100 disagreements, since those are what change results. Acceptance is lenient: a prediction passes if the intro supports it as origin or nationality, and two labels list two countries ("TR|IT", "FR|CM").
3. **The term comparison is still mostly country.** The leading words are British, London, England and American. The GB-only sentence shows the American gap falls from 31.2 to 4.8, so the table should be rebuilt from GB acts only. Replace "same direction in two half samples" (63% of all terms agree by sign) with a permutation of tier labels. Say that only 256 of 1,884 low-tier acts have English text.
4. **Demonym list has no entry for several MusicBrainz countries.** CD, CI, ML, EC, MD, MN and NE are missing, so origin fills for African acts are missed systematically.
5. **Examples are the first three alphabetic hits.** The text says so, but pick them by rate and say how.
6. **Tag agreement null.** The centred-rank version (0.63 to 0.79) is a partial answer. A shuffle of acts within edition-size class would be a real null.

## Text against the course pages and GVMH

- **Pass:** capture and miss sentences are present for every item in both findings. The voice is participant style, with no dashes and no grading talk.
- **Fix:** name the null once in a caption, and avoid long headers.
- **Check later:** the figure and final report refresh after the rerun. Recheck `findings_reach.md` and the PNG then.
