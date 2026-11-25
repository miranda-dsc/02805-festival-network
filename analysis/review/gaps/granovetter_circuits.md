| Item | Status | Effort |
| --- | --- | --- |
| Exact-k national share | Matched and rerun | Done |
| Outside GB | Country deletions checked | Done |
| Tilt by tag status | Checked within reach class | Done |
| Reach labels | Imported from the source | Done |
| Glastonbury 2025 | Edition verified, raw revision open | Done locally |

**Exact k.** We accepted only draws where each sampled act occupied k distinct festivals across its k editions. The national-share excesses were +6.0, +6.1 and +3.5 percentage points for 2, 3 to 4 and 5 or more festivals. The two narrower classes were nearly tied, and the broadest class had the smallest excess. This was a per-act conditional estimate for acts with no observed returns. There was no joint null band for these means. [National share](../../granovetter/circuits_check/national_share.csv)

**Outside GB.** The 57 pair-years came from 21 distinct festival pairs. Removing any one country kept the two narrower classes above chance. The pooled ratio for the broadest class was 0.60 and rose to 1.00 without Belgium (29 observed, 28.89 expected). The pooled deficit depended on Belgium. [Leave-one-country-out counts and ratios](../../granovetter/circuits_check/outside_gb_country_deletions.csv)

**Tilt by tag status.** The untagged tilt was 3.20, 2.81 and 2.46 across the three reach classes, compared with 1.07, 1.22 and 1.15 for strict-tagged acts. The stronger untagged tilt held within each reach class across the fixed-null festival deletions. The reach gradient was clearest among untagged acts and mainly reflected differences in their cross-country overlap relative to the null. [Tilt by reach and tag status](../../granovetter/circuits_check/tilt_by_tags.csv)

**Reach labels.** The check used `circuits.CLASSES` and `circuits.reach_class` from `analysis/circuits/run.py` at commit `ead7208`. We used its 200-draw Curveball generator for the national-share and tilt checks and verified the original edition-weighted share and pooled pair totals. [Run script](../../granovetter/circuits_check/run.py)

**Glastonbury 2025.** The 2,194-key outlier was one real edition, `g2025`. Its festival-wide schedule included some non-music events. It accounted for 22 of 2,610 pair rows and 3.49% of pooled observed overlap. In 2025 it accounted for 26.3% of overlap, but the raw country gap moved by about 0.01 acts per pair when those rows were dropped with the null held fixed. The local raw JSON was unavailable, so the source revision could not be checked. [Pair influence](../../granovetter/circuits_check/largest_edition_pairs.csv) [Clashfinder page](https://clashfinder.com/s/g2025/) [Official Glastonbury programme](https://glastonburyfestivals.co.uk/line-up/line-up-2025/)
