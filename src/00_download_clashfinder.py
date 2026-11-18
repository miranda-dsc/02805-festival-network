import sys
import time
from pathlib import Path

import requests

# Find credentials.py in the main folder
sys.path.append(".") 
from credentials import CLASHFINDER_KEY, CLASHFINDER_USER

IDS_FILE = Path("data/clashfinder_ids.txt")
OUT = Path("data/raw/clashfinder")
OUT.mkdir(parents=True, exist_ok=True)

AUTH = {"authUsername": CLASHFINDER_USER, "authPublicKey": CLASHFINDER_KEY}
HEADERS = {"User-Agent": "DTU-02805-festival-project (miranda-dsc on clashfinder)"}

# ------ Read the IDs ----------
ids = []
for line in IDS_FILE.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        ids.append(line)

print(f"{len(ids)} clashfinders in the list")

for cf_id in ids:
    path = OUT / f"{cf_id}.json"

    # Skip files we already have
    if path.exists():
        print(f"{cf_id}: already downloaded")
        continue

    url = f"https://clashfinder.com/data/event/{cf_id}.json"
    response = requests.get(url, params=AUTH, headers=HEADERS, timeout=30)

    if response.status_code == 200:
        path.write_text(response.text, encoding="utf-8")
        print(f"{cf_id}: saved")
    else:
        print(f"{cf_id}: error {response.status_code}")
        print(response.text[:300])  # show the start of the site's message

    time.sleep(2)