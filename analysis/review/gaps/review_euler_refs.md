Review of euler's references: `analysis/kleinberg/refs.bib` (14 entries added, 120 lines, uncommitted) and `analysis/review/gaps/euler_refs.md`. Reviewed 2026-11-25. No files of theirs were edited. GVMH checker passes on `euler_refs.md`.

## Checked online (sample of 10 of the 14 added, plus the existing Strona entry and three claims)

| Entry | Result |
| --- | --- |
| `newman2003mixing` | Matches the APS page: Phys. Rev. E 67(2), 2003, article 026126. |
| `wilson1927` | Matches Crossref: JASA 22(158), 1927, pp. 209 to 212. |
| `benjaminihochberg1995` | Matches the OUP page: JRSS B 57(1), 1995, pp. 289 to 300. |
| `blondel2008louvain` | Matches the IOP page: JSTAT 2008(10), P10008, 9 October 2008. |
| `danon2005nmi` | Matches the IOP page: JSTAT 2005(9), P09008, 26 September 2005. |
| `manning2008ir` | Matches Crossref: Cambridge University Press, 2008, DOI as given. |
| `honnibal2020spacy` | The four authors, title and year 2020 match the project's `CITATION.cff`. The DOI 10.5281/zenodo.1212303 resolves on Zenodo to the v3.7.2 release record (October 2023), so it behaves as the all-versions DOI, which is what `CITATION.cff` itself lists. Acceptable, but it means the DOI does not point at a 2020 artefact; keep the `CITATION.cff` form. |
| `cohen1960kappa` | Not verified online: the SAGE page returned 403. Volume 20(1), pp. 37 to 46 agrees with the standard citation. |
| `strona2014` (existing) | Not verified online: the Nature page redirected to a login. Nature Communications 5, 4114, is the standard citation of the curveball paper. |
| Clashfinder robots | The live `robots.txt` has one group (`user-agent: *`) with `Crawl-delay: 10`, `allow: /`, and disallows only `/show/customise/` and `/!clashfinder_data/`. The downloader requests `/data/event/<id>.json`, which is allowed. Matches `euler_refs.md`. |
| MusicBrainz dump | The listing shows `20261121-001001/` (21 Nov 2026). Matches `musicbrainzartist20261121`. |

Not checked online: `spacyen380`, `clashfinderapi`, `wikidatasitelinks`, `wikipediatextextracts`, `babellanguages` (URL-only entries); the Wikipedia, Wikidata and Babel pages were not fetched.

## Actionable, ranked

1. **Two entries are not independently verified.** `cohen1960kappa` and `strona2014` rest on the standard citation only. Check them by hand in a browser (publisher pages blocked automated fetch) before the paper is frozen. Nothing suggests they are wrong.

2. **Clashfinder Methods claim: the 10-second figure is the site's and the code does not meet it.** The live robots file says `Crawl-delay: 10`; `src/00_download_clashfinder.py` sleeps 2 seconds. The proposed wording ("requested sequentially, the downloader pauses two seconds") is accurate. Keep it, and do not write that the collection followed the crawl delay. The pilot note in `CLAUDE.md` ("at most one page per 10 seconds") is the guidance the code did not follow; one honest sentence in Methods plus a line in the group notes is enough. The downloader's User-Agent contains the repo owner's GitHub name, which is fine for the paper only if nobody quotes the string.

3. **Bib entries lack fields the PNAS style uses.** `spacyen380`, `clashfinderapi`, `wikidatasitelinks`, `wikipediatextextracts` and `babellanguages` have a URL but no `year` or `note` with an access date; the PNAS template will print "n.d." Add `year` and `note = {Accessed 25 November 2026}` (the access date `euler_refs.md` already uses for Clashfinder) to each. `honnibal2020spacy` is a `@misc` with a DOI but no `howpublished`; check how it renders in Overleaf.

4. **The claim map should say which citations will actually appear.** The paper has six pages. Louvain and NMI are cited "if reported"; reach, tags and text do not need Louvain. Cut `blondel2008louvain` and `danon2005nmi` from the paper's bib unless a result uses them, and keep them in `refs.bib` for the project. Unused entries do not print but dangling keys in the text break the build.

5. **Where each key is used.** `euler_refs.md` maps keys to claims but not to paper sections. Add the section (Methods for Clashfinder, MusicBrainz, Babel, spaCy, TF-IDF; Results for Newman assortativity; Methods for Wilson, Benjamini-Hochberg, kappa) so Gustav can place them while writing. Cohen's kappa is cited, but the paper's origin audit has one reader; do not cite kappa as inter-rater unless the second reader (`second_reader.csv`) is labelled.

6. **Links in `euler_refs.md`.** `pure.unamur.be/.../fast.pdf` for Louvain is a repository copy; use the DOI link. The `analysis/newman/run.py:75` and `analysis/newman/text/run.py:209` line references move with edits; use function names.
