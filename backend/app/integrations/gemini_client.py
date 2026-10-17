import asyncio
import json
import time
from typing import Any, Dict, Optional
from google import genai
from google.genai import types
from google.api_core.exceptions import GoogleAPIError

from app.config import get_settings
from app.exceptions import ExternalProviderError
from app.schemas.product import ImageAnalysis
from app.utils.logging import logger

GEMINI_ANALYSIS_PROMPT = """You are an expert e-commerce catalog matching specialist.
Analyze this product photograph to extract visible attributes for exact matching against listings on Amazon India (Amazon.in).

You must return a valid JSON object strictly matching this schema:
{
  "product_category": "string (e.g. 'wireless earbuds', 'running shoes', 'instant coffee')",
  "brand": "string or null (ONLY if brand name or logo is clearly visible, otherwise null)",
  "model": "string or null (ONLY if model number/name is visible or explicitly printed, otherwise null)",
  "color": "string or null (primary color of the physical item)",
  "visible_text": ["array of exact strings/words visible on product body or packaging"],
  "identifying_attributes": ["array of distinct physical design features, form factor, or packaging traits"],
  "uncertainties": ["array of attributes that cannot be determined with certainty from this angle/resolution"],
  "search_queries": [
    "string: high-precision primary search query combining brand + model + key feature",
    "string: alternate query (e.g. brand + category + color)",
    "string: variant-focused query"
  ]
}

Strict Rules:
1. NEVER hallucinate or guess brand names or model numbers. If not clearly legible or identifiable, use null.
2. Distinguish visible text verbatim from inferred physical characteristics.
3. Identify variant-sensitive attributes such as pack quantity, volume, storage size, or color.
4. Provide up to 3 focused, distinct search queries optimized for Amazon.in search. Do not provide more than 3 queries.
5. Return ONLY valid JSON.
"""


def _clean_string(value: Any) -> Optional[str]:
    """Clean a nullable string attribute, converting empty or 'null' literals to None."""
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ("null", "none", "unknown", "n/a"):
        return None
    return val_str


def _clean_list(items: Any) -> list:
    """Ensure an attribute is a clean list of strings."""
    if not isinstance(items, list):
        return []
    cleaned = []
    for item in items:
        if item is not None:
            s = str(item).strip()
            if s:
                cleaned.append(s)
    return cleaned


class GeminiClient:
    """Client adapter for Google Gemini multimodal vision inference.

    Uses the new `google.genai` SDK (v2.x) with proper async support via
    `client.aio.models.generate_content()`.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.gemini_timeout_seconds
        )
        self._is_configured = bool(self.api_key and self.api_key.strip())

        if self._is_configured:
            self._client = genai.Client(api_key=self.api_key)
        else:
            self._client = None

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        max_retries: int = 1,
    ) -> ImageAnalysis:
        """
        Send image buffer to Gemini Vision API and parse structured product attributes.
        Implements bounded retries for malformed JSON or transient timeouts per specification 6.3.
        """
        if not self._is_configured or self._client is None:
            raise ExternalProviderError(
                provider="gemini",
                message="GEMINI_API_KEY is not configured in .env. Please provide a valid Gemini API key.",
                status_code=503,
            )

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        attempts = 0
        last_exception: Optional[Exception] = None

        while attempts <= max_retries:
            attempts += 1
            start_time = time.time()
            logger.info(
                f"Dispatching Gemini vision analysis (attempt {attempts}/{max_retries + 1}): "
                f"model='{self.model_name}', mime_type='{mime_type}', size={len(image_bytes)} bytes"
            )

            try:
                # Use the async client for proper coroutine-based async
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self.model_name,
                        contents=[GEMINI_ANALYSIS_PROMPT, image_part],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,  # Low temperature to minimize hallucination
                        ),
                    ),
                    timeout=self.timeout_seconds,
                )

                duration = time.time() - start_time
                logger.info(f"Gemini response received in {duration:.2f}s (attempt {attempts})")

                # Log token usage safely if available
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                    candidates_tokens = getattr(response.usage_metadata, "candidates_token_count", None)
                    logger.info(
                        f"Gemini token usage: prompt_tokens={prompt_tokens}, candidate_tokens={candidates_tokens}"
                    )

                if not response.text:
                    raise ExternalProviderError(
                        provider="gemini",
                        message="Gemini returned an empty response",
                        status_code=502,
                    )

                # Parse and validate JSON
                try:
                    raw_data = json.loads(response.text)
                except json.JSONDecodeError as jde:
                    logger.warning(
                        f"Malformed JSON on attempt {attempts}: {str(jde)}. Raw text snippet: {response.text[:200]}"
                    )
                    if attempts <= max_retries:
                        await asyncio.sleep(0.5)
                        continue
                    raise ExternalProviderError(
                        provider="gemini",
                        message=f"Gemini response could not be parsed as valid JSON: {str(jde)}",
                        status_code=502,
                        details={"raw_text": response.text[:500]},
                    )

                if not isinstance(raw_data, dict):
                    if attempts <= max_retries:
                        await asyncio.sleep(0.5)
                        continue
                    raise ExternalProviderError(
                        provider="gemini",
                        message="Gemini returned JSON that is not an object",
                        status_code=502,
                    )

                # Normalize fields and enforce schema rules
                product_category = _clean_string(raw_data.get("product_category")) or "Unclassified Product"
                brand = _clean_string(raw_data.get("brand"))
                model_attr = _clean_string(raw_data.get("model"))
                color = _clean_string(raw_data.get("color"))
                visible_text = _clean_list(raw_data.get("visible_text"))
                identifying_attributes = _clean_list(raw_data.get("identifying_attributes"))
                uncertainties = _clean_list(raw_data.get("uncertainties"))
                search_queries = _clean_list(raw_data.get("search_queries"))[:3]

                # If no search queries were returned, generate a fallback query
                if not search_queries:
                    parts = [p for p in [brand, model_attr, product_category] if p]
                    search_queries = [" ".join(parts)] if parts else [product_category]

                normalized = {
                    "product_category": product_category,
                    "brand": brand,
                    "model": model_attr,
                    "color": color,
                    "visible_text": visible_text,
                    "identifying_attributes": identifying_attributes,
                    "uncertainties": uncertainties,
                    "search_queries": search_queries[:3],
                }

                return ImageAnalysis.model_validate(normalized)

            except asyncio.TimeoutError:
                last_exception = ExternalProviderError(
                    provider="gemini",
                    message=f"Gemini Vision API request timed out after {self.timeout_seconds}s",
                    status_code=504,
                )
                logger.warning(f"Gemini request timed out on attempt {attempts}")
                if attempts <= max_retries:
                    await asyncio.sleep(0.5)
                    continue
                raise last_exception

            except ExternalProviderError as e:
                last_exception = e
                if attempts <= max_retries and e.status_code >= 500:
                    await asyncio.sleep(0.5)
                    continue
                raise

            except GoogleAPIError as ge:
                logger.error(f"Gemini API error on attempt {attempts}: {str(ge)}")
                last_exception = ExternalProviderError(
                    provider="gemini",
                    message=f"Gemini API call failed: {str(ge)}",
                    status_code=502,
                )
                if attempts <= max_retries:
                    await asyncio.sleep(0.5)
                    continue
                raise last_exception

            except Exception as e:
                logger.error(f"Unexpected error during Gemini analysis: {str(e)}", exc_info=True)
                raise ExternalProviderError(
                    provider="gemini",
                    message=f"Unexpected error communicating with Gemini Vision API: {str(e)}",
                    status_code=502,
                )

        if last_exception:
            raise last_exception
        raise ExternalProviderError(
            provider="gemini",
            message="Gemini analysis failed after retries",
            status_code=502,
        )
