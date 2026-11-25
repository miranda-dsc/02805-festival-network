# Methods

### Data

We used European Clashfinder schedules (CC BY-NC 3.0). The downloader was configured to pause two seconds between sequential requests, compared with the ten seconds declared in robots.txt. The collection date could not be verified. We selected 2015 to 2025 schedules with at least 30 listed acts, keeping the largest per festival-year and requiring four qualifying years. We dated editions by the earliest show and used venue countries. We filtered non-music stages, placeholders and screenings. We normalized billing names by case, accents, brackets, live and DJ suffixes, leading “the,” ampersands and punctuation. Residual HTML entities affected 20 keys. We kept one booking per edition and key and excluded rebroadcasts, Leeds and 2020 to 2021. This left 214 editions, 44 festivals, 53,925 bookings and 32,293 keys. [Clashfinder licence](https://clashfinder.com/s/g2025/)

### MusicBrainz tags and Wikipedia reach

We used the 21 November 2026 MusicBrainz dump. The local archive was dated 22 November. Strict matching used a unique supplied artist ID, normalized primary name or alias, in that order. We set conflicting supplied IDs aside. We weighted tags by positive genre counts where available and tag counts otherwise, with equal total weight per act. Median tag coverage was 35%.

Reach covered 5,712 acts at two or more distinct festivals. It also included 662 ambiguous matches accepted with at least three combined tag and rating votes. We reran reach with strict matches only. We resolved Wikidata redirects and counted open Wikipedia language sitelinks, checking direct URLs where needed. Cache files dated to 24 November 2026 Copenhagen time. We counted editions outside Babel's official, de facto official and regionally official languages for the MusicBrainz artist country, treating Simple English like English. Tiers were 0, 1, 2 to 4, 5 to 9 and 10 or more, with separate unknown-country and unmatched groups. Reach measured linked coverage and depended on editing and matching.

### Networks and text

We weighted yearly edition pairs by shared acts and excluded same-brand pairs from projection statistics. Assortativity measured same-country overlap beyond weighted country marginals. For Fig. 2, we counted each festival once per act and averaged the share in each act's most-played country within tier. We applied the same calculation to shuffled bookings. Curveball preserved yearly lineup sizes and act booking counts. We used 2,000 draws per year and tier for both measures and 9,999 for full-lineup pair expectations. We assessed festival deletions with fixed draws or pair expectations.

We lowercased alphabetic tokens from English introductions and zeroed stop-word weights. We compared TF-IDF cosines from intros and strict tags by yearly Spearman correlation after removing shared acts from each pair. Intro similarity also reflected geography and careers. The agreement null used 200 draws per year within lineup-size thirds, holding tag cosines fixed. We regressed observed minus expected overlap on cosine and same-country status within year and date-gap bins.

### For Results

- Manual checks supported 39 of 40 name matches, 19 of 20 aliases and 17 of 22 accepted ambiguous matches (95% Wilson interval 56.6% to 89.9%). The Wikidata join audit confirmed 29 of 30 identities (95% Wilson interval 83.3% to 99.4%). The miss audit recovered articles for 7 of 20 acts. Each audit used one reader.
- Strict-match assortativity excess was +0.239 at zero foreign editions and -0.002 in the highest tier. Reassigning 22% or 45% of unlinked zero-foreign acts narrowed the zero-minus-one excess contrast from 0.062 to 0.008 or 0.017, respectively.
- National share measured booking concentration and could still reflect festival loyalty. Assortativity could not identify the booking decisions behind the overlap. Intro coverage had a median of 28% per edition, and yearly Wikipedia and tag agreement exceeded the null mean by 0.18 to 0.40.
