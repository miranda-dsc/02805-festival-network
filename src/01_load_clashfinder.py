import json
from pathlib import Path

import pandas as pd

IDS_FILE = Path("data/clashfinder_ids.txt")
RAW = Path("data/raw/clashfinder")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# Only use the clashfinders in our selected list
ids = []
for line in IDS_FILE.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        ids.append(line)

acts = []
editions = [] 

for cf_id in ids:
    path = RAW / f"{cf_id}.json"
    if not path.exists():
        print(f"{cf_id}: not downloaded yet, skipped")
        continue
    data = json.loads(path.read_text(encoding="utf-8"))

    first_start = None
    # Each stage ("location") has a list of shows ("events")
    for stage in data["locations"]:
        for event in stage["events"]:
            acts.append({
                "edition": data["id"],
                "act": event["name"].strip(),
                "stage": stage["name"],
                "start": event["start"],
                "mbid": event.get("mbId"),  
            })
            # Keep the earliest show
            if first_start is None or event["start"] < first_start:
                first_start = event["start"]

    editions.append({
        "edition": data["id"],
        "name": data["name"],
        "year": int(first_start[:4]),
        "start_date": first_start[:10],   # gives us the week
        "timezone": data["timezone"],     # gives us the country
        "n_shows": sum(len(s["events"]) for s in data["locations"]),
    })

# Turn the lists into tables and save them
acts = pd.DataFrame(acts)
editions = pd.DataFrame(editions)
acts.to_csv(OUT / "lineups_raw.csv", index=False)
editions.to_csv(OUT / "editions.csv", index=False)

# Warn about any edition outside Europe
outside = editions[~editions["timezone"].str.startswith("Europe/")]
if len(outside):
    print("WARNING, editions outside Europe:")
    print(outside[["edition", "name", "timezone"]].to_string(index=False))

print(editions.groupby("year")["edition"].count().rename("editions per year").to_string())
print(f"\n{len(editions)} editions, {len(acts)} shows, {acts['act'].nunique()} unique acts")