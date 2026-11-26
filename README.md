# Festivals in the same country share acts beyond chance, and the effect fades with an act's reach

Final project for 02805 Social Graphs and Interactions, DTU, 2026.
Nandini Karnati, Gustav Maglehøj Hansen and Miranda Caralampio Barrios.

We build the network of European festival editions and the acts they book
(Clashfinder lineups, 2015-2025), compare every overlap with a curveball null,
and test how country, reach and sound shape which festivals share acts.
How we used AI is documented in [AI_METHODS.md](AI_METHODS.md).

## Pipeline (src/)

Run from the repository root, in this order.

| Step | Script | Needs | Writes |
| --- | --- | --- | --- |
| 1 | `00a_find_festivals.py` | `data/raw/events.json` (Clashfinder's list of core clashfinders) | `data/clashfinder_ids.txt`, `candidate_festivals.csv` |
| 2 | `00_download_clashfinder.py` | `credentials.py` with a Clashfinder username and public key | `data/raw/clashfinder/*.json` |
| 3 | `01_load_clashfinder.py` | the downloaded files | `lineups_raw.csv`, `editions.csv` |
| 4 | `02_clean_lineups.py` | step 3 | `lineups_clean.csv`, `editions_clean.csv`, `removed_stages.csv` |
| 5 | `03b_musicbrainz_dump.py` | the MusicBrainz artist dump in `data/raw/musicbrainz/dump/` | `act_matches.csv`, `act_tags.csv` |
| 6 | `04_wikipedia.py` | step 5 | `act_wiki.csv` |

`03_musicbrainz.py` is an earlier version of step 5 that queries the
MusicBrainz API instead of the dump. Tables are written to `data/processed/`.

**Selection and cleaning, in short.** We kept European festivals with a core
clashfinder of at least 30 acts in at least 4 of the years 2015-2025, removed
non-music stages (keyword rule with hand-checked exceptions), placeholders and
film screenings, flagged pandemic rebroadcasts, and merged spelling variants
of act names.

## Analysis (analysis/)

`common.py` loads the cleaned data with the rules every analysis shares:
2020 and 2021, rebroadcasts and Leeds (same lineup as Reading) are excluded,
and each edition gets its venue country.

| Folder | What it does | In the paper |
| --- | --- | --- |
| `watts/` | Country, distance, timing and sound (genre) effects on excess shared acts; `watts/reach/` builds the Wikipedia reach tiers | Results 1 and 4, Fig. 2A and C, Fig. 3 |
| `circuits/` | Country assortativity and national share by festival count | Fig. 2B |
| `erdos/reconcile/` | Both reach measures under the same null | Results 2 |
| `granovetter/` | Trend in overlap over time; `circuits_check/` robustness of the reach results; `launch/` festivals where acts debut | Results 1 and 3 |
| `newman/` | Bipartite network, projections and communities; `text/` tag communities; `wikitext/` Wikipedia introductions, tag agreement, origin audit and second reader | Results 4, Methods |
| `euler/` | Audit of act identities (merged names, conflicting MusicBrainz ids) | Methods |
| `kleinberg/` | Literature notes; `nested/` lineup nestedness | References |
| `figures/` | Scripts for the paper figures | Figs. 1 to 3 |
| `plots/` | Interactive exploratory plots | |
| `review/` | Internal review rounds and hand labels (`match_labels.csv`) | Table 1 |

## Data

The Clashfinder files and the lineup tables derived from them are not
redistributed (CC BY-NC 3.0). The scripts in `src/` regenerate them with a
free Clashfinder account. MusicBrainz data comes from the artist dump of
21 November 2026; Wikipedia data from the Wikidata and Wikipedia APIs.
`credentials.py` and the raw downloads are excluded by `.gitignore`.

## Requirements

Python 3 with pandas, numpy, scipy, matplotlib, requests, babel, spaCy and
scikit-learn.
