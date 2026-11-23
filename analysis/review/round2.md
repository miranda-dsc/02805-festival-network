# Review round 2

Checked by running code on the saved CSVs and processed data, reading the scripts and a 20-act cache snapshot. I did not run `src/03_musicbrainz.py`.

## common.py

- Rules match CLAUDE.md: rebroadcast rows, 2020 and 2021, Leeds dropped, one row per edition and act; same-brand is a helper, not a drop. Result: 214 editions, 44 festivals, 53,925 bookings, 32,293 acts, all act keys strings.
- `fix_key` changes only the `&amp;` keys: 63 keys changed, 0 of them without `&amp;`. It does not fix the other entities. 15 acts still have broken keys: `&gt;` ("T&gt;i" becomes "t and gt i", 19 act strings), `&#233;`, `&#231;`, `&#232;`, `&#322;`, `&#324;`, `&#248;`, `&bdquo;`, `&rsquo;` ("El Gadz&#233;" becomes "el gadz and 233"). Fix it at the source in `02` (unescape, then build the key) or generalise `fix_key` by unescaping and rebuilding the key the way `02` does.

## src/03_musicbrainz.py

Round 1 points, now: scope uses `common.load`, so 5,712 eligible acts (was 6,435); ambiguous (more than one score-100 hit) and conflicting-id acts are kept apart from matches; "live" and "dj set" suffixes are stripped before search ("2Fox (DJ set)" matched); 117 lines against 259. Cache is written every 50 acts and old-format entries are discarded, which is correct.

Still open:
- Name test is exact casefold, so "2manyDj's" is unmatched while "2manydjs" matched: the same act under two keys, and "The 45's" fails despite one perfect hit. Compare with the `act_key` normalisation instead.
- A timeout, connection error or 500 stops the job (the `finally` saves, rerun resumes). Fine for a restart, but it is a long run; 503 and 429 retry with a 300 s cap and the log shows repeated 503s.
- No precision check exists yet. Hand-label about 50 search matches (and the ambiguous ones) after the run and report precision. In the snapshot, 12 Stone Toddler and 47Soul match with zero tags, so report tag coverage as well.
- `act_tags.csv` still has no rows for acts without tags.
- Eligibility counts Tomorrowland weekend 1 and winter as two festivals.

## Watts

Uses `common.load`; no z or SD in the text; uncertainty is deletion ranges, per-year counts and tail hits. 9,999 draws, tested exchangeable in round 1.

Recomputed: the date-adjusted country gap is +2.435 from `pairs.csv` (year and day-bin strata, no Tomorrowland), +2.524 on site countries, and positive in all nine years: 3.06, 5.26, 3.91, 0.82, 2.17, 2.43, 3.01, 2.39, 2.63. The 8 to 14 day excess is positive in 7 of 9 years, with 2015 (-3.81) and 2024 (-0.12) the exceptions; 0 to 7 days is positive in only 4 of 9.

Finding 2 (+2.43): put it in the paper, with changes.
- It holds up: festival deletions +1.94 (without Reading) to +2.76, pair deletions at most 0.05, +2.57 after controlling for distance.
- It is mostly a UK result: 32% of pairs are GB with GB. For pairs with no GB edition the gap is +1.34 on 474 pairs (finding 3 reports this). State that, and say a UK market or promoter effect is not separated from "country". 2018 (0.82) with the most pairs is the weak year.
- Use site country as the primary basis: 13 retained editions have wrong metadata (Nos Alive, Graspop, Rebellion labelled DK, Sziget AT and others), and the gap barely moves.

Finding 1: report the same-week effect as gone (+0.18, deletion range -0.14 to +0.48), not as sensitive. The 8 to 14 day bin is one of five bins with no mechanism, so keep it out of the headline. Finding 4: distance per doubling is a null (-0.04, p 0.32); say so. The under-100 km bin (+2.11) rests on 169 pairs. Slam Dunk's single site makes its distances unreliable.

## Newman

Does not use `common.load`; it has its own loader, drops Leeds and rebroadcast rows, and does not fix `&amp;` keys. Recomputed with `common.load`: 2019 has 5,679 acts, 30 editions, 6,930 bookings; 36.66% of lineup is booked elsewhere; 280 edition links. All match the findings, so the keys only change other years or not at all. Switch to `common.load` and rerun anyway.

Still reports z for single numbers (items 3, 5, 6, 7) with only 200 draws (p floor 0.005). Items 4 to 6 give counts of years (9 of 9, 9 of 9, 8 of 9), which are the right form.

Paper-ready: items 2 and 4 (links below null in 9 of 9 years, a strong and unremarkable result) and item 5 modularity above null in 9 of 9 years. Not yet: item 5 seed agreement (z 1.57), item 6 country NMI (2019 z 1.78, two SD in 5 of 9 years, built on the wrong country metadata) and item 7 (z 2.10 over 36 year pairs that share festivals).

## Granovetter

Uses `common.load`. Recomputed: annual excess positive in 9 of 9 panel years and 8 of 9 full years (2015 is the exception). Pair fixed-effect slope in the full set -0.033 pp per year observed, -0.046 null, excess +0.013; panel leave-one-festival-out +0.008 to +0.043.

- Not paper-ready as a trend claim. The panel is 6 festivals and 15 pairs, and after matching edition counts the range is -0.044 to +0.109 and -0.056 to +0.068, which straddles zero. 250 draws only.
- Usable as stated: overlap did not rise (no homogenisation) and the excess did not grow beyond what the null predicts. Edition counts per year run from 11 to 35, so item 3 (three-plus share, Gini) is descriptive only.
- Item 4 (returns 7.3% against 1.2%) is trivial because the null removes festival identity. Replace it with a placebo, the overlap of a lineup with other festivals' earlier editions, or drop it.
- The closing sentence is fixed text in the template; generate it from the numbers.
