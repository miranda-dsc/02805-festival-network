from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory

OUT = Path(__file__).resolve().parent
mpl_cache = TemporaryDirectory(dir=OUT)
os.environ["MPLCONFIGDIR"] = mpl_cache.name

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SAMPLES = 250
BURN = 24
THIN = 6
SEED = 2815
TOP = 6

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import load, same_brand

plt.rcParams["axes.unicode_minus"] = False


def curveball(state, groups, rng):
    for group in groups:
        order = rng.permutation(group)
        for a, b in zip(order[::2], order[1::2]):
            a_only = state[a] - state[b]
            pool = sorted(a_only | (state[b] - state[a]))
            rng.shuffle(pool)
            shared = state[a] & state[b]
            state[a] = shared.union(pool[:len(a_only)])
            state[b] = shared.union(pool[len(a_only):])


def launches(act, festival, year, country, n_acts, n_festivals, n_years):
    first = np.full(n_acts, n_years)
    np.minimum.at(first, act, year)
    debut = year == first[act]
    first_country = np.full(n_acts, -1)
    first_country[act[debut]] = country[debut]
    abroad = country != first_country[act]
    foreign_debut = np.bincount(act[debut & abroad], minlength=n_acts)
    foreign_later = np.bincount(act[~debut & abroad], minlength=n_acts)
    eligible = (foreign_debut == 0) & (foreign_later > 0)
    credit = debut & eligible[act]
    debut_slots = year[credit] * n_festivals + festival[credit]
    debut_sizes = np.bincount(act[credit], minlength=n_acts)
    counts = np.bincount(debut_slots, weights=1 / debut_sizes[act[credit]],
                         minlength=n_years * n_festivals)
    return counts.reshape(n_years, n_festivals), eligible


def launch_deletions(act, festival, year, country, n_acts, n_festivals, n_years):
    result = np.empty((n_festivals, n_festivals))
    for drop in range(n_festivals):
        keep = festival != drop
        counts, _ = launches(act[keep], festival[keep], year[keep], country[keep],
                             n_acts, n_festivals, n_years)
        result[drop] = counts.sum(axis=0)
    return result


def swap_years(state, occupied, base, starts, sizes, active, festival, rng):
    a = rng.integers(sizes)
    b = (a + rng.integers(1, sizes)) % sizes
    a, b = starts + a, starts + b
    new_a, new_b = base[a] + state[b], base[b] + state[a]
    keep = (active[festival[a], state[b]] & active[festival[b], state[a]]
            & ~occupied[new_a] & ~occupied[new_b])
    occupied[base[a[keep]] + state[a[keep]]] = False
    occupied[base[b[keep]] + state[b[keep]]] = False
    occupied[new_a[keep]] = True
    occupied[new_b[keep]] = True
    a, b = a[keep], b[keep]
    state[a], state[b] = state[b], state[a]


def first_bookings(act, festival, year, n_festivals):
    key = act * n_festivals + festival
    order = np.argsort(key, kind="stable")
    key = key[order]
    starts = np.r_[0, np.flatnonzero(np.diff(key)) + 1]
    key = key[starts]
    first = np.minimum.reduceat(year[order], starts)
    return key // n_festivals, key % n_festivals, first


def lead_edges(act, festival, year, n_festivals, n_years, brand):
    act, festival, year = first_bookings(act, festival, year, n_festivals)
    n_pairs = n_festivals * n_festivals
    slots, outgoing, incoming = [], [], []
    for gap in range(1, np.bincount(act).max()):
        left = np.flatnonzero((act[:-gap] == act[gap:]) & (year[:-gap] != year[gap:]))
        right = left + gap
        forward = year[left] < year[right]
        early = np.where(forward, left, right)
        late = np.where(forward, right, left)
        slots.append(year[early] * n_pairs + festival[early] * n_festivals + festival[late])
        keep = ~brand[festival[early], festival[late]]
        early, late = early[keep], late[keep]
        outgoing.append(year[early] * n_festivals + festival[early])
        incoming.append(year[late] * n_festivals + festival[late])
    edges = np.bincount(np.concatenate(slots), minlength=n_years * n_pairs)
    out = np.bincount(np.concatenate(outgoing), minlength=n_years * n_festivals)
    inc = np.bincount(np.concatenate(incoming), minlength=n_years * n_festivals)
    return edges.reshape(n_years, n_festivals, n_festivals), (out - inc).reshape(n_years, n_festivals)


def deletion_range(values):
    values = values.copy()
    np.fill_diagonal(values, np.nan)
    return np.nanmin(values, axis=0), np.nanmax(values, axis=0)


bookings, editions = load()
if editions[["country", "festival"]].isna().any().any():
    raise ValueError("missing edition country or festival")
if editions.duplicated(["festival", "year"]).any():
    raise ValueError("launch ties require one edition per festival and year")
editions = editions.sort_values(["year", "country", "edition"]).reset_index(drop=True)
festival, festivals = pd.factorize(editions["festival"], sort=True)
country, countries = pd.factorize(editions["country"], sort=True)
year, years = pd.factorize(editions["year"], sort=True)
n_festivals, n_years = len(festivals), len(years)
act_id, acts = pd.factorize(bookings["act_key"], sort=True)
n_acts = len(acts)
edition_index = editions.reset_index().set_index("edition")["index"]
booking_edition = bookings["edition"].map(edition_index).to_numpy()
lineups = [set() for _ in range(len(editions))]
for edition, act in zip(booking_edition, act_id):
    lineups[edition].add(act)
print(f"Loaded {len(bookings)} bookings for {n_acts} acts at {n_festivals} festivals", flush=True)

groups = list(editions.groupby(["year", "country"]).indices.values())
trade_groups = [group for group in groups if len(group) > 1]
country_act = np.unique(act_id * len(countries) + country[booking_edition]) // len(countries)
cross_country = np.bincount(country_act, minlength=n_acts) > 1
cross_id = np.cumsum(cross_country) - 1
n_cross = int(cross_country.sum())
print(f"{n_cross} acts played in multiple countries across the observed years", flush=True)

def score_launches(act, edition):
    keep = cross_country[act]
    edition = edition[keep]
    return cross_id[act[keep]], festival[edition], year[edition], country[edition]


launch_inputs = score_launches(act_id, booking_edition)
launch_args = n_cross, n_festivals, n_years
launch_observed, breakout = launches(*launch_inputs, *launch_args)
assert np.isclose(launch_observed.sum(), breakout.sum())
launch_delete_observed = launch_deletions(*launch_inputs, *launch_args)
brand = np.array([[same_brand(a, b) for b in festivals] for a in festivals])
lead_observed, lead_net = lead_edges(act_id, festival[booking_edition], year[booking_edition],
                                    n_festivals, n_years, brand)
print(f"{breakout.sum()} qualifying breakouts and {lead_observed.sum()} directed act counts", flush=True)

rng = np.random.default_rng(SEED)
launch_null = np.zeros_like(launch_observed)
launch_delete_null = np.zeros_like(launch_delete_observed)
lead_null = np.zeros_like(lead_observed, dtype=float)
lead_calendar = np.zeros_like(lead_null)
null_net = np.zeros_like(lead_net, dtype=float)
calendar_net = np.zeros_like(null_net)
launch_chains = np.zeros((2, n_festivals))
lead_chains = np.zeros_like(launch_chains)
sizes = np.array([len(lineup) for lineup in lineups])
group_counts = [
    np.bincount([act for i in group for act in lineups[i]], minlength=n_acts)
    for group in trade_groups
]
edition_slots = np.repeat(np.arange(len(editions)), sizes)
order = np.argsort(act_id, kind="stable")
time_act = act_id[order]
time_festival = festival[booking_edition[order]]
time_year = year[booking_edition[order]]
act_sizes = np.bincount(time_act, minlength=n_acts)
repeat = act_sizes > 1
starts = (np.cumsum(act_sizes) - act_sizes)[repeat]
repeat_sizes = act_sizes[repeat]
base = (time_act * n_festivals + time_festival) * n_years
active = np.zeros((n_festivals, n_years), dtype=bool)
active[festival, year] = True
time_counts = np.bincount(time_act * n_years + time_year, minlength=n_acts * n_years)
year_moves = 0

for sample in range(SAMPLES):
    if sample in (0, SAMPLES // 2):
        state = lineups.copy()
        time_state = time_year.copy()
        occupied = np.zeros(n_acts * n_festivals * n_years, dtype=bool)
        occupied[base + time_state] = True
        for _ in range(BURN):
            curveball(state, trade_groups, rng)
            swap_years(time_state, occupied, base, starts, repeat_sizes, active, time_festival, rng)
    for _ in range(THIN):
        curveball(state, trade_groups, rng)
        swap_years(time_state, occupied, base, starts, repeat_sizes, active, time_festival, rng)
    assert all(len(lineup) == size for lineup, size in zip(state, sizes))
    for group, original in zip(trade_groups, group_counts):
        shuffled = np.bincount([act for i in group for act in state[i]], minlength=n_acts)
        assert np.array_equal(original, shuffled)

    calendar_act = np.fromiter((act for lineup in state for act in lineup), dtype=int)
    launch_inputs = score_launches(calendar_act, edition_slots)
    launch_score, null_breakout = launches(*launch_inputs, *launch_args)
    assert np.array_equal(breakout, null_breakout)
    launch_null += launch_score
    launch_delete_null += launch_deletions(*launch_inputs, *launch_args)
    chain = sample // (SAMPLES // 2)
    launch_chains[chain] += launch_score.sum(axis=0)
    edges, net_by_year = lead_edges(calendar_act, festival[edition_slots], year[edition_slots],
                                    n_festivals, n_years, brand)
    lead_calendar += edges
    calendar_net += net_by_year

    assert active[time_festival, time_state].all()
    assert np.unique(base + time_state).size == len(time_act)
    assert np.array_equal(np.bincount(time_act * n_years + time_state, minlength=len(time_counts)),
                          time_counts)
    year_moves += np.count_nonzero(time_state != time_year)
    edges, net_by_year = lead_edges(time_act, time_festival, time_state, n_festivals, n_years, brand)
    lead_null += edges
    null_net += net_by_year
    lead_chains[chain] += net_by_year.sum(axis=0)
    if (sample + 1) % 50 == 0:
        print(f"Scored {sample + 1} null draws", flush=True)

print(f"{year_moves / SAMPLES:.0f} booking years changed per temporal draw", flush=True)
launch_null /= SAMPLES
launch_delete_null /= SAMPLES
lead_null /= SAMPLES
lead_calendar /= SAMPLES
null_net /= SAMPLES
calendar_net /= SAMPLES
launch_excess = launch_observed - launch_null
launch_low, launch_high = deletion_range(launch_delete_observed - launch_delete_null)

lead_excess = lead_net - null_net
calendar_excess = lead_net - calendar_net
edge_excess = (lead_observed - lead_null).sum(axis=0) * ~brand
lead_low, lead_high = deletion_range(lead_excess.sum(axis=0) - (edge_excess.T - edge_excess))

launch_table = pd.DataFrame(dict(
    festival=festivals, observed=launch_observed.sum(axis=0), expected=launch_null.sum(axis=0),
    excess=launch_excess.sum(axis=0), deletion_low=launch_low, deletion_high=launch_high,
    positive_years=(launch_excess > 1e-8).sum(axis=0),
    eligible_years=(launch_null > 0).sum(axis=0), same_brand=brand.any(axis=1),
    null_chain_gap=np.abs(launch_chains[0] - launch_chains[1]) / (SAMPLES // 2),
)).sort_values("excess", ascending=False)
lead_table = pd.DataFrame(dict(
    festival=festivals, outgoing=(lead_observed * ~brand).sum(axis=(0, 2)),
    incoming=(lead_observed * ~brand).sum(axis=(0, 1)), observed_net=lead_net.sum(axis=0),
    expected_net=null_net.sum(axis=0), excess=lead_excess.sum(axis=0),
    calendar_expected_net=calendar_net.sum(axis=0), calendar_excess=calendar_excess.sum(axis=0),
    deletion_low=lead_low, deletion_high=lead_high, positive_years=(lead_excess > 1e-8).sum(axis=0),
    matched_years=((lead_excess > 1e-8) & (calendar_excess > 1e-8)).sum(axis=0),
    eligible_years=active.sum(axis=1),
    null_chain_gap=np.abs(lead_chains[0] - lead_chains[1]) / (SAMPLES // 2),
)).sort_values("excess", ascending=False)
expected = launch_table["expected"].replace(0, np.nan)
launch_table["observed_over_expected"] = launch_table["observed"] / expected
launch_table.to_csv(OUT / "launchpads.csv", index=False)
lead_table.to_csv(OUT / "lead_lag.csv", index=False)

source, target = np.where((lead_observed + lead_null + lead_calendar).sum(axis=0) > 0)
pd.DataFrame(dict(
    source=festivals[source], target=festivals[target],
    observed=lead_observed.sum(axis=0)[source, target],
    year_shuffle_mean=lead_null.sum(axis=0)[source, target],
    calendar_shuffle_mean=lead_calendar.sum(axis=0)[source, target],
    same_brand=brand[source, target],
)).to_csv(OUT / "edges.csv", index=False)
pd.DataFrame(dict(
    year=np.repeat(years, n_festivals), festival=np.tile(festivals, n_years),
    launch_observed=launch_observed.ravel(), launch_null=launch_null.ravel(),
    net_lead_observed=lead_net.ravel(), net_lead_null=null_net.ravel(),
    net_lead_calendar_null=calendar_net.ravel(),
)).to_csv(OUT / "yearly.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.25), layout="constrained")
for ax, table, title, xlabel in zip(
    axes, (launch_table, lead_table), ("Launchpads", "Lead and lag"),
    ("Excess debut credits", "Excess net leads"),
):
    rows = table.head(TOP).iloc[::-1]
    y = np.arange(len(rows))
    ax.hlines(y, rows.deletion_low, rows.deletion_high, color="#557583", linewidth=2, zorder=2)
    ax.scatter(rows.excess, y, color="#175471", s=40, zorder=3)
    if "calendar_excess" in rows:
        ax.scatter(rows.calendar_excess, y, facecolor="white", edgecolor="#ad5e29",
                   marker="D", s=31, zorder=3, label="Calendar null")
        ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.axvline(0, color="0.65", linewidth=1, zorder=1)
    ax.set_yticks(y, rows.festival)
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.set_title(title, loc="left")
    ax.set_xlabel(xlabel)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
fig.supxlabel("Dots show observed minus null. Lines show festival deletion ranges.", fontsize=9)
fig.savefig(OUT / "launchpads.png", dpi=180)
plt.close(fig)
mpl_cache.cleanup()

launch_top = launch_table.head(3).set_index("festival")
lead_top = lead_table.head(2).set_index("festival")
reading = launch_top.loc["reading"]
escape = launch_top.loc["the great escape"]
download = launch_top.loc["download"]
escape_lead = lead_top.loc["the great escape"]
reading_lead = lead_top.loc["reading"]

report = f"""We used the 2015 to 2025 festival records and excluded 2020 and 2021. First means first observed in these records. Both nulls use {SAMPLES} draws.

1. Of {breakout.sum():,} acts first seen in one country and later booked in another, Reading earned {reading.observed:.0f} debut credits against {reading.expected:.0f} expected, The Great Escape {escape.observed:.0f} against {escape.expected:.0f}, and Download {download.observed:.0f} against {download.expected:.0f}.
   All three exceeded the null in every year where they had expected credit ({reading.positive_years:.0f}, {escape.positive_years:.0f}, and {download.positive_years:.0f} years), and their excess stayed positive after dropping any one other festival and rebuilding act histories.
   This captures who booked these acts in their first observed year, splitting credit across tied festivals and shuffling lineups within country and year to hold act histories across countries and lineup sizes fixed.
   It misses bookings outside our records and leaves differences in festival genres in the comparison.

2. The Great Escape and Reading led the ranking with {escape_lead.excess:.0f} and {reading_lead.excess:.0f} more net leads than expected from swapping years within acts' bookings at festivals that ran in those years.
   They were also the top two under the size-preserving calendar null, with positive excess under both nulls in {escape_lead.matched_years:.0f} of {escape_lead.eligible_years:.0f} hosted years for The Great Escape and {reading_lead.matched_years:.0f} of {reading_lead.eligible_years:.0f} for Reading.
   Removing any other festival's edges from the observed and null networks kept both excesses positive.
   This captures earlier bookings minus later bookings across festival pairs, counting each shared act once and leaving same-year ties and the same-brand Tomorrowland pair out of the rankings.
   It misses booking decisions and touring routes outside Clashfinder, so booking first can reflect programming, geography, or coverage.

The figure shows the six largest excesses for each measure. Its lines show festival deletion ranges. The year swap preserves each act's festival and year totals and can change individual edition sizes. The calendar shuffle preserves edition sizes and act totals by country and year.
"""
(OUT / "findings.md").write_text(report, encoding="utf-8")
