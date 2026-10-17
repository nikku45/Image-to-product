import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.exceptions import ExternalProviderError
from app.integrations.serpapi_client import SerpApiClient, _extract_price_amount
from app.schemas.product import ProductCandidate
from app.services.search_service import SearchService


MOCK_SERPAPI_RESPONSE_PRIMARY = {
    "organic_results": [
        {
            "position": 1,
            "asin": "B08N5WRWNW",
            "title": "Sony WH-1000XM4 Industry Leading Wireless Noise Cancelling Headphones - Black",
            "link": "https://www.amazon.in/dp/B08N5WRWNW",
            "link_clean": "https://www.amazon.in/dp/B08N5WRWNW",
            "thumbnail": "https://m.media-amazon.com/images/I/71o8Q5XJS5L._AC_UY218_.jpg",
            "price": "₹19,990",
            "extracted_price": 19990.0,
            "offers": ["Flat INR 1000 Off on HDFC Cards"],
        },
        {
            "position": 2,
            "asin": "B09Y2MYL5C",
            "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Silver",
            "link": "https://www.amazon.in/dp/B09Y2MYL5C",
            "thumbnail": "https://m.media-amazon.com/images/I/51SKmu2G9FL._AC_UY218_.jpg",
            "price": "₹26,990",
            "extracted_price": 26990.0,
        },
        {
            # Missing ASIN - should be filtered out
            "position": 3,
            "title": "Promotional Banner Without ASIN",
            "link": "https://www.amazon.in/promotions",
        },
    ]
}

MOCK_SERPAPI_RESPONSE_SECONDARY = {
    "organic_results": [
        {
            # Duplicate ASIN from primary - should be deduplicated
            "position": 1,
            "asin": "B08N5WRWNW",
            "title": "Sony WH-1000XM4 Duplicate Result",
            "link": "https://www.amazon.in/dp/B08N5WRWNW",
            "extracted_price": 19990.0,
        },
        {
            # New unique candidate
            "position": 2,
            "asin": "B0B88KSS9V",
            "title": "Bose QuietComfort 45 Bluetooth Wireless Noise Cancelling Headphones",
            "link": "https://www.amazon.in/dp/B0B88KSS9V",
            "thumbnail": "https://m.media-amazon.com/images/I/51JbsHSktkL._AC_UY218_.jpg",
            "price": "₹21,900",
            "extracted_price": 21900.0,
        },
        {
            # Another unique candidate
            "position": 3,
            "asin": "B0C9R7YTK1",
            "title": "Sennheiser Momentum 4 Wireless Headphones",
            "link": "https://www.amazon.in/dp/B0C9R7YTK1",
            "price": "₹24,990",
            "extracted_price": 24990.0,
        },
    ]
}


def test_extract_price_amount_variants():
    """Verify price parsing from extracted_price float and raw currency strings."""
    assert _extract_price_amount({"extracted_price": 14999.50}) == 14999.50
    assert _extract_price_amount({"extracted_price": "2999"}) == 2999.0
    assert _extract_price_amount({"price": "₹19,990.00"}) == 19990.00
    assert _extract_price_amount({"price": "Rs. 4,500"}) == 4500.0
    assert _extract_price_amount({"price": "Unavailable"}) is None
    assert _extract_price_amount({}) is None


@pytest.mark.asyncio
async def test_serpapi_client_unconfigured_error():
    """Verify SerpApiClient raises 503 ExternalProviderError when api_key is None."""
    client = SerpApiClient(api_key=None)
    client._is_configured = False

    with pytest.raises(ExternalProviderError) as exc_info:
        await client.search_amazon("Sony headphones")

    assert exc_info.value.status_code == 503
    assert "SERPAPI_API_KEY is not configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_serpapi_client_empty_query():
    """Verify empty query returns empty candidate list without making HTTP calls."""
    client = SerpApiClient(api_key="valid-key")
    res = await client.search_amazon("   ")
    assert res == []


@pytest.mark.asyncio
async def test_serpapi_client_successful_search_and_normalization():
    """Verify organic results are parsed into normalized candidate schemas with null seller_count."""
    client = SerpApiClient(api_key="valid-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_SERPAPI_RESPONSE_PRIMARY

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        candidates = await client.search_amazon("Sony WH-1000XM4")

        # 3 items in mock response, but 1 lacked ASIN, so 2 should be returned
        assert len(candidates) == 2

        first = candidates[0]
        assert first["asin"] == "B08N5WRWNW"
        assert "Sony WH-1000XM4" in first["title"]
        assert first["product_url"] == "https://www.amazon.in/dp/B08N5WRWNW"
        assert first["price_amount"] == 19990.0
        assert first["currency"] == "INR"
        # ADR-004 compliance: seller_count is strictly None
        assert first["seller_count"] is None
        assert first["seller_count_type"] is None
        assert first["source"] == "serpapi"
        assert "retrieved_at" in first


@pytest.mark.asyncio
async def test_serpapi_client_unauthorized_401():
    """Verify HTTP 401 translates to ExternalProviderError with status 401."""
    client = SerpApiClient(api_key="bad-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Invalid API key"

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ExternalProviderError) as exc_info:
            await client.search_amazon("Sony headphones")

        assert exc_info.value.status_code == 401
        assert "Invalid SerpApi API key" in exc_info.value.message


@pytest.mark.asyncio
async def test_serpapi_client_rate_limit_429():
    """Verify HTTP 429 translates to ExternalProviderError with status 429."""
    client = SerpApiClient(api_key="valid-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ExternalProviderError) as exc_info:
            await client.search_amazon("Sony headphones")

        assert exc_info.value.status_code == 429
        assert "quota exhausted" in exc_info.value.message


@pytest.mark.asyncio
async def test_serpapi_client_timeout():
    """Verify timeout translates to ExternalProviderError with status 504."""
    client = SerpApiClient(api_key="valid-key", timeout_seconds=0.01)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.TimeoutException("Timeout"))):
        with pytest.raises(ExternalProviderError) as exc_info:
            await client.search_amazon("Sony headphones", max_retries=0)

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.message


@pytest.mark.asyncio
async def test_search_service_deduplication_and_bounded_fallback():
    """
    Verify SearchService:
    1. Executes primary query.
    2. Executes every query up to max_search_queries.
    3. Deduplicates ASIN 'B08N5WRWNW' present in both responses.
    4. Binds max queries executed according to max_search_queries.
    """
    mock_client = MagicMock(spec=SerpApiClient)

    async def mock_search(query: str, limit: int = 10, **kwargs):
        if "primary" in query.lower() or "first" in query.lower():
            return [
                {
                    "asin": "B08N5WRWNW",
                    "title": "Sony WH-1000XM4 Primary",
                    "product_url": "https://www.amazon.in/dp/B08N5WRWNW",
                    "price_amount": 19990.0,
                    "currency": "INR",
                    "source": "serpapi",
                },
                {
                    "asin": "B09Y2MYL5C",
                    "title": "Sony WH-1000XM5 Primary",
                    "product_url": "https://www.amazon.in/dp/B09Y2MYL5C",
                    "price_amount": 26990.0,
                    "currency": "INR",
                    "source": "serpapi",
                },
            ]
        else:
            return [
                # Duplicate ASIN
                {
                    "asin": "B08N5WRWNW",
                    "title": "Sony WH-1000XM4 Duplicate",
                    "product_url": "https://www.amazon.in/dp/B08N5WRWNW",
                },
                # Unique ASIN
                {
                    "asin": "B0B88KSS9V",
                    "title": "Bose QC45 Fallback",
                    "product_url": "https://www.amazon.in/dp/B0B88KSS9V",
                    "price_amount": 21900.0,
                },
            ]

    mock_client.search_amazon = AsyncMock(side_effect=mock_search)

    service = SearchService(serpapi_client=mock_client)
    queries = ["First primary query", "Second fallback query", "Third ignored query"]

    candidates = await service.discover_candidates(queries)

    # All allowed queries run so every SerpApi result set is merged (deduped by ASIN)
    assert mock_client.search_amazon.call_count == 3
    assert len(candidates) == 3

    asins = [c.asin for c in candidates]
    # Check deduplication: only 1 instance of B08N5WRWNW
    assert asins.count("B08N5WRWNW") == 1
    assert "B09Y2MYL5C" in asins
    assert "B0B88KSS9V" in asins


@pytest.mark.asyncio
async def test_search_service_runs_all_queries_for_full_discovery():
    """Verify SearchService executes every allowed query to collect all SerpApi listings."""
    mock_client = MagicMock(spec=SerpApiClient)
    mock_client.search_amazon = AsyncMock(return_value=[
        {"asin": f"ASIN{i}", "title": f"Product {i}", "product_url": f"https://www.amazon.in/dp/ASIN{i}"}
        for i in range(5)
    ])

    service = SearchService(serpapi_client=mock_client)
    queries = ["Primary Query", "Secondary Fallback"]

    candidates = await service.discover_candidates(queries)

    assert mock_client.search_amazon.call_count == 2
    assert len(candidates) == 5
