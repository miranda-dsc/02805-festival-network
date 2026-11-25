| Item | Status | Effort |
| --- | --- | --- |
| Fig. 1 reach contrast and missing articles | Draft checked, qualify result in Results | 15 min |
| Fig. 3 sound claim and reach | Draft checked, scope wording | 15 min |
| PNAS placement | Standalone proofs checked, paper proof open | 20 min |
| PNG inventory and reach comparison | Complete | Done |

Keep the Fig. 1 claim at the endpoints. Under the common comparison null, excess assortativity is +0.231 at zero foreign editions and +0.007 at 10 or more. It falls from +0.315 to +0.066 across the festival-count tiers. In the separate leakage check, randomly moving 22% or 45% of zero-foreign acts without linked articles into the one-foreign tier shrinks the zero-to-one gap from 0.062 to 0.008 or 0.017. The highest tier stays fixed in this check. Use “zero linked foreign editions” in Results. [Reach sensitivity](../../watts/reach/findings_reach.md#L75)

Keep the sound claim at the pair level. The sound analysis uses 2,610 comparable edition pairs and has no slope by reach tier. It supports an association between text similarity and excess overlap across those pairs. Intro and strict tag cosines agree above the shuffled baseline in all nine years. The intro profiles can also pick up geography and career language. [Sound estimates](../../newman/wikitext/sound_effect.csv) · [Text checks](../../newman/wikitext/findings.md#L3)

Place the two paper figures at column width and check the final page count and captions in Overleaf. I read the live Week 8 page and Project checklist and used two single-column figures. The Wikipedia and festival-count panels share an excess-assortativity axis in `fig1`. National booking concentration is panel C. The pooled and yearly sound estimates are in `fig3`. I inspected all 13 existing PNGs on a contact sheet and viewed the original and both paper figures at a 329 px proof width, equivalent to 8.7 cm at 96 dpi. The original's title, “Country assortativity by reach,” is already short. Its numeric ticks and tier labels are cramped, and the three-entry legend is too small. Scaling the 8.1-inch canvas to 8.7 cm makes default 10 pt labels about 4.2 pt. In Fig. 1, panels A and B have unwrapped tier labels and a shared legend for the dark deletion whiskers and grey null bands. Panel C has its own legend. The yearly sound estimates and deletion ranges fit at column width. All exports measure 246.614 pt wide and the PDFs embed Georgia. The script reads saved results from analysis exports. The source analyses apply the shared loader. [Figure script](../../figures/make_figures.py) · [Original plot code](../../watts/reach/analyze.py#L139) · [Week 8](https://sunelehmann.com/socialgraphs2026-web/weeks/week8.html#spine) · [Project checklist](https://sunelehmann.com/socialgraphs2026-web/index.html#checklist)

## Figure plan and captions

**Fig. 1. Country assortativity falls as reach rises.** Excess country assortativity (weighted r minus its null mean) declines across foreign Wikipedia tiers (A, 4,310 acts) and festival counts (B, all 5,712 acts, including unknown Wikipedia reach). Weighted r measures within-country mixing relative to country marginals. Grey bands show the central 95% of 200 centered within-year curveball draws per year using full lineups. Whiskers span estimates after dropping one festival at a time.

**(C)** The average fraction of distinct festivals in each act's most-played country falls from 81.4% to 59.8%. The highest tier sits slightly above its null band. C and the leakage check use a tier-specific curveball null with 2,000 draws per year and tier. Reassigning 22% or 45% of zero-foreign acts without linked articles shrinks the zero-to-one excess gap from 0.062 to 0.008 or 0.017, respectively. The shuffle has no festival memory, so repeat booking can contribute to the excess in C. [PDF](../../figures/fig1.pdf) · [Comparison](../../erdos/reconcile/comparison.csv) · [Leakage check](../../watts/reach/country_gap_leakage.csv) · [Booking concentration](../../watts/reach/national_share.csv)

**Sound figure (`fig3`). Lineup similarity and excess overlap.** Markers show the change in shared acts above the curveball expectation per 0.10 increase in cosine similarity for pooled and yearly fits. Similarity uses acts unique to each lineup in the pair. Fits control for same-country status and year by day-gap bins and exclude same-brand pairs. Lines span estimates from dropping one festival at a time with the pair baselines fixed. Both measures give about 1.3 excess shared acts per 0.10 cosine across 2,610 pairs (+1.28 for Wikipedia intros and +1.36 for strict MusicBrainz tags), with a narrower pooled deletion range for tags. Both point estimates are positive in all nine years. The 2024 Wikipedia deletion range crosses zero (-0.08 to 1.51). Wikipedia intros can also pick up geography and career language. [PDF](../../figures/fig3.pdf) · [Results](../../newman/wikitext/sound_effect.csv)

## Existing PNGs

Paths are relative to `analysis/`. The three story candidates are `country_gap.png`, `country.png` and `genre.png`. The first is the main figure, the second gives the pooled country context, and the third motivates the sound panel. Use the pooled country context in Results and the new national concentration and text panels in the paper.

| PNG | What it shows |
| --- | --- |
| `euler/identity_changes.png` | Link changes under act identity rules in 2019 and 2023. Methods check. |
| `euler/projection_check.png` | Projection nulls under original and proposed act keys. Methods check. |
| `granovetter/launch/launchpads.png` | Festival debut and lead or lag estimates. Outside this story. |
| `granovetter/overlap.png` | Yearly overlap against null for common and all editions. Outside this story. |
| `newman/act_degrees_and_lineups.png` | Act degrees and edition lineup overlap. Data context. |
| `newman/edition_structure.png` | Edition ties, Louvain modularity and seed agreement. Network check. |
| `newman/text/text_and_bridges.png` | Tag agreement and bridge stability. Community analysis. |
| `newman/wikitext/tier_terms.png` | Term frequencies for GB acts at the reach extremes. Text sensitivity. |
| `watts/country.png` | Same-country overlap and GB comparison against null. Supports the opening result. |
| `watts/days.png` | Excess overlap by days between editions. Timing check. |
| `watts/distance.png` | Distance bins with and without the Tomorrowland pair. Distance check. |
| `watts/genre.png` | Tag cosine versus excess overlap by country and match rule. Supports the sound result. |
| `watts/reach/country_gap.png` | Country assortativity and curveball null by reach. Main result. |
