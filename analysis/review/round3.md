# Review round 3: MusicBrainz matches

Sample with seed 3 from `data/processed/act_matches.csv`: 40 name, 40 ambiguous, 20 alias (of 37). For each row I compared the matched artist's country, disambiguation and tags with where the act played (from `common.load`), listed the other candidates for the same key by reading the dump once, and searched the web for 9 unclear ones. Labels and reasons are in `analysis/review/match_labels.csv`. `03b_musicbrainz_dump.py` reads cleanly: it keeps the act key from `02`, takes a Clashfinder id if it is the only one, a single primary-name hit as "name", a single alias hit as "alias", and otherwise the artist with most tag and rating votes.

| method | n | correct | wrong | unsure | precision (Wilson 95%) |
| :--- | ---: | ---: | ---: | ---: | :--- |
| name | 40 | 39 | 0 | 1 | 97.5% (87 to 100) |
| alias | 20 | 19 | 1 | 0 | 95% (76 to 99) |
| ambiguous | 40 | 21 | 17 | 2 | 52.5% (37 to 67) |

Unsure counts as not correct. The name and alias rows are mostly plausible-by-fit, not individually confirmed, so read them as lower bounds on how often a unique name is the right act.

**Name and alias.** The one unsure name match is Rosborough (the entry is a Glenn Rosborough with no tags). Alias matches are renames (Eskimo Callboy to Electric Callboy, Mammoth WVH to Mammoth, Apey & the Pea to Lazarvs) and native-script names. The one error is "High School", which matched the alias of a Korean girl group at The Great Escape and Truck.

**Ambiguous.** The most-tagged rule fails when no candidate has real votes. Picks with 0 to 2 votes: 4 correct, 2 unsure, 12 wrong. Picks with 3 to 9 votes: 10 of 15 correct. Picks with 10 or more votes: 7 of 7. By candidate count, keys with 4 or more candidates are right in 9 of 24. Typical errors: a Dutch hard rock band taken for London's Palace, a 1997 US band for the 2017 South London Talk Show, a mastering engineer for Steve Hall, and a Cologne DJ for the techno DJ Imogen at Glastonbury.

**Would a simple rule fix it?**
- A requirement of "some tags" does not: 5 of the 17 wrong picks have tags, from 2 to 4 votes, and correct picks with none exist (Bibi Seck, Rationale, Santu).
- "Prefer a European country" does not either: most wrong picks are already European (NL, DE, FI, CH, GB).
- "Prefer the candidate in the festivals' venue country, then most votes, unless the top pick has 10 or more votes" fixes 7 clearly (FFF at Eurockeennes, Imogen, LICE, Monki, Palace, Talk Show, Ugly), reduces three more to a coin flip between two UK candidates (Matt Wills, Stanleys, DJ Storm), and breaks one correct pick (Serum, whose entry has no country). That would take the sample from 21 to about 27 of 40 (about 67%).
- Simpler and safer: keep ambiguous matches only when the pick has at least 3 votes (17 of 22 correct, 77%) and treat the rest as unmatched. Four keys with no usable candidate (CUT_, Holler, Mr E, Steve Hall) are lost either way.

**For the analysis.** The Watts sound results change little between the two policies (1.27 and 1.23 excess acts per 0.10 cosine), so use the strict set (id, name, alias) as the main version and report the ambiguous version with the 3-vote filter as a check. Report these precisions in the paper's methods; the sample is small, so say the ambiguous figure is 52% with an interval of 37 to 67.
