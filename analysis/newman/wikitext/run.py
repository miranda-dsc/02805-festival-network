"""compare wikipedia opening paragraphs across lineups and reach tiers"""

import os
import random
import sys
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import spacy
from scipy.sparse import csr_matrix
from scipy.stats import false_discovery_control, rankdata, spearmanr
from sklearn.feature_extraction.text import CountVectorizer

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parents[1]
WATTS = ANALYSIS / "watts"
TIERS = WATTS / "reach" / "tiers.csv"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ANALYSIS), str(WATTS)]
from common import PROCESSED, load
from genre_profiles import MATCHED, profiles, tagged_acts

DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
TOKENIZER = spacy.blank("en").tokenizer
STOPWORDS = spacy.lang.en.stop_words.STOP_WORDS
SEED = 28305
MIN_DOCUMENTS = 5
PROFILE_DRAWS = 200
TIER_DRAWS = 1999


def save(frame, name):
    frame.to_csv(OUT / f"{name}.csv", index=False, float_format="%.8g")


def words(text):
    return [token.lower_ for token in TOKENIZER(text) if token.is_alpha]


def correlation(frame):
    if len(frame) < 3:
        return np.nan
    return spearmanr(frame.wiki_cosine, frame.genre_similarity_strict).statistic


def fit(frame, key):
    values = frame[["excess", "same_country", key]].astype(float)
    values -= values.groupby([frame.year, frame.days_bin], observed=True).transform("mean")
    y, country, cosine = values.to_numpy().T
    beta, _, rank, _ = np.linalg.lstsq(np.column_stack((country, 10 * cosine)), y, rcond=None)
    return beta[1] if rank == 2 else np.nan


def deletions(frame):
    festivals = sorted(set(frame.festival_a) | set(frame.festival_b))
    for festival in festivals:
        yield festival, frame[frame.festival_a.ne(festival) & frame.festival_b.ne(festival)]


def exclusive_cosines(rows, left, right, vectors):
    exclusive = [sorted(rows[a] - rows[b]) for a, b in zip(left, right)]
    exclusive.extend(sorted(rows[b] - rows[a]) for a, b in zip(left, right))
    sizes = np.array([len(row) for row in exclusive])
    indices = np.array([act for row in exclusive for act in row], dtype=int)
    memberships = csr_matrix(
        (np.ones(len(indices)), indices, np.r_[0, sizes.cumsum()]),
        shape=(len(sizes), vectors.shape[0]),
    )
    profiles = memberships @ vectors
    a, b = profiles[:len(left)], profiles[len(left):]
    norm_a = np.asarray(a.multiply(a).sum(axis=1)).ravel()
    norm_b = np.asarray(b.multiply(b).sum(axis=1)).ravel()
    norms = np.sqrt(norm_a * norm_b)
    dot = np.asarray(a.multiply(b).sum(axis=1)).ravel()
    return np.divide(dot, norms, out=np.full(len(dot), np.nan), where=norms > 0)


def shuffled_agreement(group, text_rows, bookings, vectors):
    ordered = sorted(set(group.edition_a) | set(group.edition_b),
                     key=lambda key: (len(bookings[key]), key))
    indices = {key: i for i, key in enumerate(ordered)}
    classes = np.array_split(np.arange(len(ordered)), 3)
    left, right = group.edition_a.map(indices), group.edition_b.map(indices)
    original = [text_rows[key] for key in ordered]
    sizes = np.array([len(row) for row in original])
    target = rankdata(group.genre_similarity_strict)
    np.testing.assert_allclose(exclusive_cosines(original, left, right, vectors), group.wiki_cosine)
    samples = []
    for chain, gap in enumerate((5, 10)):
        rng = random.Random(SEED + int(group.year.iloc[0]) + 100000 * chain)
        rows = [row.copy() for row in original]
        for draw in range(PROFILE_DRAWS // 2 + 1):
            for members in classes:
                if len(members) < 2:
                    continue
                for _ in range((50 if draw == 0 else gap) * len(members)):
                    a, b = rng.sample(members.tolist(), 2)
                    left_only, right_only = rows[a] - rows[b], rows[b] - rows[a]
                    if left_only and right_only:
                        pool = sorted(left_only | right_only)
                        rng.shuffle(pool)
                        shared = rows[a] & rows[b]
                        rows[a] = shared | set(pool[:len(left_only)])
                        rows[b] = shared | set(pool[len(left_only):])
            if draw:
                assert np.array_equal([len(row) for row in rows], sizes)
                for members in classes:
                    observed = np.bincount([act for i in members for act in original[i]],
                                           minlength=vectors.shape[0])
                    shuffled = np.bincount([act for i in members for act in rows[i]],
                                           minlength=vectors.shape[0])
                    assert np.array_equal(observed, shuffled)
                values = exclusive_cosines(rows, left, right, vectors)
                assert np.isfinite(values).all()
                samples.append(float(np.corrcoef(rankdata(values), target)[0, 1]))
    return np.array(samples)


def build_pairs(lineups, editions, wiki, counts, vocab):
    length = np.asarray(counts.sum(axis=1)).ravel()
    df = counts.getnnz(axis=0)
    idf = np.log(len(wiki) / df)
    idf[np.isin(vocab, list(STOPWORDS))] = 0
    tf = counts.multiply(1 / length[:, None])
    vectors = tf.multiply(idf).tocsr()
    wiki_keys = pd.Index(wiki.act_key)
    bookings = lineups.groupby("edition").act_key.agg(set).to_dict()
    text_rows = {edition: set(wiki_keys.get_indexer(sorted(acts))) - {-1}
                 for edition, acts in bookings.items()}
    full = {edition: np.asarray(vectors[sorted(rows)].sum(axis=0)).ravel()
            for edition, rows in text_rows.items()}
    coverage = editions[["year", "edition", "festival"]].copy()
    coverage["lineup_size"] = coverage.edition.map({key: len(v) for key, v in bookings.items()})
    coverage["english_acts"] = coverage.edition.map({key: len(v) for key, v in text_rows.items()})
    coverage["coverage"] = coverage.english_acts / coverage.lineup_size
    save(coverage, "edition_coverage")
    results = []
    for year, group in editions.sort_values("edition").groupby("year"):
        for a, b in combinations(group.edition, 2):
            shared = sorted(text_rows[a] & text_rows[b])
            shared_vector = np.asarray(vectors[shared].sum(axis=0)).ravel() if shared else 0
            left, right = full[a] - shared_vector, full[b] - shared_vector
            count_a = len(text_rows[a]) - len(shared)
            count_b = len(text_rows[b]) - len(shared)
            norm = np.linalg.norm(left) * np.linalg.norm(right)
            cosine = np.clip(left @ right / norm, 0, 1) if count_a and count_b and norm else np.nan
            results.append({"year": year, "edition_a": a, "edition_b": b,
                            "exclusive_wiki_a": count_a, "exclusive_wiki_b": count_b,
                            "wiki_cosine": cosine, "shared_check": len(bookings[a] & bookings[b])})
    pairs = pd.DataFrame(results)
    weights = tagged_acts().query("method in @MATCHED")
    profiles(lineups, editions, pairs, weights, "_strict")
    keys = ["year", "edition_a", "edition_b"]
    inputs = pd.read_csv(WATTS / "pairs.csv", usecols=keys + [
        "festival_a", "festival_b", "same_country", "same_brand", "days_bin",
        "shared_acts", "null_mean", "excess",
    ])
    swap = inputs.edition_a.gt(inputs.edition_b)
    for a, b in (("edition_a", "edition_b"), ("festival_a", "festival_b")):
        inputs.loc[swap, [a, b]] = inputs.loc[swap, [b, a]].to_numpy()
    pairs = pairs.merge(inputs, on=keys, how="left", validate="one_to_one")
    assert pairs.shared_acts.eq(pairs.shared_check).all()
    np.testing.assert_allclose(pairs.excess, pairs.shared_acts - pairs.null_mean, atol=1e-9)
    save(pairs.drop(columns="shared_check"), "edition_pairs")
    results = []
    null_rows = []
    finite = pairs.dropna(subset=["wiki_cosine", "genre_similarity_strict"])
    for year, group in finite.groupby("year"):
        estimates = [correlation(part) for _, part in deletions(group)]
        ranks = group[["wiki_cosine", "genre_similarity_strict"]].rank()
        centered = ranks - ranks.groupby([group.days_bin, group.same_country], observed=True).transform("mean")
        partial = centered.wiki_cosine.corr(centered.genre_similarity_strict)
        observed = correlation(group)
        null = shuffled_agreement(group, text_rows, bookings, vectors)
        null_rows.extend({"year": year, "draw": draw, "spearman": value}
                         for draw, value in enumerate(null, 1))
        results.append({"year": year, "pairs": len(group), "spearman": observed,
                        "null_mean": null.mean(), "excess": observed - null.mean(),
                        "null_sd": null.std(ddof=1),
                        "null_95": np.quantile(null, 0.95),
                        "p_upper": (1 + (null >= observed).sum()) / (len(null) + 1),
                        "spearman_within_day_country": partial,
                        "deletion_min": np.nanmin(estimates), "deletion_max": np.nanmax(estimates)})
    save(pd.DataFrame(results), "tag_agreement")
    save(pd.DataFrame(null_rows), "tag_agreement_null")
    sound = finite.loc[~finite.same_brand].copy()
    results = []
    for key in ("wiki_cosine", "genre_similarity_strict"):
        for year, group in [("all", sound), *sound.groupby("year")]:
            estimates = [fit(part, key) for _, part in deletions(group)]
            results.append({"measure": key, "year": year, "pairs": len(group),
                            "acts_per_0_10": fit(group, key),
                            "deletion_min": np.nanmin(estimates), "deletion_max": np.nanmax(estimates)})
    save(pd.DataFrame(results), "sound_effect")
    print(f"{len(pairs)} same-year pairs, {len(finite)} comparable profiles, {len(sound)} model pairs")


def compare_tiers(wiki, counts, vocab):
    tiers = pd.read_csv(TIERS, keep_default_na=False, dtype={"act_key": str})
    assert tiers.act_key.is_unique
    foreign = pd.to_numeric(tiers.n_foreign, errors="coerce")
    order = (tiers.assign(foreign=foreign).groupby("tier").foreign.median()
             .dropna().sort_values().index.tolist())
    coverage = (tiers.assign(english_text=tiers.act_key.isin(wiki.act_key)).groupby("tier")
                .english_text.agg(acts="size", english="sum").reset_index())
    save(coverage, "tier_coverage")
    low, high = order[0], order[-1]
    assert low != high
    known = tiers.set_index("act_key").reindex(wiki.act_key)
    is_gb = known.home_country.eq("GB")
    low_rows, high_rows = [np.flatnonzero(is_gb & known.tier.eq(tier)) for tier in (low, high)]
    intro_lengths = np.asarray(counts.sum(axis=1)).ravel()

    def rates(rows):
        matrix = counts[rows]
        frequency = np.asarray(matrix.sum(axis=0)).ravel()
        return 10_000 * frequency / frequency.sum(), matrix.getnnz(axis=0), frequency.sum()

    low_rate, low_docs, low_words = rates(low_rows)
    high_rate, high_docs, high_words = rates(high_rows)
    eligible = ~np.isin(vocab, list(STOPWORDS)) & ((low_docs + high_docs) >= MIN_DOCUMENTS)
    difference = (high_rate - low_rate)[eligible]
    combined = np.r_[low_rows, high_rows]
    rng = np.random.default_rng(SEED)
    matrix = counts[combined][:, eligible]
    total = np.asarray(matrix.sum(axis=0)).ravel()
    n_words = intro_lengths[combined]
    extreme = np.zeros(len(difference), dtype=int)
    max_extreme = np.zeros(len(difference), dtype=int)
    for _ in range(TIER_DRAWS):
        order = rng.permutation(len(combined))
        picks = order[:len(low_rows)]
        low_n = n_words[picks].sum()
        low_freq = np.asarray(matrix[picks].sum(axis=0)).ravel()
        null = 10_000 * ((total - low_freq) / (n_words.sum() - low_n) - low_freq / low_n)
        extreme += np.abs(null) >= np.abs(difference)
        max_extreme += np.abs(null).max() >= np.abs(difference)

    terms = pd.DataFrame({
        "term": vocab[eligible], "low_rate": low_rate[eligible], "high_rate": high_rate[eligible],
        "low_documents": low_docs[eligible], "high_documents": high_docs[eligible],
        "difference": difference, "p_two_sided": (1 + extreme) / (1 + TIER_DRAWS),
        "p_max": (1 + max_extreme) / (1 + TIER_DRAWS),
    }).sort_values("difference")
    terms["q_bh"] = false_discovery_control(terms.p_two_sided)
    save(terms, "tier_terms")
    leaders = pd.concat([terms.head(8), terms.tail(8).iloc[::-1]])
    contexts = []
    for row in leaders.itertuples():
        group = low_rows if row.difference < 0 else high_rows
        col = np.searchsorted(vocab, row.term)
        hits = counts[group, col].toarray().ravel()
        rates_per_intro = 10_000 * hits / intro_lengths[group]
        ranked = np.lexsort((group, -intro_lengths[group], -rates_per_intro))
        for position in ranked[:3]:
            if not hits[position]:
                continue
            idx = group[position]
            contexts.append({"term": row.term, "tier": low if row.difference < 0 else high,
                             "act_key": wiki.iloc[idx].act_key, "rate": rates_per_intro[position],
                             "intro": wiki.iloc[idx].intro.translate(DASHES)})
    save(pd.DataFrame(contexts), "tier_term_contexts")
    save(pd.DataFrame({"tier": [low, high], "gb_english": [len(low_rows), len(high_rows)],
                       "gb_words": [low_words, high_words]}), "tier_comparison")
    plot(terms, low, high)
    print(f"{low}: {len(low_rows)} GB intros, {high}: {len(high_rows)} GB intros")


def plot(terms, low, high):
    os.environ.setdefault("MPLBACKEND", "Agg")
    with TemporaryDirectory(dir=OUT) as cache:
        os.environ.setdefault("MPLCONFIGDIR", cache)
        os.environ.setdefault("XDG_CACHE_HOME", cache)
        import matplotlib.pyplot as plt

        plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(6.3, 5.4), layout="constrained")
        ax.scatter(terms.low_rate, terms.high_rate, s=10, color="#537b90", alpha=0.30)
        top = max(terms.low_rate.max(), terms.high_rate.max())
        ax.plot([0, top], [0, top], lw=0.8, color="0.45")
        for rows, color in ((terms.head(4), "#a25437"), (terms.tail(4), "#245d75")):
            ax.scatter(rows.low_rate, rows.high_rate, s=17, color=color)
            for row in rows.itertuples():
                offset = (-4, 4) if row.term == "albums" else (4, 3)
                ax.annotate(row.term, (row.low_rate, row.high_rate), xytext=offset,
                            ha="right" if offset[0] < 0 else "left",
                            textcoords="offset points", fontsize=8, color=color)
        ax.set(xscale="symlog", yscale="symlog", xlabel=f"{low} (per 10,000 words)",
               ylabel=f"{high} (per 10,000 words)", title="GB reach terms")
        ticks = (0, 1, 10, 100)
        ax.set_xticks(ticks, labels=[str(tick) for tick in ticks])
        ax.set_yticks(ticks, labels=[str(tick) for tick in ticks])
        ax.set_xlim(left=0, right=top * 2)
        ax.set_ylim(bottom=0, top=top * 2)
        fig.supxlabel(f"Null: {TIER_DRAWS:,} GB tier label shuffles", fontsize=9)
        fig.savefig(OUT / "tier_terms.png", dpi=180)
        plt.close(fig)


def main():
    lineups, editions = load()
    wiki = pd.read_csv(PROCESSED / "act_wiki.csv", keep_default_na=False, dtype={"act_key": str})
    wiki = wiki.loc[wiki.intro_lang.eq("en") & wiki.intro.ne("") & wiki.act_key.isin(lineups.act_key)]
    wiki = wiki.sort_values("act_key").reset_index(drop=True)
    tokens = wiki.intro.map(words)
    wiki = wiki.loc[tokens.str.len().gt(0)].reset_index(drop=True)
    vectorizer = CountVectorizer(analyzer=str.split)
    counts = vectorizer.fit_transform(tokens[tokens.str.len().gt(0)].map(" ".join)).tocsr()
    vocab = vectorizer.get_feature_names_out()
    print(f"{len(wiki)} English introductions, {len(vocab)} word types")
    if "--tiers-only" not in sys.argv:
        build_pairs(lineups, editions, wiki, counts, vocab)
    if TIERS.exists() and "--pairs-only" not in sys.argv:
        compare_tiers(wiki, counts, vocab)
    elif "--tiers-only" in sys.argv:
        raise FileNotFoundError(TIERS)


if __name__ == "__main__":
    main()
