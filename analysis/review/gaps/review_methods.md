Review of granovetter's Methods draft (`analysis/review/gaps/methods_draft.md`) against the code, the data and the live course page. Reviewed 2026-11-25. No files of theirs were edited. GVMH checker passes. The draft is about 865 words including the number-sources list.

## Checked and fine

- Counts match `common.load()`: 214 editions, 44 festivals, 53,925 bookings, 32,293 act keys, 5,712 repeat-festival acts.
- Selection rules (2015 to 2025, at least 30 acts, at least four qualifying years, largest schedule per festival-year, earliest show for date), the Leeds, rebroadcast and 2020 to 2021 exclusions, and the same-brand pair exclusion match `src/00a_find_festivals.py`, `src/02_clean_lineups.py` and `common.py`.
- HTML entity count: 20 keys across 30 bookings. My loose search gave 21 keys and 32 bookings, with one false positive, so this is right and `CLAUDE.md` ("15") is out of date.
- MusicBrainz match order and the three-vote rule match `src/03b_musicbrainz_dump.py` as described in the earlier granovetter report. Precision 39/40, 19/20, 17/22 matches `round3.md`. Dump date 21 November 2026 matches the live listing. Median strict coverage 35% matches `tag_coverage.csv` (35.25%).
- Reach: tiers, bins and Babel rules match `findings_reach.md`. The Q-id audit (29/30) and the missed-article audit (7/20) match their csvs.
- Null: 2,000 draws from a shared post-burn-in state, 9,999 for the full-lineup expectations, 200 for the tag agreement in lineup-size thirds, all match the code. The deletion description matches.
- Strict-match assortativity 0.239 and -0.002 match `country_gap_strict.csv` (0.2098 + 0.0293, -0.0391 + 0.0368). The 22% and 45% leakage claim matches `country_gap_leakage.csv`.
- The text pipeline reads as `run.py` does: English introductions with spaCy's blank tokenizer, alphabetic lowercased tokens, a stop-word list defined (I did not trace where the stop-word weights are zeroed).

## Course page (live site, weeks/week8.html and the checklist)

Methods must give "enough that a reader could redo it: the data (what, from where, collected when, how many), every preprocessing choice that could change a number, each measurement and what it measures, each validation and its result." The draft covers what, where from and how many, most preprocessing, and the validations. It does not cover "collected when" or what each measurement captures. The paper also has six pages in all, so Methods is about three-quarters of a page.

## Actionable, ranked

1. **"Collected when" is missing.** The draft gives no collection dates for Clashfinder. `euler_refs.md` found no run records. State the dates from the file timestamps in `data/raw/clashfinder/` if they exist; otherwise say "downloaded in November 2026" only if that is true. Say that the downloader pauses two seconds per request (the site's robots file declares 10), per `review_euler_refs.md`.

2. **The Methods paragraph for Fig. 2 and the same-country measures is absent.** Fig. 2 is the national share (each festival once per act, share in the most-played country, averaged over acts of the same tier, against the same curveball null). The draft describes only assortativity and the cosine regression. Add one sentence for the share, and one for the pair-level same-country excess that the circuits and Watts results use, if either is cited.

3. **The main reach analysis includes ambiguous matches, and the draft does not say.** The Wikipedia reach paragraph joins "MusicBrainz artist IDs" without saying that 662 of the matched acts come from accepted ambiguous matches (precision 17/22 after the vote rule), with strict matching as a sensitivity. The tag section says strict profiles use ID, name and alias only, so a reader will assume reach does too. State which matches feed reach and where the strict version appears (the 0.239 and -0.002).

4. **No sentence on what each measurement captures and misses.** The course page asks for it per analysis; the draft has one fragment ("Reach measured linked Wikipedia coverage and depended on editing and match coverage"; "Intro similarity also captured geography and careers"). Add one captures sentence and one misses sentence for assortativity, national share and cosine similarity, or put them in Results next to each figure; do not leave them out of both.

5. **The Checks paragraph mixes validations and results with sample sizes but gives no intervals.** The draft reports 39 of 40, 19 of 20, 17 of 22, 29 of 30, 7 of 20. The Wilson intervals are in the repo (`origin_wilson.csv`, `findings_reach.md`); the MusicBrainz and Wikidata ones are in the earlier granovetter report. Add the intervals for the two that carry the paper (ambiguous 17/22 and the Wikidata 29/30). Also say the hand checks were by one reader unless the second-reader sheet is filled.

6. **Wording that overstates.** "Randomly moving 22% or 45% ... narrowed the difference between these two lower tiers" should say it narrowed the zero-minus-one contrast from 0.062 to 0.008 or 0.017 (the numbers are in `findings_reach.md`). "Reach measured linked Wikipedia coverage" is the honest claim; keep it and do not call the tiers "popularity" elsewhere. The "Median edition coverage" appears twice with different values (35% for tags, 28% for Wikipedia intros), which is correct but confusing without a label.

7. **"Number sources" is not paper material.** It cites internal paths and review files (`analysis/review/gaps/granovetter.md`) as sources. Keep it for the group, but the paper's Methods needs the facts, not the paths; and a paper reader cannot open a review file. Cite scripts by name only.

8. **The licence link points at a different festival's page** (`clashfinder.com/s/download2k26/`; the earlier report used `nos19`). Pick one page that states CC BY-NC 3.0 and open it once; I did not fetch either.

9. **Length.** At about 865 words (about 750 without the sources list) the draft would fill most of a PNAS page at two columns; with Abstract, Significance, Introduction, Results, Discussion, three figures and the references in six pages, plan for Methods to be about half a page. Cut the number-sources list, merge "Act identity" into "Data", and move the hand-check numbers into Results next to the figures they support.
