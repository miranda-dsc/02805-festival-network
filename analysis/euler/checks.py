import pandas as pd

from act_identity import candidate_groups, resolve_acts, spelling_key

A = "00000000-0000-0000-0000-000000000001"
B = "00000000-0000-0000-0000-000000000002"


def table(rows):
    return pd.DataFrame(rows, columns=["edition", "act_key", "act", "mbid"])


assert spelling_key("Florence + The Machine") == spelling_key("Florence & the Machine")
assert spelling_key("Florence &amp; The Machine") == spelling_key("Florence and the Machine")
assert spelling_key("RØDHÅD") == spelling_key("Rodhad")
assert spelling_key("Fontaines D.C.") == spelling_key("Fontaines DC")

shows = table([("a", "h los", "HÆLOS", A), ("a", "haelos", "Haelos", A),
               ("b", "haelos", "Haelos", A)])
out, mapping, approved = resolve_acts(shows)
assert len(out) == 2
assert out.groupby("edition").act_key.agg(set).iloc[0] == out.groupby("edition").act_key.agg(set).iloc[1]
assert list(shows.act_key) == ["h los", "haelos", "haelos"]
assert out.original_act_key.isin(shows.act_key).all()

for shows in [
    table([("a", "honeyblood", "Honeyblood", A), ("b", "sundara karma", "Sundara Karma", A)]),
    table([("a", "dream state", "Dream State", A), ("b", "dreamstate", "Dreamstate", B)]),
    table([("a", "h e r", "H.E.R.", A), ("b", "her", "Her", A)]),
    table([("a", "h los", "HÆLOS", A), ("b", "haelos", "Haelos", "")]),
]:
    out, mapping, approved = resolve_acts(shows)
    assert out.act_key.nunique() == 2
    assert not approved

shows = table([("a", "first", "!!!", A), ("b", "second", "???", A)])
assert not candidate_groups(shows, "spelling")
print("identity checks passed: alias recovery, conflicting IDs, unrelated names, short names, missing IDs and empty signatures")
