# AI Methods

This file documents where an AI model touched our data, code or text, which
decisions were ours, and how we checked the AI's output.

## Data collection and cleaning

### Who decided what

| Decision | Proposed by | Decided by | Reason |
| --- | --- | --- | --- |
| Use Clashfinder's API instead of downloading files by hand | Human | Human | Reproducible, and needed for about 300 files |
| Use each edition's "core" clashfinder | AI | Human | It is the version the site marks as the reference one |
| Collect all years 2015-2025 | Human (overruled the AI, which proposed only 2019 and 2022-2025) | Human | To see whether festivals kept presenting the same artists in those years |
| Keep festivals present in at least 4 years | AI | Human | Balance between number of festivals and years covered |
| Check ambiguous festival names (Lollapalooza, Pitchfork, Ultra, Mysteryland) by timezone | Human | Human | Names alone could not tell the countries apart |
| Remove non-music stages by keyword, with exceptions | AI | Human, after reviewing every flagged stage | Talks, circus and theatre are not music |
| Write separate *_clean files instead of overwriting inputs | Human | Human | Each file is produced by one script only |


### Errors we found in the AI's output

- **Rebroadcasts counted as bookings.** The AI's name cleaning removed text in
  brackets, which turned "Lorde (2017)" in Glastonbury 2020 into a new booking.
  We found it by checking one artist across all editions by hand.
- **Input overwritten.** The cleaning script overwrote editions.csv, its own input.
- **Invented example.** The AI used "Lorde (DJ set)" as an example of a name
  variant; we checked and it does not exist in our data.
- **Wrong attribution.** The AI credited a Crossley paper to the wrong co-author;
  we found the correct reference.


### How we checked the data

- Glastonbury 2025: 4,116 shows, compared with Clashfinder's website.
- Glastonbury is absent in 2018, its real fallow year.
- Every edition outside a Europe/... timezone was reviewed and removed.
- Every stage flagged as non-music was reviewed by hand, and those that host
  music were kept.

## Analysis (analysis/)



## Paper and slides

- **AI:** [what was drafted or reviewed with AI]
- **Checks:** every number in the paper was checked against the result tables
  (analysis/review/gaps/review_paper.md).
