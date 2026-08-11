"""
Vocabulary divergence engine — log-odds ratios, JSD, chi-square tests for
comparing faction discourse in multi-turn debates.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency
from sklearn.feature_extraction.text import TfidfVectorizer


def compute_log_odds_ratio(
    text_a: str,
    text_b: str,
    top_n: int = 15,
    prior: float = 0.01,
) -> pd.DataFrame:
    """Weighted log-odds ratio with Dirichlet prior between two text corpora.

    Returns a DataFrame with columns ``word``, ``z_score``, ``count_a``,
    ``count_b`` — the top *top_n* terms for each faction combined.
    Positive z → characteristic of faction A; negative z → faction B.
    """
    if not text_a.strip() or not text_b.strip():
        return pd.DataFrame(columns=["word", "z_score", "count_a", "count_b"])

    vec = TfidfVectorizer(stop_words="english", token_pattern=r"(?u)\b[a-zA-Z]{3,}\b")
    try:
        dtm = vec.fit_transform([text_a, text_b]).toarray()
    except ValueError:
        return pd.DataFrame(columns=["word", "z_score", "count_a", "count_b"])

    words = np.array(vec.get_feature_names_out())
    if len(words) == 0:
        return pd.DataFrame(columns=["word", "z_score", "count_a", "count_b"])

    y_a, y_b = dtm[0], dtm[1]
    n_a, n_b = y_a.sum(), y_b.sum()
    alpha_0 = len(words) * prior

    log_odds = np.log((y_a + prior) / (n_a + alpha_0 - y_a - prior + 1e-9)) - np.log(
        (y_b + prior) / (n_b + alpha_0 - y_b - prior + 1e-9)
    )
    variance = (1.0 / (y_a + prior + 1e-9)) + (1.0 / (y_b + prior + 1e-9))
    z_scores = log_odds / np.sqrt(variance + 1e-9)

    df = pd.DataFrame({"word": words, "z_score": z_scores, "count_a": y_a, "count_b": y_b})
    top_a = df.nlargest(top_n, "z_score")
    top_b = df.nsmallest(top_n, "z_score")
    return pd.concat([top_a, top_b]).drop_duplicates().reset_index(drop=True)


def compute_corpus_divergence(text_a: str, text_b: str) -> Dict[str, Any]:
    """Jensen-Shannon divergence, chi-square p-value, and cosine similarity."""
    if not text_a.strip() or not text_b.strip():
        return {"jsd": 0.0, "chi2_p_value": 1.0, "cosine_similarity": 1.0,
                "statistically_significant": False}

    vec = TfidfVectorizer(stop_words="english", token_pattern=r"(?u)\b[a-zA-Z]{3,}\b")
    try:
        dtm = vec.fit_transform([text_a, text_b]).toarray()
    except ValueError:
        return {"jsd": 0.0, "chi2_p_value": 1.0, "cosine_similarity": 1.0,
                "statistically_significant": False}

    if dtm.shape[1] == 0:
        return {"jsd": 0.0, "chi2_p_value": 1.0, "cosine_similarity": 1.0,
                "statistically_significant": False}

    p_a = dtm[0] / (dtm[0].sum() + 1e-9)
    p_b = dtm[1] / (dtm[1].sum() + 1e-9)

    jsd_val = float(jensenshannon(p_a, p_b))
    cos_sim = float(np.dot(dtm[0], dtm[1]) / (np.linalg.norm(dtm[0]) * np.linalg.norm(dtm[1]) + 1e-9))

    try:
        contingency = np.array([dtm[0], dtm[1]]) + 1
        chi2, p_val, _, _ = chi2_contingency(contingency[:, contingency.sum(axis=0) > 0])
    except ValueError:
        p_val = 1.0

    return {
        "jsd": round(jsd_val, 4),
        "chi2_p_value": round(float(p_val), 5),
        "cosine_similarity": round(cos_sim, 4),
        "statistically_significant": bool(p_val < 0.05),
    }
