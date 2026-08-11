"""
Vocabulary statistics tests — log-odds ratio & corpus divergence.
"""

from src.tools.statistics import compute_log_odds_ratio, compute_corpus_divergence

TEXT_A = "lab equipment research computing academic output rankings priority"
TEXT_B = "housing subsidies student insecurity rent burden affordability crisis"


class TestStatistics:
    def test_log_odds_returns_dataframe(self):
        df = compute_log_odds_ratio(TEXT_A, TEXT_B, top_n=5)
        assert hasattr(df, "columns")
        assert "word" in df.columns
        assert "z_score" in df.columns

    def test_log_odds_positive_z_for_faction_a(self):
        df = compute_log_odds_ratio("research computing lab", "housing rent crisis", top_n=5)
        top = df.nlargest(3, "z_score")
        assert any(w in top["word"].values for w in ["research", "computing", "lab"])

    def test_corpus_divergence_jsd_in_range(self):
        div = compute_corpus_divergence(TEXT_A, TEXT_B)
        assert 0.0 <= div["jsd"] <= 1.0

    def test_corpus_divergence_detects_different(self):
        div = compute_corpus_divergence(
            "lab equipment research output academic impact",
            "housing rent affordability student crisis",
        )
        # Different enough that JSD > 0
        assert div["jsd"] > 0

    def test_same_text_near_identical(self):
        div = compute_corpus_divergence("lab equipment research", "lab equipment research")
        assert div["cosine_similarity"] > 0.9

    def test_empty_inputs(self):
        df = compute_log_odds_ratio("", "")
        assert df.empty
        div = compute_corpus_divergence("", "")
        assert div["jsd"] == 0.0
