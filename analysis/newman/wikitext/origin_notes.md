Run from the repo root with pandas, spaCy 3.8 and scikit-learn installed.

```sh
python -m pip install --no-deps --target analysis/newman/wikitext/.deps geonamescache==3.0.0 https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
python analysis/newman/wikitext/origin.py
```

The English sentencizer selects the first sentence. We use NORP demonyms next to the main copula and GPEs in origin phrases such as "formed in" or "from". Country and state qualifiers can resolve a city. For an unqualified city, we use the [GeoNames](https://www.geonames.org/) gazetteer of cities with at least 15,000 residents and require either one candidate country or a fourfold population lead over the next country's candidate. An explicit demonym takes precedence over an unqualified city lookup. The rules leave ambiguous and unsupported mentions blank.

We compare inferred countries to MusicBrainz artist countries on rows with both values. For the precision check, we sampled 30 outputs with a country using seed 731 and read the matching Wikipedia intros before scoring the labels. The hand labels are stored independently of the model output. The hand check verifies support in the retrieved intro and leaves article matching and biography accuracy outside its scope.

For the stricter review we kept the original random draw, checked every original fill and drew 50 of the original disagreements using seed 734. The label is one country when supported by a clear nationality or origin. A band’s formation or an act’s stated hometown can resolve multiple nationality labels. We leave competing origins unresolved when the intro gives no single location or when birthplace and hometown point to different countries. A current base does not establish origin. Blank hand labels remain in the audit denominator as unsupported predictions. The disagreement sample compares both sources with the same reading of the intro, which cannot resolve biographical facts the intro leaves out.

The revised rules add demonyms and explicit country names for places missing from our list. Generic Congolese can refer to either republic, so it needs a place or an explicit country name. The script scores both rule sets on the same cases and checks for any extra fills.

The processed CSV keeps only hand-supported predictions when the MusicBrainz country is missing. The audit retains the raw predictions and records absences or disputes. The change table records every country prediction that changed when we expanded the dictionary.

We read all ten leads affected by the expanded demonym list. The canonical export keeps the seven supported codes and blanks the three dual-country leads without a clear tie-breaker. `origin_export_summary.csv` describes the exported codes, while `origin_summary.csv` preserves the original and revised raw extraction scores. The 95% Wilson intervals are in `origin_wilson.csv`.

`second_reader.csv` contains 20 randomly selected intros from the unique cases in the first audit. The labels and notes are blank. Enter one supported country code or leave it blank if the intro cannot resolve a country. Rerunning the exporter preserves the sheet so any labels can be kept.
