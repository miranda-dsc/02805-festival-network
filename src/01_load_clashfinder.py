import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/clashfinder")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

acts = []     
editions = [] 


for path in sorted(RAW.glob("*.json")):
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
        "start_date": first_start[:10],   # week
        "timezone": data["timezone"],     # country
        "n_shows": sum(len(s["events"]) for s in data["locations"]),
    })


acts = pd.DataFrame(acts)
editions = pd.DataFrame(editions)
acts.to_csv(OUT / "lineups_raw.csv", index=False)
editions.to_csv(OUT / "editions.csv", index=False)

print(editions.to_string(index=False))
print(f"\n{len(editions)} editions, {len(acts)} shows, {acts['act'].nunique()} unique acts")