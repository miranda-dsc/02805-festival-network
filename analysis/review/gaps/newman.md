| Item | Status | Effort |
| --- | --- | --- |
| A2. Reach sensitivity | landed | done |
| B1. Term tests | landed | done |
| B2. Tag agreement | landed | done |
| B3. Wilson intervals and blind reader | open | about 30 min |
| B4. Demonym audit | landed | done |
| B5. Disagreement reading | landed | done |
| B6. Term figure | landed | done |
| Follow-up 2. Term interpretation | fixed now | done |
| Follow-up 3. English coverage | fixed now | done |
| Follow-up 4. Yearly sound estimates | fixed now | done |
| Follow-up 5. Tag agreement interpretation | fixed now | done |
| Follow-up 6. Reach interpretation | fixed now | done |

B3 is the only open Newman item. The Wilson intervals are in `wikitext/findings.md` item 3, and I recalculated all three from the counts in `origin_wilson.csv`. The 20 intros in `wikitext/second_reader.csv` still have blank labels and notes. A group member needs to read them blind so we can report agreement between readers in the paper.

For A2, I subtracted the null mean from observed r in each of the three reach CSVs and matched the five values per rule to `findings_reach.md` lines 118 to 126. The highest tier is inside the central 95% null band for each rule.

For B1, I recalculated BH q from the stored raw p values. Of 649 terms, 96 had raw p below 0.05 and 21 had q below 0.05, including British, England and London at higher rates in the GB zero-foreign tier. The findings table gives raw p, BH q and max-gap p. For B2, I checked the nine yearly rows and 1,800 stored draws. The reported excess is 0.18 to 0.40, the null means span 0.32 to 0.60, and the minimum attainable p is 1/201, rounded to 0.005.

For B4, I checked the ten demonym audit rows. Seven were supported, and the export summary reports 1,993 agreements out of 2,095 paired countries. For B5, the findings give the 28 of 50 cases favoring Wikipedia and 4 of 50 favoring MusicBrainz, with the origin results split across paragraphs. For B6, I inspected the PNG and caption. Both axes use plain rate ticks at 0, 1, 10 and 100. The caption identifies the four labels on each side and reports their max-gap result.

I checked stored analysis outputs and the rendered figure against the live course guidance on measurement checks and figure captions. [Week 8](https://sunelehmann.com/socialgraphs2026-web/weeks/week8.html#spine) [Project checklist](https://sunelehmann.com/socialgraphs2026-web/index.html#checklist)

For follow-ups 2 and 3, `wikitext/findings.md` gives the exploratory BH result and the family-wise max-gap result, and explains the 12% versus 100% English-intro selection. I checked these against `tier_terms.csv` and `tier_coverage.csv`. For follow-ups 4 and 5, I checked `sound_effect.csv` for the yearly range and the negative 2024 deletion estimate. The text now gives those values and describes agreement above all 200 draws with tag similarities held fixed.

For follow-up 6, I checked the leakage results, the highest tier's yearly count and the Q-id audit sample against the stored CSVs. `findings_reach.md` describes the similar excess of the two low tiers under leakage, the pooled null band and 5 of 9 year count, and the limits of the audit by match method. The 2,194-act edition is with Granovetter.
