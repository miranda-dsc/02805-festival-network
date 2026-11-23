# GVMH sweep

The checker passes on every file we wrote (25 files, 9 figures). It flags only Miranda's src/00 to 02, listed at the end. The points below are what the checker cannot see. I read every .py and .md and looked at all nine PNGs. Nothing was edited. granovetter/launch exists but is empty, newman/text and kleinberg/nested do not exist yet, and analysis/watts is still changing, so rerun the checker on those once the agents finish.

## analysis/watts

1. `findings.md` is out of date against the work since. "Open problems" still says to audit the ambiguous matches (round 3 did that: 52.5%). Item 2 says the sound "underrepresents acts booked at only one festival"; those acts have no weight at all. The text also never says that country proxy tags such as british and uk sit in the sound.
2. `findings_v1tags.md` is a comparative leftover named after an old version, and it differs from `findings.md`. Delete it or move it out of the folder before the group reads the folder. The same holds for `act_matches_v1.csv` and `act_tags_v1.csv` in data/processed.
3. The heading is "### Open problems" in the generated file, while granovetter, newman and euler use a plain "Open problems" line. Pick one.
4. `distance.png`: the title "Distance between sites" repeats the x label. Drop the title or make it say what is plotted.
5. `days.png`, right panel: nine coloured lines with a small legend and one wild year (2015). Hard to read at paper width. Show median and range across years, or small multiples.
6. `country.png`: the left panel title "Same country" repeats the tick labels. The legend sits over the first panel's data corner. Fine otherwise.
7. `genre.png` is readable. The legend title "Bin means (10+ pairs)" is fine.
8. Code and docstrings are clean: no comments, short lowercase docstrings. Lines in `tagged.py` run past 100 characters in three places (`national_share`, `main`); match run.py.

## analysis/euler

1. `README.md` has no full stops at the end of most sentences and mixes lowercase and sentence-case starts. Sentences run long (the projection and change-null paragraphs). It also says "the input hashes are checked again after the run" with no stop. Make it consistent and cut it by a third.
2. `findings.md` is dense: long sentences stacked with clauses ("checked against the saved pair differences"). Items 1 to 5 each hold three or more numbers. Plain short sentences would help the group explain each figure. Item 5 reports that a file is missing; it is a note, not a finding.
3. `projection_check.png`: the observed value is a green vertical line with no legend entry, and its colour matches "Proposed fix". Label it "Observed".
4. `identity_changes.png` is clear. The "+0" label for a zero bar is fine.

## analysis/granovetter

1. `findings.md` capitalises "Curveball" in running text; euler and newman write it lowercase. Item 3 packs two endpoint sets and three measures into one item.
2. `overlap.png` reads well. Panel titles are short. The y label has a unit. Nothing to fix.
3. `run.py` has no comments and no module docstring.

## analysis/newman

1. `findings.md` items 1 and 2 are not findings: scale counts, and a null that matches exactly by construction. Say so in one sentence, or move them into the intro. Item 5 starts "They measure" for a single measurement; use "It measures".
2. Item 7 is one 60-word sentence. Split it.
3. Figures are clear. The left plot of `act_degrees_and_lineups.png` has a log axis that is labelled. The right plot has 45 dots per year in one column and could use jitter or a box, but it reads.

## analysis/kleinberg

1. `references.md`: "We cite this for" opens every entry; vary or drop it. The line "Five priority references are marked" is a note to the group that belongs outside the list. The bold "Priority" tag on each marked entry is the heaviest formatting in the repo; use a plain "Priority" in a heading or sort them first.

## analysis/common.py, src/03_musicbrainz.py, src/03b_musicbrainz_dump.py

1. Clean. Comments are lowercase and keyword style. `03b_musicbrainz_dump.py` has an inline comment on `MIN_VOTES` that explains why, which is fine.
2. `common.py` comment "act_key was built before html unescaping" is a fact the code does not show, so it stays.

## analysis/review

1. My own round files use headings and tables and run 618 to 1,047 words. They are for the group lead, not the paper, so I left them. If they go to the group, round 1 and 2 are over the page limits in the briefs by a few lines.

## Miranda's src/00 to 02 (do not edit)

1. 21 comments start with an uppercase letter (00_download 2, 00a 3, 01 5, 02 11 per the checker). The style rule is lowercase keyword comments.
2. Most comments narrate the next line ("Remove non-music stages", "Keep the earliest show", "Turn the lists into tables and save them", "One row per act per edition"). They could go.
3. Prints like "Rule 1: removed ..." are good and match the count style in CLAUDE.md. Keep.
4. `02_clean_lineups.py` country comes from the timezone; 13 editions are wrong (already in CLAUDE.md). This is a data issue, not a style one.
