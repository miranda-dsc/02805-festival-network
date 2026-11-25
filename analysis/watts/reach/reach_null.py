"""country mixing and booking concentration under the within-year curveball"""
from concurrent.futures import ThreadPoolExecutor

from numba import njit
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

from run import DAY_EDGES, DAY_LABELS, SEED, SWEEPS, same_brand, trade
from tagged import SAMPLES


@njit(nogil=True)
def draw_statistics(rows, sizes, degrees, seed, pair_index, countries, n_countries,
                    festivals, n_festivals, samples):
    """branch from the shared post-burn-in hub with the observed lineup in row zero"""
    n_editions = len(sizes)
    overlaps = np.zeros((samples + 1, n_editions * (n_editions - 1) // 2), dtype=np.int32)
    countries_by_act = np.zeros((samples + 1, len(degrees), n_countries), dtype=np.uint8)
    festivals_by_act = np.zeros((samples + 1, len(degrees), (n_festivals + 63) // 64),
                               dtype=np.uint64)
    if len(degrees) == 0:
        return overlaps, countries_by_act, festivals_by_act
    np.random.seed(seed)
    booked = np.zeros((n_editions, len(degrees)), dtype=np.bool_)
    for edition, size in enumerate(sizes):
        for act in rows[edition, :size]:
            booked[edition, act] = True
    counts = np.empty_like(degrees)
    sites = np.empty((len(degrees), max(degrees)), dtype=np.int32)
    attempts = SWEEPS * n_editions
    for draw_index in range(samples + 1):
        if draw_index == 0:
            draw = rows
        else:
            draw = rows.copy()
            membership = booked.copy()
            if n_editions > 1:
                trade(draw, sizes, membership, attempts)
        counts[:] = 0
        for edition, size in enumerate(sizes):
            festival = festivals[edition]
            block = festival // 64
            bit = np.uint64(1) << np.uint64(festival % 64)
            for act in draw[edition, :size]:
                n = counts[act]
                if n >= degrees[act] or (n > 0 and sites[act, n - 1] == edition):
                    raise ValueError("act degree or binary lineup changed")
                for j in range(n):
                    overlaps[draw_index, pair_index[sites[act, j], edition]] += 1
                sites[act, n] = edition
                counts[act] += 1
                countries_by_act[draw_index, act, countries[edition]] += 1
                festivals_by_act[draw_index, act, block] |= bit
        if not np.array_equal(counts, degrees):
            raise ValueError("act degree changed")
        if draw_index == 0 and n_editions > 1:
            trade(rows, sizes, booked, attempts)
    return overlaps, countries_by_act, festivals_by_act


def year_draws(editions, lineups, country_index, festival_index, samples):
    year = int(editions["year"].iloc[0])
    selected = lineups[lineups["edition"].isin(editions["edition"])]
    codes, acts = pd.factorize(selected["act_key"], sort=True)
    booked = selected.assign(code=codes).groupby("edition")["code"].agg(set)
    rows = [sorted(booked.get(edition, ())) for edition in editions["edition"]]
    sizes = np.array([len(row) for row in rows])
    slots = np.full((len(rows), sizes.max()), -1, dtype=np.int32)
    for i, row in enumerate(rows):
        slots[i, :sizes[i]] = row
    degrees = np.bincount([act for row in rows for act in row], minlength=len(acts))

    left, right = np.triu_indices(len(rows), k=1)
    pair_index = np.full((len(rows), len(rows)), -1, dtype=np.int32)
    pair_index[left, right] = np.arange(len(left))
    countries = country_index.get_indexer(editions["country"])
    festivals = festival_index.get_indexer(editions["festival"])
    overlaps, country_counts, festival_masks = draw_statistics(
        slots, sizes, degrees, SEED + year, pair_index, countries, len(country_index),
        festivals, len(festival_index), samples)
    if not (overlaps.sum(axis=1) == overlaps[0].sum()).all():
        raise ValueError("total pair overlap changed")

    pairs = pd.DataFrame({"year": year}, index=np.arange(len(left)))
    for col in ("edition", "festival", "country"):
        pairs[f"{col}_a"] = editions[col].to_numpy()[left]
        pairs[f"{col}_b"] = editions[col].to_numpy()[right]
    starts = editions["start_date"].to_numpy()
    days = np.abs(starts[left] - starts[right]) / np.timedelta64(1, "D")
    pairs["days_bin"] = pd.cut(days, DAY_EDGES, labels=DAY_LABELS, right=False)
    pairs["same_country"] = pairs["country_a"].eq(pairs["country_b"])
    pairs["shared_acts"] = overlaps[0]
    pairs["null_mean"] = overlaps[1:].mean(axis=0)
    pairs["excess"] = pairs["shared_acts"] - pairs["null_mean"]
    keep = np.array([not same_brand(a, b) for a, b in
                     zip(pairs["festival_a"], pairs["festival_b"])], dtype=bool)
    print(f"{year}: {len(rows)} editions, {keep.sum()} pairs, {samples} checked shuffles", flush=True)
    return pairs.loc[keep], overlaps[:, keep], acts, country_counts, festival_masks


@njit
def distinct_shares(festival_masks, country_masks):
    shares = np.zeros(len(festival_masks))
    for draw, masks_by_act in enumerate(festival_masks):
        for masks in masks_by_act:
            total, most = 0, 0
            for country in country_masks:
                count = 0
                for block in range(len(masks)):
                    bits = masks[block] & country[block]
                    while bits:
                        bits &= bits - np.uint64(1)
                        count += 1
                total += count
                most = max(most, count)
            shares[draw] += most / total
    return shares / festival_masks.shape[1]


def assortativity(pairs, overlaps, country_index):
    """weighted newman r from symmetric country mixing counts"""
    n_countries = len(country_index)
    left = country_index.get_indexer(pairs["country_a"])
    right = country_index.get_indexer(pairs["country_b"])
    cells = np.concatenate((left * n_countries + right, right * n_countries + left))
    edges = np.tile(np.arange(len(pairs)), 2)
    mapping = coo_matrix((np.ones(len(cells), dtype=np.int8), (cells, edges)),
                         shape=(n_countries ** 2, len(pairs))).tocsr()
    mixing = (mapping @ overlaps.T).T.reshape(-1, n_countries, n_countries)
    total = mixing.sum(axis=(1, 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        e = mixing / total[:, None, None]
        chance = (e.sum(axis=1) * e.sum(axis=2)).sum(axis=1)
        same = np.trace(e, axis1=1, axis2=2)
        return np.divide(same - chance, 1 - chance,
                         out=np.full(len(overlaps), np.nan), where=chance < 1 - 1e-12)


def summarize(values, label):
    observed = values[0]
    null = values[1:]
    null = null[np.isfinite(null)]
    mean = null.mean() if len(null) else np.nan
    sd = null.std(ddof=1) if len(null) > 1 else np.nan
    low, high = np.quantile(null, [0.025, 0.975]) if len(null) else (np.nan, np.nan)
    return {label: observed, f"{label}_null_mean": mean, f"{label}_null_sd": sd,
            f"{label}_null_low": low, f"{label}_null_high": high, f"{label}_excess": observed - mean}


def tier_null(lineups, editions, samples=SAMPLES):
    if samples < 2 or lineups.empty:
        raise ValueError("need a nonempty tier and at least two shuffles")
    countries = pd.Index(editions["country"].drop_duplicates().sort_values())
    festival_countries = editions[["festival", "country"]].drop_duplicates().set_index("festival")
    festivals = festival_countries.index
    if not festivals.is_unique:
        raise ValueError("festival country varies across editions")
    country_masks = np.zeros((len(countries), (len(festivals) + 63) // 64), dtype=np.uint64)
    for festival, country in enumerate(countries.get_indexer(festival_countries["country"])):
        country_masks[country, festival // 64] |= np.uint64(1) << np.uint64(festival % 64)
    degrees = lineups.groupby("act_key").size().sort_index()
    dtype = np.min_scalar_type(degrees.max())
    country_counts = np.zeros((samples + 1, len(degrees), len(countries)), dtype=dtype)
    festival_masks = np.zeros((samples + 1, len(degrees), country_masks.shape[1]), dtype=np.uint64)
    frames, overlaps, years = [], [], []
    groups = [group for _, group in editions.groupby("year")]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = pool.map(lambda group: year_draws(group, lineups, countries, festivals, samples), groups)
        for group, (pairs, weights, acts, counts, masks) in zip(groups, results):
            index = degrees.index.get_indexer(acts)
            country_counts[:, index, :] += counts
            festival_masks[:, index, :] |= masks
            years.append(dict(year=int(group["year"].iloc[0]),
                              **summarize(assortativity(pairs, weights, countries), "r")))
            frames.append(pairs)
            overlaps.append(weights)

    if not (country_counts.sum(axis=2) == degrees.to_numpy()).all():
        raise ValueError("pooled act degree changed")
    shares = (country_counts.max(axis=2) / degrees.to_numpy()).mean(axis=1)
    pairs = pd.concat(frames, ignore_index=True)
    weights = np.concatenate(overlaps, axis=1)
    summary = summarize(assortativity(pairs, weights, countries), "r")
    yearly = pd.DataFrame(years)
    deletions = []
    for festival in sorted(festivals):
        keep = ~pairs["festival_a"].eq(festival) & ~pairs["festival_b"].eq(festival)
        r = assortativity(pairs[keep], weights[:, keep], countries)
        if np.isfinite(r[0]) and np.isfinite(r[1:]).any():
            deletions.append(r[0] - np.nanmean(r[1:]))
    summary.update(r_positive_years=int(yearly["r_excess"].gt(0).sum()),
                   r_defined_years=int(yearly["r_excess"].notna().sum()),
                   r_deletion_min=min(deletions, default=np.nan),
                   r_deletion_max=max(deletions, default=np.nan))
    summary.update(summarize(shares, "one_country"))
    summary.update(summarize(distinct_shares(festival_masks, country_masks), "one_country_distinct"))
    return pairs, summary, yearly
