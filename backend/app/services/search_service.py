from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from app.config import get_settings
from app.integrations.serpapi_client import SerpApiClient
from app.schemas.product import ProductCandidate
from app.utils.logging import logger


class SearchService:
    """
    Coordinates Amazon.in product discovery using generated search queries.
    Implements query dispatch fallback and ASIN deduplication policies.
    """

    def __init__(self, serpapi_client: Optional[SerpApiClient] = None):
        self.settings = get_settings()
        self.serpapi_client = serpapi_client or SerpApiClient()

    async def discover_candidates(
        self,
        search_queries: List[str],
    ) -> List[ProductCandidate]:
        """
        Execute search dispatch policy:
        1. Run every generated query up to settings.max_search_queries (default 3).
        2. Merge organic SerpApi listings and deduplicate by ASIN.
        3. Return all unique product listings for ranking and display.
        """
        if not search_queries:
            logger.warning("No search queries provided to SearchService; returning empty candidate list")
            return []

        # Deduplicate and clean queries preserving order
        unique_queries: List[str] = []
        seen_queries: Set[str] = set()
        for q in search_queries:
            clean = q.strip()
            if clean and clean.lower() not in seen_queries:
                unique_queries.append(clean)
                seen_queries.add(clean.lower())

        max_allowed_queries = min(len(unique_queries), self.settings.max_search_queries)
        candidates_by_asin: Dict[str, ProductCandidate] = {}
        queries_executed = 0

        for query in unique_queries[:max_allowed_queries]:
            queries_executed += 1
            logger.info(
                f"Executing search query {queries_executed}/{max_allowed_queries}: '{query}' "
                f"(current unique ASINs: {len(candidates_by_asin)})"
            )

            raw_candidates = await self.serpapi_client.search_amazon(
                query=query,
                limit=self.settings.max_candidates_per_query,
            )

            for item in raw_candidates:
                asin = item.get("asin")
                if not asin or asin in candidates_by_asin:
                    continue  # Deduplicate by ASIN

                # Provisional ranking score for Phase 4; calibrated by MatchingService in Phase 5
                candidate = ProductCandidate(
                    asin=asin,
                    title=item.get("title", ""),
                    product_url=item.get("product_url", f"https://www.amazon.in/dp/{asin}"),
                    image_url=item.get("image_url"),
                    price_amount=item.get("price_amount"),
                    currency=item.get("currency", "INR"),
                    seller_count=item.get("seller_count"),  # Null per ADR-004
                    seller_count_type=item.get("seller_count_type"),
                    match_score=0.75,
                    match_confidence="medium",
                    match_signals={"matched_query": query, "position": len(candidates_by_asin) + 1},
                    source="serpapi",
                    retrieved_at=item.get("retrieved_at") or datetime.now(timezone.utc).isoformat(),
                )
                candidates_by_asin[asin] = candidate

        logger.info(
            f"Search discovery completed: {queries_executed} queries executed, "
            f"{len(candidates_by_asin)} unique candidate ASINs discovered"
        )

        return list(candidates_by_asin.values())
