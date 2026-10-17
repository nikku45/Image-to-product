"""Tests for unique listing / seller competition metrics."""

from app.schemas.product import ProductCandidate
from app.utils.marketplace_metrics import compute_listing_metrics


def _candidate(asin: str) -> ProductCandidate:
    return ProductCandidate(
        asin=asin,
        title=f"Product {asin}",
        product_url=f"https://www.amazon.in/dp/{asin}",
        match_score=0.5,
        match_confidence="medium",
    )


def test_compute_listing_metrics_unique_asins():
    candidates = [_candidate("B000000001"), _candidate("B000000002"), _candidate("B000000001")]
    total_candidates, total_sellers = compute_listing_metrics(candidates)
    assert total_candidates == 2
    assert total_sellers == 2


def test_compute_listing_metrics_empty():
    assert compute_listing_metrics([]) == (0, 0)
