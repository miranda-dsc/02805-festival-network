# Review round 1

Checked by running code on the processed data, recomputing numbers, and querying Crossref, DataCite and the ACL Anthology. I did not run the full MusicBrainz job.

## 1. src/03_musicbrainz.py

Checked: reran the act selection on lineups_clean.csv and ids.txt; read the cache (8 acts, 7 done, 1 pending, from a pilot run) and run.log; did not test the match rule on a cache copy because 5 search matches say nothing about precision.

- Selection counts 6,435 acts at two or more festivals, correct as written. It includes 2020 and 2021, rebroadcast rows and Leeds, which the shared rules drop. Under the analysis scope it is 5,701, so 734 requests (about 12%) are spent on acts the analysis never uses. Filter in the script, or the tag table will not match the networks.
- Only 915 of the 5,701 in-scope acts have a Clashfinder mbid; the other ~4,800 go through the search rule.
- Match rule: top hit with score 100 and equal casefolded name. `score_100_hits` is stored but never used, so an act whose name has several score-100 artists (I did not check which ones do; the cache holds too few) is accepted on the first hit. That is a homonym risk exactly where Euler flags short names. Reject when `score_100_hits > 1` or send them to a hand check. The rule is strict on the other side: names ending in "live" or "dj set" or containing "&amp;" (83 act strings still carry HTML entities) fail the name test.
- Clashfinder-id path takes `clashfinder_mbids[0]` even when `mbid_conflict` is true (13 keys).
- Resume works: statuses pending, lookup, done, atomic write, lock. Rate limit is 1.1 s per request, fine for 1 per second. Acts without an id need two requests, so roughly 2 to 3 hours.
- act_tags.csv: columns are consistent with the cache. One row per act and tag, no row for acts without tags, so coverage must be counted from the cache, not the csv.
- Weight: 259 lines against 44 to 100 for src/00 to 02. It rewrites the whole indented JSON with fsync after every state change, about three times per act, which grows quadratic over 6,000 acts. Cut: the Retry-After date parsing, the redirect handling, `search_hits` storage, the status machine (store only finished acts and save every 50), the lock, the random sample printout. About 100 lines would do.

## 2. analysis/euler

Checked: reran `act_identity.py` on the retained rows (rebroadcast and 2020 to 2021 out).

- Reproduced exactly: 55,808 rows, 32,487 keys, 1,793 valid-id rows, 46 id groups, 297 spelling groups, 484 risky keys, observed weighted links 2,485 and 1,168, pair edges 307 and 145 (31 and 24 editions), the 4 approved groups, and the resolved result (2,487 and 1,168 links, pairs unchanged). Merging all spelling groups gives 2,498 and 1,173, so the +13 and +5 are right.
- The 2019 figure uses 31 editions, so Leeds is still in. Newman has 280 links on 30 editions. Rerun after dropping Leeds so the numbers agree.
- The conclusion is supported only in a narrow sense: the identity errors the audit can see change links by about 0.5% (13 of 2,485). Only 3% of rows have an id, so the audit cannot see most homonyms; the 36 and 21 "at most" figures are for a screen, not for errors. Say "not detectable with ids and spelling", not "barely changes".
- Real bug found: "catfish and amp the bottlemen" shows that `02_clean_lineups.py` does not unescape HTML before building act_key. Fixing it in 02 is cleaner than a merge table.
- The z of -12.7 against a null with the same margins says nothing about identity; the findings already note this. Good.

## 3. analysis/kleinberg references

Opened through Crossref: all 16 DOIs resolve and match authors, title, venue, volume and pages. Differences are only years: Lopez and Leenders 2018 online (2019 in print, as written), Crossley 2025 (online 2023), Mulder et al. 2021 (online 2020), Mulder and Hitters 2025 (online 2024). Write one convention. Also checked the DataCite record for 10.7801/822 (title, authors, 2026, Mannheim) and the ACL Anthology page (authors, AKBC 2026, pages 26 to 44, dated October 2026 although the checklist date is November 2026). Priority five all match: Crossley and Emms, Lopez and Leenders, Gastinger et al., Silver et al., Strona et al. Not verified: Adler (escholarship returned 403 and Crossref has no record), the AcousticBrainz dataset page (Zenodo 403), Rosen 1981 (JSTOR, not opened). The MusicBrainz Genre page opens and says what is claimed. Gastinger et al. is listed twice (paper and dataset), fine. refs.bib has no format problems I found, but I did not compile it.

## 4. Reading and Leeds, and the nulls

Recomputed from analysis/watts/pairs.csv (modified 22:10; not yet overwritten when I checked). It still contains Leeds: 136 pairs, 7 of them Reading with Leeds (shared acts 130 to 266, one day apart).

- Same-week (0 to 7 days) excess: 3.36 acts over 379 pairs. Dropping only the 7 Reading to Leeds pairs gives -0.39; dropping all Leeds pairs gives +0.30 over 357. Beyond 61 days it is -0.38 and -0.75. The claim holds for the same-week effect.
- It does not hold for country. Same-country excess falls from 2.38 to 0.91 without Leeds, still positive, and different-country stays at -1.37. Do not extend the claim.
- Per year the same-week mean without Leeds swings from -2.25 to +2.32 with 9 to 103 pairs; 2018 alone has 103 pairs.
- Null fairness: the curveball SD is genuine for the null, but the pairs share editions and the same festivals recur every year, so the pooled z (38.4, 33.4) treats about 2,800 dependent pairs, from about 45 festivals, as if each added information. The sound unit is the festival or the edition. Report an interval from resampling festivals or a per-year consistency count, not the pooled z. The shuffle p floor is 1/241, as seen in the 0.004 values.
- Curveball keeps each act's yearly count but ignores the same act returning to the same festival; "same country" partly picks up festival families (Reading and Leeds, Tomorrowland). Newman's z of -10 for edition links in 9 of 9 years is fairer, since it is one test per year, but the nine years are not independent either.
