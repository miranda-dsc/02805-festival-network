Review of Watts's figures: `analysis/figures/make_figures.py`, `fig1` to `fig3` (png and pdf, saved 11:11), `analysis/review/gaps/watts.md` (revised 11:48; the revision adds the same-brand and "two or more festivals" clauses to the Fig. 1 caption and the tag-agreement sentence in the text above the captions). Reviewed 2026-11-25. No files of theirs were edited. GVMH checker passes on the script and on `watts.md`.

## Plotted numbers against the source csvs

| Figure | Source and columns | Result |
| --- | --- | --- |
| Fig. 1 | `watts/reach/country_gap.csv`: `r`, `r_null_low`, `r_null_high` | Dots 0.194, 0.137, 0.081, 0.057, -0.029. Bands -0.049 to -0.013, -0.063 to +0.011, -0.058 to -0.013, -0.052 to -0.007, -0.052 to -0.024. All match the plotted marks. |
| Fig. 2 | `watts/reach/national_share.csv`, rows with `control` "2 or more festivals": `one_country_distinct`, null low and high | Dots 81.4, 74.0, 70.5, 65.2 and 59.8 percent. Bands 75.1 to 76.2, 67.4 to 70.5, 63.8 to 66.0, 61.4 to 63.8, 57.9 to 59.5. Match. |
| Fig. 3 | `newman/wikitext/sound_effect.csv`, rows with `year` "all": `acts_per_0_10`, `deletion_min`, `deletion_max` | Wikipedia 1.28 (0.96 to 1.82); strict tags 1.36 (1.24 to 1.42). Match. |

Caption numbers: Fig. 1 0.226 and 0.009 (0.2256, 0.0090), 4,310 acts, 1,402 unknown (505 + 897): correct. Fig. 2 5.7 and 1.2 points (81.36 minus 75.63, 59.84 minus 58.65): correct. Fig. 3 2,610 pairs, +1.28, +1.36, nine positive yearly point estimates (minimum 0.63): correct.

## Readability at 8.7 cm (I viewed the three PNGs)

- The PDFs are 246.6 pt wide (8.7 cm) with real 9 pt ticks, 8 pt legend, 11 pt titles; the PNGs are 600 dpi. At that size all tick labels, tier labels and legend entries are legible, and nothing overlaps.
- Fig. 1: the 10+ dot sits on top of its band and hides most of its upper end. Give the markers a white edge, or draw the band wider than the dot, so the reader can see the dot is inside the band.
- Fig. 3: the left spine at -0.05 and the zero line at 0 draw two vertical lines next to each other. Widen the lower x limit (for example -0.2) or hide the spine.
- Fig. 3 height is 4.3 cm, Figs. 1 and 2 are 6.2 cm each: 16.7 cm in total, about two-thirds of a PNAS column. Figs. 1 and 2 share an x axis and could be one two-panel figure; optional.
- Single hue, strong lightness contrast between dots and bars: fine in grayscale.

## GVMH

- No em or en dashes in the script, the PDFs' text layer (`pdftotext`) or `watts.md`. `axes.unicode_minus` is off, so negative ticks are plain hyphens, which is correct.
- Titles are short ("Country assortativity", "National booking concentration", "Lineup similarity and overlap"). Tier labels use "2 to 4", "5 to 9", "10+".
- Fig. 1 caption says "10-or-more tier"; the rest of the text says "10 or more". Make it consistent.

## Course page (live week 8 and checklist) against the captions

The page asks for two or three figures; captions that say what is plotted, what the comparison is and what the reader should see; the check shown next to the claim; labelled axes. Three figures meets the count; all axes are labelled.

## Actionable, ranked

1. **Fig. 1 caption omits the leakage check.** The figure invites reading the 0 to 1 drop as a trend, and `country_gap_leakage.csv` shows the zero-minus-one contrast can shrink from 0.062 to 0.008 or 0.017 under random reassignment of the no-article acts. Put one sentence in the caption (the check next to the claim), not only in Results. Define "r" in the caption (the y label uses it) and give the draws (2,000 per year and tier).
2. **Fig. 1 and Fig. 2 disagree at the 10+ tier and the captions do not say so.** In Fig. 1 the 10+ dot is inside its null band. In Fig. 2 it is just above its band (0.598 against an upper edge of 0.5945). A reader will compare the two panels; add a clause to the Fig. 2 caption that the highest tier is slightly above its band even with each festival counted once.
3. **Fig. 3 caption: "positive in all nine years" needs its limit.** It holds for the point estimates only; the Wikipedia 2024 festival-deletion range runs from -0.08 to 1.51, and 2017 and 2025 start at 0.40 and 0.45. Either say so or plot the yearly estimates (they are in the csv), which also gives the reader the consistency check.
4. **Fig. 3 has no "what to see" sentence.** The caption lists what is plotted and the controls but not the reading (both measures give an excess of about 1.3 shared acts per 0.10 cosine, the tag range is narrower). Add it, and the misses clause that the intros can pick up geography and career language (it is in the text above the captions, not in the caption).
5. **Fig. 2 caption: the repeat-booking caveat should be a measured limit.** "The shuffle has no festival memory, so repeat booking can contribute to the excess" is right, and the distinct-festival counting already removes part of it. The exactly-k check (`review_granovetter_circuits.md`) shows a matched null is not yet available; keep the sentence as is and do not add a stronger claim.
6. **Drop or keep the in-figure titles on purpose.** Each repeats the y label and the bold caption title and uses about 0.5 cm of the 6.2 cm figure height; with six pages in all, remove them if space is short.
7. **The script needs Georgia installed** (`findfont` with `fallback_to_default=False`), so a group member without it cannot rerun it; say so in a comment-free README line or relax the check. The PDFs are already committed and embed the font.
8. **PNAS placement is still open**, as `watts.md` states: check the final captions and page count in Overleaf; I did not compile the template.

## Round 2 (checked 2026-11-25 after the 12:08 figures and the revised `watts.md`)

Checker passes on `make_figures.py` and `watts.md`; the PDFs contain no dashes. `fig1` is now a three-panel figure (A Wikipedia reach and B festival count, both from `erdos/reconcile/comparison.csv`; C national booking concentration), 8.7 by 10.0 cm. `fig3` is the sound figure with pooled and yearly estimates, 8.7 by 7.7 cm. `fig2` is still exported as a standalone copy of panel C.

Plotted numbers against the csvs (all match):
- Panel A reads `r_excess`, `r_deletion_min` and `r_deletion_max` for the five foreign tiers: 0.231, 0.176, 0.116, 0.091, 0.007; the 10+ range is -0.008 to +0.029.
- Panel B reads the same columns for the festival-count classes: 0.315, 0.218, 0.066, with ranges 0.278 to 0.354, 0.191 to 0.236, 0.056 to 0.076.
- Panel C is unchanged and matches `national_share.csv` (81.4 to 59.8 percent, bands as before).
- `fig3` pooled and yearly points and ranges match `sound_effect.csv` (2015 Wikipedia 2.07, 2024 Wikipedia 0.63 with a range from -0.08, strict tags 0.91 for 2024). The zero line is a single line now and the double axis is gone.

Your three points:
1. **Same grey for two different things: confirmed.** In A and B the bars (width 2) are festival-deletion ranges; in C the bars (width 8) are the central 95% of the null. Both use the `NULL` colour and the only legend, in C, says "Central 95% of null", so a reader applies it to A and B. Draw deletion ranges in a different style (thin dark whiskers with caps, as in `fig3`) and give A or B its own legend entry, "Range after dropping one festival".
2. **Panel B title: not clipped, but flush with the edge.** The last dark pixel of the title is 19 px (0.8 mm at 600 dpi) from the image edge, and the final letter is complete. The title is left-aligned to the axes and runs about 30 px past the axes' right end. Shorten it ("By festival count") or give the figure a little right padding, since LaTeX or a journal crop can remove that margin.
3. **Panel A is on the shared shuffle, consistent with B: confirmed** (0.231 from `comparison.csv`; Watts's own null gives 0.226). The caption says "common within-year curveball null" and "shuffle full lineups" for A and B, and describes the tier-specific null for C. It does not give the draw count for A and B (200), and it does not say that C and the leakage sentence use a different null (2,000 draws, tier-specific margins). The leakage numbers (0.062 falling to 0.008 or 0.017) are Watts-null values placed in the same paragraph as the shared-null excesses (0.231 and 0.176 give a gap of 0.055, not 0.062). Say so in the caption.

Items from round 1:
- Point 1 (leakage in the caption, r defined): closed in content; see the null-mixing point above and add the 200 draws.
- Point 2 (10+ above its band in C): closed; the caption now says so.
- Point 3 and 4 (Fig. 3 yearly limit, what to see, misses clause): closed; yearly estimates are plotted and the caption states the 2024 range.
- Point 5 (repeat-booking caveat): closed.
- Point 6 (titles): still present, as panel and figure titles; optional.
- Point 7 (Georgia): open, unchanged.
- Point 8 (Overleaf proof): open.
- Markers and double axis (readability notes): closed.

New or still open:
1. **No null spread in A and B.** Points are observed r minus the mean null r, with deletion ranges only. The reader cannot see whether 0.066 (5 or more festivals) or 0.007 (10 or more) is beyond or within draw-to-draw variation; the earlier figure showed that. Add the central 95% of the null excess to `comparison.csv` (it has the draws) and plot it, or state the null SD (about 0.01 in Watts's runs) in the caption. The course page wants the check next to the claim.
2. **Panel B uses all 5,712 acts; panel A uses 4,310.** The caption says the Wikipedia comparison has 4,310 acts and that 1,402 are unknown, but not that B includes them. Say it, or the two panels look like the same cohort.
3. **Tick labels in A wrap across lines** ("2 to / 4", "5 to / 9", "10 or / more"). Legible at 8.7 cm but a range split over two lines reads badly; widen A (the `width_ratios` are 1.35 and 1) or reduce the tick size to 8 pt.
4. **The script hard-codes "3-4 festivals" and "5+ festivals"** from `comparison.csv`. It will break when Erdos reruns after Nandini's relabel. Take the class names from the csv order.
5. **Remove or flag the standalone `fig2`**, a duplicate of panel C, so nobody places both.
6. **Size.** `fig1` plus `fig3` are 17.7 cm tall, about 70 percent of one PNAS column; check the six-page budget in Overleaf with the captions, which are long (the Fig. 1 caption is about 330 words).

Verdict: open items (the three points you raised, plus items 1 to 6).
