from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

DATA = Path("data/processed")
MATCHED = ("clashfinder id", "name", "alias")
MIN_COVERAGE = 0.5


def tagged_acts():
    matches = pd.read_csv(DATA / "act_matches.csv", keep_default_na=False)
    tags = pd.read_csv(DATA / "act_tags.csv", keep_default_na=False, na_values=[""])
    matches = matches[matches["mbid"].ne("")]
    tags = tags.merge(matches[["act_key", "mbid", "method"]], on=["act_key", "mbid"],
                      validate="many_to_one")
    tags["weight"] = tags["genre_count"].fillna(tags["tag_count"])
    return tags[tags["tag"].notna() & tags["weight"].gt(0)]


def profiles(lineups, editions, pairs, tags, suffix):
    acts = pd.Index(tags["act_key"].unique())
    vocab = pd.Index(tags["tag"].unique())
    weights = tags["weight"] / tags.groupby("act_key")["weight"].transform("sum")
    matrix = csr_matrix(
        (weights, (acts.get_indexer(tags["act_key"]), vocab.get_indexer(tags["tag"]))),
        shape=(len(acts), len(vocab)),
    )
    rows = {edition: set() for edition in editions["edition"]}
    codes = acts.get_indexer(lineups["act_key"])
    for edition, code in zip(lineups.loc[codes >= 0, "edition"], codes[codes >= 0]):
        rows[edition].add(code)

    full = np.stack([np.asarray(matrix[sorted(row)].sum(axis=0)).ravel() for row in rows.values()])
    df = (full > 0).sum(axis=0)
    idf = 1 + np.log((1 + len(full)) / (1 + df))
    tagged_count = pd.Series({edition: len(row) for edition, row in rows.items()})
    coverage = tagged_count / lineups.groupby("edition").size()
    low = coverage.lt(MIN_COVERAGE) | coverage.isna()

    similarity, count_a, count_b = [], [], []
    for a, b in zip(pairs["edition_a"], pairs["edition_b"]):
        left, right = sorted(rows[a] - rows[b]), sorted(rows[b] - rows[a])
        count_a.append(len(left))
        count_b.append(len(right))
        if not left or not right:
            similarity.append(np.nan)
            continue
        va, vb = [(np.asarray(matrix[codes].sum(axis=0)).ravel() * idf)
                  for codes in (left, right)]
        cosine = (va @ vb) / (np.linalg.norm(va) * np.linalg.norm(vb))
        similarity.append(np.clip(cosine, 0, 1))

    pairs[f"genre_similarity{suffix}"] = similarity
    pairs[f"exclusive_tagged_a{suffix}"] = count_a
    pairs[f"exclusive_tagged_b{suffix}"] = count_b
    pairs[f"low_coverage{suffix}"] = pairs["edition_a"].map(low) | pairs["edition_b"].map(low)
    return {
        f"tagged_acts{suffix}": editions["edition"].map(tagged_count),
        f"coverage{suffix}": editions["edition"].map(coverage),
        f"low_coverage{suffix}": editions["edition"].map(low),
    }


def genre_profiles(lineups, editions, pairs):
    tags = tagged_acts()
    pairs = pairs.copy()
    coverage = editions[["edition", "festival", "year"]].copy()
    coverage["lineup_size"] = editions["edition"].map(lineups.groupby("edition").size()).fillna(0)
    for suffix, methods in (("", (*MATCHED, "ambiguous")), ("_strict", MATCHED)):
        eligible = tags[tags["method"].isin(methods)]
        coverage = coverage.assign(**profiles(lineups, editions, pairs, eligible, suffix))
    return pairs, coverage
