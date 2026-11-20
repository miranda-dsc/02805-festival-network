import re
import unicodedata
from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")

# Stages whose name shows they are not music
NON_MUSIC_WORDS = (
    r"walkabout|circus|cabaret|poetry|\bword|speaker|cinema|film|theatre|theater|"
    r"\bkid|children|family|forum|debate|comed|talk|literar|book|workshop|panel|"
    r"conference|lecture|spoken|science|einstein|wellbeing|well-being|yoga|meditat|"
    r"healing|craft|sensation seekers|pavement|astrolabe|politic|q&a"
)
# Stages that match the words above but that we checked by hand and host music
MUSIC_EXCEPTIONS = (
    r"house of books|book of wisdom|rock'n'roll circus|soul circus|silent disco|"
    r"imperial theater|sallis benny theatre|marlborough theatre|talking heads|"
    r"music & film arena|club tent|conference stage"
)

# Entries that are not an act at all
PLACEHOLDERS = (
    r"^(?:tba|tbc|tbd|to be announced|special guests?|see board|"
    r"secret (?:guests?|sets?|show|line ?up|special guests?))\b"
)

# Rebroadcasts, e.g. "Lorde (2017)"
REBROADCAST = r"\((?:19|20)\d{2}\)"

# Country from the clashfinder's timezone
COUNTRY = {
    "Europe/London": "GB", "Europe/Brussels": "BE", "Europe/Madrid": "ES",
    "Europe/Paris": "FR", "Europe/Warsaw": "PL", "Europe/Berlin": "DE",
    "Europe/Budapest": "HU", "Europe/Prague": "CZ", "Europe/Bratislava": "SK",
    "Europe/Amsterdam": "NL", "Europe/Lisbon": "PT", "Europe/Copenhagen": "DK",
    "Europe/Rome": "IT", "Europe/Vienna": "AT",
}


def act_key(name: str) -> str:
    """One key per act, so 'Onyvaa', 'ONYVAA' and 'Onyvaa (live)' count as one."""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    without_brackets = re.sub(r"\(.*?\)|\[.*?\]", " ", text)
    if re.search(r"[a-z0-9]", without_brackets): 
        text = without_brackets
    text = re.sub(r"\s+(dj set|live set|live|dj)$", "", text.strip())
    text = re.sub(r"^the\s+", "", text.strip())
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


shows = pd.read_csv(PROCESSED / "lineups_raw.csv")
editions = pd.read_csv(PROCESSED / "editions.csv")
print(f"Start: {len(shows)} shows, {shows['act'].nunique()} distinct names")

# Remove non-music stages
stage = shows["stage"].str.lower()
non_music = stage.str.contains(NON_MUSIC_WORDS) & ~stage.str.contains(MUSIC_EXCEPTIONS)
removed = (
    shows[non_music].groupby("stage")
    .agg(n_shows=("act", "size"), example_acts=("act", lambda a: " | ".join(a.drop_duplicates().head(3))))
    .sort_values("n_shows", ascending=False)
)
removed.to_csv(PROCESSED / "removed_stages.csv")
shows = shows[~non_music]
print(f"Rule 1: removed {non_music.sum()} shows on {len(removed)} non-music stages")

# Remove placeholders and names with no letters or digits
shows = shows.assign(act_key=shows["act"].map(act_key))
placeholder = shows["act_key"].str.contains(PLACEHOLDERS) | (shows["act_key"] == "")
shows = shows[~placeholder]
print(f"Rule 2: removed {placeholder.sum()} placeholder entries")

# Rebroadcasts are part of the lineup
# Outside 2020-2021, a year in brackets marks a film screening.
has_year = shows["act"].str.contains(REBROADCAST) & (shows["act"] != "Sunday (1994)")  # a real band
year = shows["edition"].map(editions.set_index("edition")["year"])
pandemic = year.isin([2020, 2021])
shows = shows.assign(rebroadcast=has_year & pandemic)
films = has_year & ~pandemic
shows = shows[~films]
print(f"Rule 3: flagged {shows['rebroadcast'].sum()} rebroadcasts (2020-2021), removed {films.sum()} films")

# One row per act per edition
lineups = (
    shows.sort_values("mbid")  # rows with a MusicBrainz ID first
    .groupby(["edition", "act_key"], as_index=False)
    .agg(act=("act", "first"), mbid=("mbid", "first"), rebroadcast=("rebroadcast", "max"))
)
lineups.to_csv(PROCESSED / "lineups_clean.csv", index=False)

# Country for each edition
editions["country"] = editions["timezone"].map(COUNTRY)
editions.to_csv(PROCESSED / "editions_clean.csv", index=False)

print(f"\nResult: {len(lineups)} act-edition rows, {lineups['act_key'].nunique()} distinct acts")
print(f"Acts with a MusicBrainz ID already: {lineups.dropna(subset=['mbid'])['act_key'].nunique()}")