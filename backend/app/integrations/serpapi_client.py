import asyncio
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings
from app.exceptions import ExternalProviderError
from app.schemas.product import ProductCandidate
from app.utils.logging import logger

SERPAPI_SEARCH_URL = "https://serpapi.com/search"


def _extract_price_amount(item: Dict[str, Any]) -> Optional[float]:
    """
    Safely extract numeric price from SerpApi organic listing item.
    Supports:
    - extracted_price (float/int/numeric string)
    - price (numeric float/int)
    - price (string formatted like '₹14,999.00', 'Rs. 4,500', '1499', '₹1,499 - ₹2,199')
    - prices (list of price objects with 'value' or 'extracted_value')
    Returns None if missing or unparseable.
    """
    # 1. Direct extracted_price
    extracted = item.get("extracted_price")
    if extracted is not None:
        try:
            val = float(extracted)
            if val >= 0:
                return round(val, 2)
        except (ValueError, TypeError):
            pass

    # 2. Direct numeric price field
    raw_price = item.get("price")
    if isinstance(raw_price, (int, float)):
        return round(float(raw_price), 2)

    # 3. String price parsing
    if isinstance(raw_price, str):
        matches = re.findall(r"\d[\d,]*(?:\.\d+)?", raw_price)
        if matches:
            try:
                val = float(matches[0].replace(",", ""))
                return round(val, 2)
            except ValueError:
                pass

    # 4. Check 'prices' array if present in SerpApi response
    prices_list = item.get("prices")
    if isinstance(prices_list, list) and len(prices_list) > 0:
        first_price = prices_list[0]
        if isinstance(first_price, dict):
            val = first_price.get("value") or first_price.get("extracted_value")
            if val is not None:
                try:
                    return round(float(val), 2)
                except (ValueError, TypeError):
                    pass

    return None


def _extract_currency(item: Dict[str, Any], default: str = "INR") -> str:
    """
    Explicitly extract currency code or symbol from SerpApi listing item.
    Defaults to INR for Amazon.in.
    """
    curr = item.get("currency")
    if curr and isinstance(curr, str) and curr.strip():
        return curr.strip()

    price_str = str(item.get("price") or "")
    if "₹" in price_str or "rs" in price_str.lower() or "inr" in price_str.lower():
        return "INR"
    if "$" in price_str or "usd" in price_str.lower():
        return "USD"
    if "€" in price_str or "eur" in price_str.lower():
        return "EUR"
    if "£" in price_str or "gbp" in price_str.lower():
        return "GBP"

    return default


class SerpApiClient:
    """Client adapter for SerpApi Amazon Search API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        amazon_domain: str = "amazon.in",
        timeout_seconds: float = 20.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.serpapi_api_key
        self.amazon_domain = amazon_domain
        self.timeout_seconds = timeout_seconds
        self._is_configured = bool(self.api_key and self.api_key.strip())

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    async def search_amazon(
        self,
        query: str,
        limit: int = 10,
        max_retries: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Execute an Amazon Search query on Amazon.in via SerpApi and return normalized candidate dicts.
        """
        if not self._is_configured:
            raise ExternalProviderError(
                provider="serpapi",
                message="SERPAPI_API_KEY is not configured in .env. Please provide a valid SerpApi API key.",
                status_code=503,
            )

        clean_query = query.strip()
        if not clean_query:
            return []

        params = {
            "engine": "amazon",
            "amazon_domain": self.amazon_domain,
            "k": clean_query,
            "api_key": self.api_key,
        }

        attempts = 0
        last_exception: Optional[Exception] = None

        while attempts <= max_retries:
            attempts += 1
            logger.info(
                f"Dispatching SerpApi Amazon search (attempt {attempts}/{max_retries + 1}): "
                f"domain='{self.amazon_domain}', query='{clean_query}'"
            )

            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(SERPAPI_SEARCH_URL, params=params)

                # Handle specific HTTP error status codes
                if response.status_code == 401 or response.status_code == 403:
                    raise ExternalProviderError(
                        provider="serpapi",
                        message="Invalid SerpApi API key or unauthorized access",
                        status_code=401,
                    )
                elif response.status_code == 429:
                    raise ExternalProviderError(
                        provider="serpapi",
                        message="SerpApi monthly search quota exhausted or rate limit reached",
                        status_code=429,
                    )
                elif response.status_code >= 500:
                    logger.warning(f"SerpApi returned HTTP {response.status_code} on attempt {attempts}")
                    if attempts <= max_retries:
                        await asyncio.sleep(1.0)
                        continue
                    raise ExternalProviderError(
                        provider="serpapi",
                        message=f"SerpApi server error (HTTP {response.status_code})",
                        status_code=502,
                    )
                elif response.status_code != 200:
                    raise ExternalProviderError(
                        provider="serpapi",
                        message=f"SerpApi returned unexpected status {response.status_code}: {response.text[:200]}",
                        status_code=502,
                    )

                data = response.json()

                if "error" in data:
                    err_msg = str(data["error"])
                    logger.error(f"SerpApi response contained error: {err_msg}")
                    raise ExternalProviderError(
                        provider="serpapi",
                        message=f"SerpApi error: {err_msg}",
                        status_code=502,
                    )

                organic_results = data.get("organic_results", [])
                logger.info(f"SerpApi returned {len(organic_results)} organic listings for '{clean_query}'")

                candidates: List[Dict[str, Any]] = []
                retrieval_time = datetime.now(timezone.utc).isoformat()

                for item in organic_results[:limit]:
                    asin = item.get("asin")
                    if not asin:
                        continue  # ASIN is mandatory for marketplace candidate normalization

                    title = item.get("title") or "Unknown Product Title"
                    # Construct verified canonical Amazon.in URL
                    product_url = f"https://www.amazon.in/dp/{asin}"
                    thumbnail = item.get("thumbnail")
                    price_amount = _extract_price_amount(item)
                    currency = _extract_currency(item, default="INR")

                    # Note on seller_count: SerpApi Amazon Search does NOT reliably expose seller count in search snippets.
                    # Per ADR-004 and architecture section 7.3, seller_count is explicitly null.
                    candidate_dict = {
                        "asin": str(asin).strip(),
                        "title": str(title).strip(),
                        "product_url": product_url,
                        "image_url": thumbnail,
                        "price_amount": price_amount,
                        "currency": currency,
                        "seller_count": None,
                        "seller_count_type": None,
                        "source": "serpapi",
                        "retrieved_at": retrieval_time,
                    }
                    candidates.append(candidate_dict)

                return candidates

            except httpx.TimeoutException:
                logger.warning(f"SerpApi request timed out on attempt {attempts}")
                last_exception = ExternalProviderError(
                    provider="serpapi",
                    message=f"SerpApi search request timed out after {self.timeout_seconds}s",
                    status_code=504,
                )
                if attempts <= max_retries:
                    await asyncio.sleep(1.0)
                    continue
                raise last_exception

            except ExternalProviderError:
                raise

            except Exception as e:
                logger.error(f"Unexpected error communicating with SerpApi: {str(e)}", exc_info=True)
                raise ExternalProviderError(
                    provider="serpapi",
                    message=f"Unexpected error connecting to SerpApi: {str(e)}",
                    status_code=502,
                )

        if last_exception:
            raise last_exception
        return []
