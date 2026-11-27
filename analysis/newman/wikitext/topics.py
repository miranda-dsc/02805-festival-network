"""lda topics on english wikipedia intros, compared between the two ends of the reach scale"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(OUT))
from run import PROCESSED, STOPWORDS, TIERS, load, words

TOPICS = 8
SEEDS = (28305, 1, 2, 3, 4)
DRAWS = 1999
LOW, HIGH = "0 foreign", "10 or more foreign"
TOP_WORDS = 10


def fit(counts, seed):
    lda = LatentDirichletAllocation(n_components=TOPICS, learning_method="batch",
                                    max_iter=50, random_state=seed)
    mix = lda.fit_transform(counts)
    return lda, mix / mix.sum(axis=1, keepdims=True)


def match(reference, other):
    """closest topic in another fit for each reference topic, by word cosine"""
    a = reference / np.linalg.norm(reference, axis=1, keepdims=True)
    b = other / np.linalg.norm(other, axis=1, keepdims=True)
    similarity = a @ b.T
    best = similarity.argmax(axis=1)
    return best, similarity[np.arange(len(best)), best]


def compare(mix, low, high, rng):
    """difference in mean topic share, high minus low, against shuffled reach labels"""
    rows = np.r_[low, high]
    observed = mix[high].mean(axis=0) - mix[low].mean(axis=0)
    extreme = np.zeros(TOPICS, dtype=int)
    max_extreme = np.zeros(TOPICS, dtype=int)
    for _ in range(DRAWS):
        order = rng.permutation(rows)
        null = mix[order[len(low):]].mean(axis=0) - mix[order[:len(low)]].mean(axis=0)
        extreme += np.abs(null) >= np.abs(observed)
        max_extreme += np.abs(null).max() >= np.abs(observed)
    return observed, (extreme + 1) / (DRAWS + 1), (max_extreme + 1) / (DRAWS + 1)


def main():
    lineups, _ = load()
    wiki = pd.read_csv(PROCESSED / "act_wiki.csv", keep_default_na=False, dtype={"act_key": str})
    wiki = wiki.loc[wiki.intro_lang.eq("en") & wiki.intro.ne("") & wiki.act_key.isin(lineups.act_key)]
    wiki = wiki.sort_values("act_key").reset_index(drop=True)
    text = wiki.intro.map(lambda intro: " ".join(word for word in words(intro) if word not in STOPWORDS))
    wiki, text = wiki.loc[text.ne("")].reset_index(drop=True), text.loc[text.ne("")].reset_index(drop=True)
    vectorizer = CountVectorizer(analyzer=str.split, min_df=5, max_df=0.5)
    counts = vectorizer.fit_transform(text)
    vocab = vectorizer.get_feature_names_out()
    print(f"{len(wiki)} intros, {len(vocab)} word types after stop words and document limits")

    fits = {seed: fit(counts, seed) for seed in SEEDS}
    lda, mix = fits[SEEDS[0]]

    tiers = pd.read_csv(TIERS, keep_default_na=False, dtype={"act_key": str}).set_index("act_key")
    known = tiers.reindex(wiki.act_key)
    rng = np.random.default_rng(SEEDS[0])
    result = []
    for scope, keep in (("all", np.ones(len(wiki), dtype=bool)),
                        ("GB acts", known.home_country.eq("GB").to_numpy())):
        low = np.flatnonzero(keep & known.tier.eq(LOW).to_numpy())
        high = np.flatnonzero(keep & known.tier.eq(HIGH).to_numpy())
        observed, p, p_max = compare(mix, low, high, rng)
        print(f"{scope}: {len(low)} {LOW} and {len(high)} {HIGH} intros")
        for k in range(TOPICS):
            result.append(dict(scope=scope, topic=k + 1, low_acts=len(low), high_acts=len(high),
                               low_share=mix[low, k].mean(), high_share=mix[high, k].mean(),
                               difference=observed[k], p=p[k], p_max=p_max[k]))

    top = [", ".join(vocab[np.argsort(-row)[:TOP_WORDS]]) for row in lda.components_]
    topics = pd.DataFrame({"topic": range(1, TOPICS + 1), "share": mix.mean(axis=0), "top_words": top})
    topics.to_csv(OUT / "topics.csv", index=False, float_format="%.4f")
    result = pd.DataFrame(result)

    # same comparison on refits with other seeds, topics matched to the first fit
    gb = known.home_country.eq("GB").to_numpy()
    low = np.flatnonzero(gb & known.tier.eq(LOW).to_numpy())
    high = np.flatnonzero(gb & known.tier.eq(HIGH).to_numpy())
    seeds = []
    for seed, (other, other_mix) in fits.items():
        best, similarity = match(lda.components_, other.components_)
        for k in range(TOPICS):
            seeds.append(dict(seed=seed, topic=k + 1, matched_cosine=similarity[k],
                              difference=other_mix[high, best[k]].mean() - other_mix[low, best[k]].mean()))
    seeds = pd.DataFrame(seeds)
    seeds.to_csv(OUT / "topics_seeds.csv", index=False, float_format="%.4g")
    print(seeds.pivot(index="topic", columns="seed", values="difference").round(3).to_string())
    result.to_csv(OUT / "topics_by_reach.csv", index=False, float_format="%.4g")
    print(topics.to_string(index=False))
    print(result.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
