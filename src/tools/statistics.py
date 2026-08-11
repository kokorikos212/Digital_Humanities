r"""Vocabulary divergence engine — log-odds ratios, JSD, chi-square tests for
comparing two text corpora.

Provides mathematically rigorous implementations of Monroe et al. (2008)
Weighted Log-Odds Ratios with Dirichlet priors, Jensen-Shannon Divergence,
Pearson's Chi-Square Test of Independence, and Vector Cosine Similarity for
computational discourse analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency
from sklearn.feature_extraction.text import CountVectorizer


class DivergenceEngineError(Exception):
    """Base exception for vocabulary divergence engine operations."""

    pass


class EmptyCorpusError(DivergenceEngineError):
    """Raised when input text corpora contain no extractable tokens or are empty."""

    pass


class InvalidParameterError(DivergenceEngineError, ValueError):
    """Raised when a hyperparameter or input argument violates mathematical bounds."""

    pass


def compute_log_odds_ratio(
    text_a: str,
    text_b: str,
    top_n: int = 15,
    prior: float = 0.01,
    token_pattern: str = r"(?u)\b[a-zA-Z]{3,}\b",
    stop_words: str | List[str] | None = "english",
) -> pd.DataFrame:
    r"""Computes Weighted Log-Odds Ratios with an uninformative Dirichlet prior.

    Implements the generative model proposed by Monroe, Colaresi, and Quinn
    (2008) to measure term divergence between two text corpora (:math:`A` and :math:`B`).
    Using raw term counts rather than TF-IDF floats, this function estimates
    posterior log-odds z-scores under a symmetric Dirichlet prior over the
    vocabulary :math:`V`.

    Mathematical Formulation:
        Let :math:`y_{w,A}` and :math:`y_{w,B}` denote raw integer counts of term :math:`w` in
        corpora :math:`A` and :math:`B`. Let :math:`n_A = \sum_{w} y_{w,A}` and
        :math:`n_B = \sum_{w} y_{w,B}` represent total corpus sizes.

        Given prior parameter :math:`\alpha_w = \alpha` for all :math:`w \in V` and total
        prior weight :math:`\alpha_0 = |V|\alpha`, the posterior estimate of log-odds
        ratio :math:`\hat{\delta}_{w}^{(A-B)}` is:

        .. math::

           \hat{\delta}_{w}^{(A-B)} = \ln \left( \frac{y_{w,A} + \alpha}{n_A + \alpha_0 - y_{w,A} - \alpha} \right) - \ln \left( \frac{y_{w,B} + \alpha}{n_B + \alpha_0 - y_{w,B} - \alpha} \right)

        The estimated asymptotic variance :math:`\sigma^2\left(\hat{\delta}_{w}^{(A-B)}\right)` is:

        .. math::

           \sigma^2\left(\hat{\delta}_{w}^{(A-B)}\right) = \frac{1}{y_{w,A} + \alpha} + \frac{1}{y_{w,B} + \alpha}

        The standardized z-score :math:`z_w` is computed as:

        .. math::

           z_w = \frac{\hat{\delta}_{w}^{(A-B)}}{\sqrt{\sigma^2\left(\hat{\delta}_{w}^{(A-B)}\right)}}

    Args:
        text_a: Plaintext string for Corpus/Faction A.
        text_b: Plaintext string for Corpus/Faction B.
        top_n: Positive integer specifying the number of top characteristic
            terms to select per faction (sorted by z-score extremes).
        prior: Positive float representing symmetric Dirichlet prior parameter
            :math:`\alpha` (:math:`\alpha > 0`).
        token_pattern: Regular expression defining token extraction boundaries.
        stop_words: Language string or list of stop words to exclude from
            vectorization.

    Returns:
        pd.DataFrame containing columns:
            - ``word`` (str): Extracted vocabulary term.
            - ``z_score`` (float): Standardized log-odds ratio score (:math:`z_w`).
            - ``count_a`` (int): Absolute frequency in Corpus A.
            - ``count_b`` (int): Absolute frequency in Corpus B.

    Raises:
        InvalidParameterError: If :math:`\text{top\_n} \le 0` or :math:`\alpha \le 0`, or inputs
            are non-string types.
        EmptyCorpusError: If either corpus is empty, contains only whitespace,
            or yields zero vocabulary terms post-tokenization.

    Examples:
        >>> text_1 = "policy proposal funding research lab budget university"
        >>> text_2 = "housing subsidy dorm welfare student emergency grant"
        >>> df = compute_log_odds_ratio(text_1, text_2, top_n=2, prior=0.01)
        >>> list(df.columns)
        ['word', 'z_score', 'count_a', 'count_b']
        >>> len(df) <= 4
        True
    """
    if not isinstance(text_a, str) or not isinstance(text_b, str):
        raise InvalidParameterError(
            f"Expected string inputs for text_a and text_b; received {type(text_a).__name__} and {type(text_b).__name__}."
        )

    if not isinstance(top_n, int) or top_n <= 0:
        raise InvalidParameterError(
            f"Parameter 'top_n' must be a positive integer > 0; received {top_n} (type: {type(top_n).__name__})."
        )

    if not isinstance(prior, (int, float)) or prior <= 0.0:
        raise InvalidParameterError(
            f"Prior parameter 'prior' must be a positive float > 0.0; received {prior}."
        )

    if not text_a.strip():
        raise EmptyCorpusError("Corpus A (text_a) is empty or contains only whitespace.")
    if not text_b.strip():
        raise EmptyCorpusError("Corpus B (text_b) is empty or contains only whitespace.")

    vec = CountVectorizer(stop_words=stop_words, token_pattern=token_pattern)
    try:
        dtm = vec.fit_transform([text_a, text_b]).toarray()
    except ValueError as err:
        raise EmptyCorpusError(
            f"Tokenization yielded zero vocabulary terms across both corpora. Error details: {err}"
        ) from err

    words = np.array(vec.get_feature_names_out())
    if len(words) == 0:
        raise EmptyCorpusError("Extracted vocabulary size is zero after stop-word filtering.")

    y_a = dtm[0].astype(np.float64)
    y_b = dtm[1].astype(np.float64)
    n_a = y_a.sum()
    n_b = y_b.sum()

    if n_a == 0:
        raise EmptyCorpusError("Corpus A yielded zero tokens matching the specified token pattern.")
    if n_b == 0:
        raise EmptyCorpusError("Corpus B yielded zero tokens matching the specified token pattern.")

    alpha_0 = len(words) * prior

    # Log-odds ratio calculation with Dirichlet prior
    log_odds_a = np.log((y_a + prior) / (n_a + alpha_0 - y_a - prior))
    log_odds_b = np.log((y_b + prior) / (n_b + alpha_0 - y_b - prior))
    delta = log_odds_a - log_odds_b

    # Variance and standardized z-scores
    variance = (1.0 / (y_a + prior)) + (1.0 / (y_b + prior))
    z_scores = delta / np.sqrt(variance)

    df = pd.DataFrame(
        {
            "word": words,
            "z_score": z_scores,
            "count_a": y_a.astype(int),
            "count_b": y_b.astype(int),
        }
    )

    top_a = df.nlargest(top_n, "z_score")
    top_b = df.nsmallest(top_n, "z_score")

    return pd.concat([top_a, top_b]).drop_duplicates().reset_index(drop=True)


def compute_corpus_divergence(
    text_a: str,
    text_b: str,
    token_pattern: str = r"(?u)\b[a-zA-Z]{3,}\b",
    stop_words: str | List[str] | None = "english",
    alpha_significance: float = 0.05,
) -> Dict[str, Any]:
    r"""Computes Jensen-Shannon Divergence, Chi-Square independence, and Cosine Similarity.

    Performs distribution analysis across two text corpora by evaluating:
      1. Jensen-Shannon Divergence (:math:`JSD \in [0, 1]` using base 2 log):
         Symmetric measure of information divergence between multinomial distributions :math:`P_A` and :math:`P_B`.
      2. Pearson's Chi-Square (:math:`\chi^2`) Test of Independence:
         Determines whether word occurrences are statistically independent of corpus assignment.
      3. Vector Cosine Similarity (:math:`\cos \theta \in [0, 1]`):
         Measures global geometric alignment over raw term count vectors.

    Mathematical Formulation:
        Let :math:`y_A, y_B \in \mathbb{N}_0^{|V|}` represent raw count vectors.
        Empirical probabilities are :math:`P_A = \frac{y_A}{\sum y_A}` and :math:`P_B = \frac{y_B}{\sum y_B}`.
        Let :math:`M = \frac{1}{2}(P_A + P_B)`.

        .. math::

           JSD(P_A \parallel P_B) = \frac{1}{2} D_{\text{KL}}(P_A \parallel M) + \frac{1}{2} D_{\text{KL}}(P_B \parallel M)

        where:

        .. math::

           D_{\text{KL}}(P \parallel Q) = \sum_{w} P(w) \log_2 \left(\frac{P(w)}{Q(w)}\right)

        The Chi-Square statistic is evaluated over smoothed :math:`2 \times |V|` contingency matrix :math:`C`:

        .. math::

           \chi^2 = \sum_{i=1}^2 \sum_{w=1}^{|V|} \frac{(O_{i,w} - E_{i,w})^2}{E_{i,w}}

    Args:
        text_a: Plaintext string for Corpus/Faction A.
        text_b: Plaintext string for Corpus/Faction B.
        token_pattern: Regular expression defining token extraction boundaries.
        stop_words: Language string or list of stop words to exclude.
        alpha_significance: Significance threshold :math:`\alpha` for hypothesis testing (:math:`0 < \alpha < 1`).

    Returns:
        Dict[str, Any] containing keys:
            - ``jsd`` (float): Bounded Jensen-Shannon Divergence (:math:`[0.0, 1.0]`).
            - ``chi2_p_value`` (float): Asymptotic p-value from Chi-Square test.
            - ``cosine_similarity`` (float): Vector Cosine similarity (:math:`[0.0, 1.0]`).
            - ``statistically_significant`` (bool): True if ``chi2_p_value`` < ``alpha_significance``.

    Raises:
        InvalidParameterError: If non-string inputs or invalid ``alpha_significance`` parameters are supplied.
        EmptyCorpusError: If either corpus is empty or tokenization yields zero vocabulary terms.

    Examples:
        >>> t1 = "the university budget provides funding for laboratory research equipment"
        >>> t2 = "the student assembly demands housing subsidies and affordable dining options"
        >>> metrics = compute_corpus_divergence(t1, t2)
        >>> 0.0 <= metrics['jsd'] <= 1.0
        True
        >>> 0.0 <= metrics['cosine_similarity'] <= 1.0
        True
        >>> isinstance(metrics['statistically_significant'], bool)
        True
    """
    if not isinstance(text_a, str) or not isinstance(text_b, str):
        raise InvalidParameterError(
            f"Expected string inputs for text_a and text_b; received {type(text_a).__name__} and {type(text_b).__name__}."
        )

    if not isinstance(alpha_significance, float) or not (0.0 < alpha_significance < 1.0):
        raise InvalidParameterError(
            f"Parameter 'alpha_significance' must be a float in range (0, 1); received {alpha_significance}."
        )

    if not text_a.strip():
        raise EmptyCorpusError("Corpus A (text_a) is empty or contains only whitespace.")
    if not text_b.strip():
        raise EmptyCorpusError("Corpus B (text_b) is empty or contains only whitespace.")

    vec = CountVectorizer(stop_words=stop_words, token_pattern=token_pattern)
    try:
        dtm = vec.fit_transform([text_a, text_b]).toarray().astype(np.float64)
    except ValueError as err:
        raise EmptyCorpusError(
            f"Tokenization yielded zero vocabulary terms across both corpora. Error details: {err}"
        ) from err

    if dtm.shape[1] == 0:
        raise EmptyCorpusError("Extracted vocabulary matrix contains zero feature columns.")

    sum_a, sum_b = dtm[0].sum(), dtm[1].sum()
    if sum_a == 0:
        raise EmptyCorpusError("Corpus A contains zero valid token occurrences.")
    if sum_b == 0:
        raise EmptyCorpusError("Corpus B contains zero valid token occurrences.")

    # Multinomial probability distributions
    p_a = dtm[0] / sum_a
    p_b = dtm[1] / sum_b

    # Jensen-Shannon Divergence (square of JS distance with base 2 log)
    js_distance = jensenshannon(p_a, p_b, base=2)
    jsd_val = float(js_distance**2)

    # Cosine Similarity
    norm_a = np.linalg.norm(dtm[0])
    norm_b = np.linalg.norm(dtm[1])
    if norm_a == 0.0 or norm_b == 0.0:
        cos_sim = 0.0
    else:
        cos_sim = float(np.dot(dtm[0], dtm[1]) / (norm_a * norm_b))

    # Contingency Table with Laplace smoothing (+1) for Chi-Square test
    contingency = (dtm + 1.0).astype(int)
    try:
        _, p_val, _, _ = chi2_contingency(contingency)
    except ValueError:
        p_val = 1.0

    return {
        "jsd": round(jsd_val, 4),
        "chi2_p_value": round(float(p_val), 5),
        "cosine_similarity": round(cos_sim, 4),
        "statistically_significant": bool(p_val < alpha_significance),
    }