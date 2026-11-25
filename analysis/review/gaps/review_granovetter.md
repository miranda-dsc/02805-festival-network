Review of granovetter's gap report (`analysis/review/gaps/granovetter.md`, report only). Reviewed 2026-11-25. GVMH checker passes ("gvmh ok"). No files edited.

## Spot checks that hold

- Scope, from `common.load()`: 214 editions, 44 festivals, 53,925 bookings, 32,293 act keys, 5,712 keys at two or more festivals. Edition counts per year 11, 20, 26, 35, 30, 22, 23, 24, 23. With `pandemic=True`: 239 editions, 44 festivals, 33,321 keys, 6,035 repeat keys. All match.
- 3,144 + 1,681 + 887 = 5,712 (circuits reach classes), and 26,581 single-festival keys is 82.3%. Matches my rerun of circuits.
- MusicBrainz audit counts from `analysis/review/match_labels.csv`: name 39 correct and 1 unsure of 40, alias 19 of 20 (1 wrong), ambiguous 21 of 40 (17 wrong, 2 unsure). Matches the report.
- HTML-entity keys: I find 32 loaded bookings and 21 distinct keys by a loose pattern; the report says 20 keys and 30 bookings. The extra is one false positive ("neil cowie twists the 80 s and 90 s", where "80 s" is not an entity), so the report's count is right and the 15 in `CLAUDE.md:148` is out of date.
- Wikitext tier counts, the 2,613 same-year pair count, 2,610 after the same-brand exclusion: match.
- Methods facts that check against code: curveball draws (9,999 in `analysis/watts/run.py:17`, 2,000 in `analysis/watts/tagged.py:12`, reach imports it, circuits 200, kleinberg 400 and 200 deletion draws in `analysis/kleinberg/nested/run.py:11-12`), `tomorrowland weekend 2` in the exclusion list (`src/00a_find_festivals.py:24`), the `Sunday (1994)` exception (`src/02_clean_lineups.py:80`), MBID-first ordering before the one-row-per-act collapse (line 90), MIN_YEARS 4 and MIN_ACTS 30 (`00a`).

## Actionable, ranked

1. **Fix the circuits counts that the Methods paragraph will cite.** The report's Methods text says "Circuits uses 200 per year" and "Circuits also keeps the pair null fixed" and points at `circuits/findings.md:1` and `:10`. Both are right today, but the circuits review (`review_circuits.md`) asks for changes to that file (class labels "3 to 4", dropping the 1-festival class, an exactly-two-edition restriction in the national share). Re-check these two sentences once Nandini's rerun lands; do not freeze the Methods text before then.

2. **Several citations point at the wrong line.**
   - `analysis/watts/reach/reach_null.py:15` is cited for the 2,000 draws; line 15 is inside `draw_statistics`, and the draw count lives in `analysis/watts/tagged.py:12` (imported at `reach_null.py:10`). Cite `tagged.py:12`.
   - "See `src/02_clean_lineups.py:42`" for the act identity points at the docstring of `act_key`, which is fine, but the rules (brackets, trailing live or dj set, leading the, ampersand) are in the lines after it; cite the range.
   - The `common.py` line references (`:13`, `:31`, `:39`, `:51`) are fine as of now; they move with any edit to `common.py`, so give function names (`load`, `fix_key`, `same_brand`).
   Line numbers in a paper are not needed anyway; function names survive an edit.

3. **The report is a facts dump and is not yet Methods text.** The Methods bullets run to one long sentence chain each (the MusicBrainz and Wikidata bullets are about 200 words). For the paper, someone has to cut each to the three to five facts a reader needs, and the six-page limit leaves roughly half a page for Methods. State which facts go in the paper and which go in a supplement or README; otherwise it will be pasted whole.

4. **Report the open items as open.** The table marks "HTML entities in act keys" as Open, correctly, but the proposed fix (decode before deriving the key in `02`) needs Miranda's `lineups_raw.csv`, which is not local, and changes act identity for about 20 keys that sit in 30 bookings out of 53,925. That is 0.06% of bookings, so a rerun of every identity-dependent join is hard to justify at this stage. Recommend to the group: do not fix, instead report the count in Methods as a known limitation (as the report already says to) and note the effect is under 0.1% of bookings. This also settles the CLAUDE.md "15" line, which should now read 20 keys.

5. **Euler's scope is a documented difference, not a defect, but the paper must not mix them.** The report reproduces euler's 32,487 keys by retaining Leeds and turning off `fix_key`. The identity audit is the only place that scope appears; make sure no figure or sentence in the paper combines the 32,487 and 32,293 counts. Add the number to whoever drafts the paper's data paragraph.

6. **Smaller points.**
   - "The 248 selected Clashfinder IDs cover 45 festivals before exclusions ... 214 editions" is right, but 248 - 9 Leeds - 25 pandemic = 214 only if no edition was also dropped for another reason; state that identity once in a line (it holds: 248 - 34 = 214).
   - The MusicBrainz precision sentence mixes four rates (name, alias, ambiguous before and after the filter) with their Wilson intervals; the three-vote filter figure (17/22, 77%) is not recomputable from `match_labels.csv` alone, so name the file or script that produces it.
   - The report relies on the "live checklist" and week 8 page, which I did not re-fetch; the local `course-site` copy may lag. Someone should read the live page once before the paper is frozen.
