"""
Unit tests for MatchingService (Phase 5: Candidate Ranking & Normalization).

Covers:
    - Exact brand + model match → high confidence
    - Partial match → medium confidence
    - Model contradiction → penalty applied, low confidence
    - Missing attributes → treated as unknown (neutral), not mismatch
    - Color/variant mismatch → affects ranking
    - Deterministic ordering for identical inputs
    - Deduplication by ASIN
    - Empty candidate list
    - No-match scenario (all candidates score low)
"""

import pytest
from datetime import datetime, timezone

from app.schemas.product import ImageAnalysis, ProductCandidate
from app.services.matching_service import (
    MatchingService,
    score_candidate,
    _normalize_text,
    _tokenize,
    _token_overlap_score,
    _exact_match,
    WEIGHT_BRAND,
    WEIGHT_MODEL,
    WEIGHT_CATEGORY,
    WEIGHT_VARIANT,
    WEIGHT_OTHER,
    CONTRADICTION_PENALTY,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_analysis(
    *,
    brand: str = None,
    model: str = None,
    category: str = "Smartphone",
    color: str = None,
    visible_text: list = None,
    identifying_attributes: list = None,
    search_queries: list = None,
) -> ImageAnalysis:
    return ImageAnalysis(
        product_category=category,
        brand=brand,
        model=model,
        color=color,
        visible_text=visible_text or [],
        identifying_attributes=identifying_attributes or [],
        uncertainties=[],
        search_queries=search_queries or ["test query"],
    )


def _make_candidate(
    *,
    asin: str = "B0TESTCODE1",
    title: str = "Test Product",
    price_amount: float = None,
    image_url: str = None,
) -> ProductCandidate:
    return ProductCandidate(
        asin=asin,
        title=title,
        product_url=f"https://www.amazon.in/dp/{asin}",
        image_url=image_url,
        price_amount=price_amount,
        currency="INR",
        seller_count=None,
        match_score=0.5,
        match_confidence="medium",
        match_signals=None,
        source="serpapi",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Text normalization helper tests
# ---------------------------------------------------------------------------

class TestTextNormalization:
    def test_normalize_text_basic(self):
        assert _normalize_text("Samsung Galaxy S24 Ultra") == "samsung galaxy s24 ultra"

    def test_normalize_text_with_punctuation(self):
        assert _normalize_text("iPhone 15 Pro (128GB, Blue)") == "iphone 15 pro 128gb blue"

    def test_normalize_text_empty(self):
        assert _normalize_text("") == ""
        assert _normalize_text(None) == ""

    def test_tokenize_removes_noise(self):
        tokens = _tokenize("samsung galaxy for the best quality")
        assert "samsung" in tokens
        assert "galaxy" in tokens
        assert "quality" in tokens
        assert "the" not in tokens
        assert "for" not in tokens
        assert "best" not in tokens

    def test_token_overlap_full(self):
        ref = ["samsung", "galaxy"]
        cand = ["samsung", "galaxy", "s24"]
        assert _token_overlap_score(ref, cand) == 1.0

    def test_token_overlap_partial(self):
        ref = ["samsung", "galaxy", "s24"]
        cand = ["samsung", "galaxy"]
        assert abs(_token_overlap_score(ref, cand) - 2.0 / 3.0) < 0.01

    def test_token_overlap_empty_reference(self):
        assert _token_overlap_score([], ["samsung"]) == 0.0

    def test_exact_match_found(self):
        assert _exact_match("Samsung", "Samsung Galaxy S24 Ultra 256GB") is True

    def test_exact_match_not_found(self):
        assert _exact_match("Apple", "Samsung Galaxy S24 Ultra") is False

    def test_exact_match_unknown(self):
        assert _exact_match(None, "Samsung Galaxy S24") is None
        assert _exact_match("", "Samsung Galaxy S24") is None


# ---------------------------------------------------------------------------
# Score candidate tests
# ---------------------------------------------------------------------------

class TestScoreCandidate:
    """Test the composite scoring function."""

    def test_exact_brand_and_model_match(self):
        """When brand and model both appear in title → high score."""
        analysis = _make_analysis(
            brand="Samsung",
            model="Galaxy S24 Ultra",
            category="Smartphone",
            color="Titanium Black",
        )
        candidate = _make_candidate(
            title="Samsung Galaxy S24 Ultra 256GB Titanium Black Smartphone"
        )

        score, confidence, signals = score_candidate(analysis, candidate)

        assert score >= CONFIDENCE_HIGH_THRESHOLD
        assert confidence == "high"
        assert signals["has_critical_contradiction"] is False

    def test_brand_match_model_missing_from_title(self):
        """Brand matches but model not in title → lower score."""
        analysis = _make_analysis(brand="Samsung", model="Galaxy S24 Ultra")
        candidate = _make_candidate(title="Samsung Phone Case Premium")

        score, confidence, signals = score_candidate(analysis, candidate)

        assert score < CONFIDENCE_HIGH_THRESHOLD
        assert confidence in ("medium", "low")

    def test_model_contradiction_applies_penalty(self):
        """When model tokens don't overlap at all → contradiction penalty."""
        analysis = _make_analysis(brand="Apple", model="iPhone 15 Pro")
        candidate = _make_candidate(title="Apple AirPods Pro 2nd Generation")

        score, confidence, signals = score_candidate(analysis, candidate)

        assert signals["has_critical_contradiction"] is True
        assert signals["contradiction_penalty_applied"] is True
        assert score < CONFIDENCE_MEDIUM_THRESHOLD
        assert confidence == "low"

    def test_missing_brand_treated_as_unknown(self):
        """No brand extracted → brand dimension is neutral, not a mismatch."""
        analysis = _make_analysis(brand=None, model="Galaxy S24")
        candidate = _make_candidate(title="Samsung Galaxy S24 256GB")

        score, confidence, signals = score_candidate(analysis, candidate)

        # Brand signal should be 'unknown'
        brand_signal = next(s for s in signals["attribute_signals"] if s["attribute"] == "brand")
        assert brand_signal["status"] == "unknown"
        # Model match should still contribute
        assert score > 0.5

    def test_missing_model_treated_as_unknown(self):
        """No model extracted → model dimension is neutral."""
        analysis = _make_analysis(brand="Samsung", model=None, category="Smartphone")
        candidate = _make_candidate(title="Samsung Galaxy S24 Ultra")

        score, confidence, signals = score_candidate(analysis, candidate)

        model_signal = next(s for s in signals["attribute_signals"] if s["attribute"] == "model")
        assert model_signal["status"] == "unknown"

    def test_color_match_boosts_variant_score(self):
        """Color appearing in title boosts variant dimension score."""
        analysis = _make_analysis(
            brand="Samsung",
            model="Galaxy S24",
            color="Blue",
        )
        candidate_match = _make_candidate(title="Samsung Galaxy S24 128GB Blue")
        candidate_no_color = _make_candidate(
            asin="B0TESTCODE2", title="Samsung Galaxy S24 128GB Black"
        )

        score_match, _, _ = score_candidate(analysis, candidate_match)
        score_no_color, _, _ = score_candidate(analysis, candidate_no_color)

        assert score_match > score_no_color

    def test_identifying_attributes_contribute(self):
        """Identifying attributes like storage size boost the score."""
        analysis = _make_analysis(
            brand="Samsung",
            model="Galaxy S24",
            identifying_attributes=["256GB", "5G"],
        )
        candidate = _make_candidate(title="Samsung Galaxy S24 256GB 5G Smartphone")

        score, _, signals = score_candidate(analysis, candidate)

        variant_signal = next(s for s in signals["attribute_signals"] if s["attribute"] == "variant")
        assert variant_signal["status"] == "evaluated"
        assert variant_signal["avg_sub_score"] > 0.5

    def test_visible_text_matching(self):
        """Visible text from packaging boosts the 'other' score."""
        analysis = _make_analysis(
            brand="Samsung",
            model="Galaxy S24",
            visible_text=["Samsung", "Galaxy S24", "Made in Vietnam"],
        )
        candidate = _make_candidate(title="Samsung Galaxy S24 Ultra 256GB")

        _, _, signals = score_candidate(analysis, candidate)
        other_signal = next(s for s in signals["attribute_signals"] if s["attribute"] == "other_descriptive")
        assert other_signal["status"] == "evaluated"
        assert other_signal["matched_fragments"] >= 1

    def test_no_attributes_known_gives_neutral_score(self):
        """When no extractable attributes are known, score is 0.5 (neutral)."""
        analysis = _make_analysis(
            brand=None,
            model=None,
            category="",
            color=None,
        )
        # Override product_category to empty
        analysis.product_category = ""
        candidate = _make_candidate(title="Random Product Title")

        score, confidence, signals = score_candidate(analysis, candidate)

        assert score == 0.5
        assert confidence == "low"

    def test_score_clamped_to_valid_range(self):
        """Scores are always in [0.0, 1.0]."""
        analysis = _make_analysis(brand="TestBrand", model="TestModel")
        candidate = _make_candidate(title="Completely Different Product")

        score, _, _ = score_candidate(analysis, candidate)

        assert 0.0 <= score <= 1.0

    def test_category_partial_match(self):
        """Category with partial token overlap gets partial credit."""
        analysis = _make_analysis(category="Wireless Bluetooth Headphones")
        candidate = _make_candidate(title="Premium Wireless Headphones with Active Noise Cancellation")

        _, _, signals = score_candidate(analysis, candidate)
        cat_signal = next(s for s in signals["attribute_signals"] if s["attribute"] == "category")
        assert cat_signal["status"] in ("match", "partial")
        assert cat_signal["contribution"] > 0


# ---------------------------------------------------------------------------
# MatchingService tests
# ---------------------------------------------------------------------------

class TestMatchingService:
    """Test the MatchingService class for ranking and normalization."""

    def test_empty_candidates_returns_empty(self):
        service = MatchingService()
        analysis = _make_analysis(brand="Samsung")
        result = service.rank_candidates(analysis, [])
        assert result == []

    def test_returns_all_candidates_by_default(self):
        """Without max_results, every discovered candidate is returned ranked."""
        service = MatchingService()
        analysis = _make_analysis(brand="Samsung", model="Galaxy S24")

        candidates = [
            _make_candidate(asin=f"B0TESTCOD0{i}", title=f"Product {i}")
            for i in range(5)
        ]
        candidates[2] = _make_candidate(
            asin="B0BEST0001",
            title="Samsung Galaxy S24 256GB Smartphone",
        )

        result = service.rank_candidates(analysis, candidates)
        assert len(result) == 5
        assert result[0].asin == "B0BEST0001"

    def test_returns_top_n_when_max_results_set(self):
        """max_results truncates the ranked list when explicitly configured."""
        service = MatchingService(max_results=3)
        analysis = _make_analysis(brand="Samsung", model="Galaxy S24")

        candidates = [
            _make_candidate(asin=f"B0TESTCOD0{i}", title=f"Product {i}")
            for i in range(5)
        ]
        # Make one clearly better
        candidates[2] = _make_candidate(
            asin="B0BEST0001",
            title="Samsung Galaxy S24 256GB Smartphone",
        )

        result = service.rank_candidates(analysis, candidates)
        assert len(result) == 3
        # Best match should be first
        assert result[0].asin == "B0BEST0001"

    def test_deduplication_by_asin(self):
        """Duplicate ASINs are removed (first occurrence preserved)."""
        service = MatchingService()
        analysis = _make_analysis(brand="Samsung")

        candidates = [
            _make_candidate(asin="B0DUPLICATE", title="Samsung Product A"),
            _make_candidate(asin="B0DUPLICATE", title="Samsung Product B"),
            _make_candidate(asin="B0UNIQUE001", title="Samsung Galaxy"),
        ]

        result = service.rank_candidates(analysis, candidates)

        asins = [c.asin for c in result]
        assert asins.count("B0DUPLICATE") == 1

    def test_deterministic_ordering(self):
        """Same inputs always produce same output ordering."""
        service = MatchingService()
        analysis = _make_analysis(brand="Samsung", model="Galaxy S24")

        candidates = [
            _make_candidate(asin="B0ACODE0001", title="Samsung Galaxy S24"),
            _make_candidate(asin="B0BCODE0002", title="Samsung Galaxy S24 Ultra"),
            _make_candidate(asin="B0CCODE0003", title="Apple iPhone 15"),
        ]

        result1 = service.rank_candidates(analysis, candidates.copy())
        result2 = service.rank_candidates(analysis, candidates.copy())

        # Need to recreate since objects are mutated
        candidates_fresh = [
            _make_candidate(asin="B0ACODE0001", title="Samsung Galaxy S24"),
            _make_candidate(asin="B0BCODE0002", title="Samsung Galaxy S24 Ultra"),
            _make_candidate(asin="B0CCODE0003", title="Apple iPhone 15"),
        ]
        result3 = service.rank_candidates(analysis, candidates_fresh)

        assert [c.asin for c in result1] == [c.asin for c in result3]

    def test_scores_updated_on_candidates(self):
        """After ranking, candidate match_score and match_confidence are updated."""
        service = MatchingService()
        analysis = _make_analysis(brand="Samsung", model="Galaxy S24")

        candidate = _make_candidate(title="Samsung Galaxy S24 256GB")
        result = service.rank_candidates(analysis, [candidate])

        assert len(result) == 1
        assert result[0].match_score != 0.5  # Not the provisional placeholder
        assert result[0].match_confidence in ("high", "medium", "low")
        assert result[0].match_signals is not None
        assert "attribute_signals" in result[0].match_signals

    def test_better_match_ranks_higher(self):
        """Candidate with more attribute matches ranks above one with fewer."""
        service = MatchingService()
        analysis = _make_analysis(
            brand="Samsung",
            model="Galaxy S24 Ultra",
            category="Smartphone",
            color="Titanium Black",
        )

        good_match = _make_candidate(
            asin="B0GOOD00001",
            title="Samsung Galaxy S24 Ultra 256GB Titanium Black Smartphone",
        )
        poor_match = _make_candidate(
            asin="B0POOR00001",
            title="Phone Case Cover for Mobile",
        )

        result = service.rank_candidates(analysis, [poor_match, good_match])

        assert result[0].asin == "B0GOOD00001"
        assert result[0].match_score > result[1].match_score

    def test_model_conflict_ranks_lower(self):
        """A candidate with a conflicting model should rank below a matching one."""
        service = MatchingService()
        analysis = _make_analysis(brand="Apple", model="iPhone 15 Pro")

        matching = _make_candidate(
            asin="B0MATCH0001",
            title="Apple iPhone 15 Pro 256GB Natural Titanium",
        )
        conflicting = _make_candidate(
            asin="B0CONFL0001",
            title="Apple MacBook Air M2 Laptop",
        )

        result = service.rank_candidates(analysis, [conflicting, matching])

        assert result[0].asin == "B0MATCH0001"
        assert result[0].match_confidence in ("high", "medium")
        assert result[1].match_confidence == "low"

    def test_custom_max_results(self):
        """max_results parameter controls output size."""
        service = MatchingService(max_results=1)
        analysis = _make_analysis(brand="Samsung")

        candidates = [
            _make_candidate(asin=f"B0TEST000{i}", title="Samsung Product")
            for i in range(5)
        ]

        result = service.rank_candidates(analysis, candidates)
        assert len(result) == 1

    def test_all_low_confidence_scenario(self):
        """When no candidate matches well, all return low confidence."""
        service = MatchingService()
        analysis = _make_analysis(
            brand="Sony",
            model="WH-1000XM5",
            category="Headphones",
        )

        candidates = [
            _make_candidate(asin="B0WRONG0001", title="Samsung Galaxy S24"),
            _make_candidate(asin="B0WRONG0002", title="Apple iPhone 15 Pro"),
            _make_candidate(asin="B0WRONG0003", title="Bosch Washing Machine"),
        ]

        result = service.rank_candidates(analysis, candidates)

        for c in result:
            assert c.match_confidence == "low"
            assert c.match_score < CONFIDENCE_MEDIUM_THRESHOLD
