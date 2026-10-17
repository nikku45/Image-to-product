"""Marketplace competition metrics derived from discovered product candidates."""

from typing import Iterable, Tuple

from app.schemas.product import ProductCandidate


def compute_listing_metrics(
    candidates: Iterable[ProductCandidate],
) -> Tuple[int, int]:
    """
    Derive total product listings and unique seller count from candidates.

    Each unique ASIN represents one distinct Amazon.in product listing; we treat
    that as one seller offering for competition summary purposes (per product spec).
    """
    unique_asins = {c.asin for c in candidates if c.asin}
    total_candidates = len(unique_asins)
    total_sellers = total_candidates
    return total_candidates, total_sellers
