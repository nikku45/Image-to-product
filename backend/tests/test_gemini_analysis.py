import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest
from google.api_core.exceptions import GoogleAPIError

from app.config import Settings
from app.exceptions import ExternalProviderError
from app.integrations.gemini_client import GeminiClient
from app.schemas.product import ImageAnalysis
from app.services.analysis_service import AnalysisService
from app.utils.image_validation import ValidatedImage


@pytest.fixture
def mock_validated_image() -> ValidatedImage:
    return ValidatedImage(
        data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        format="JPEG",
        mime_type="image/jpeg",
        width=400,
        height=400,
        original_filename="sample_product.jpg",
    )


def _make_gemini_client(api_key="test-api-key"):
    """Create a GeminiClient with a mocked genai.Client so no real API call is made."""
    with patch("app.integrations.gemini_client.genai.Client") as MockClientCls:
        mock_client_instance = MagicMock()
        MockClientCls.return_value = mock_client_instance
        client = GeminiClient(api_key=api_key)
    return client, mock_client_instance


@pytest.mark.asyncio
async def test_gemini_client_unconfigured_error():
    """Verify GeminiClient raises 503 ExternalProviderError when api_key is None."""
    client = GeminiClient(api_key=None)
    client._is_configured = False

    with pytest.raises(ExternalProviderError) as exc_info:
        await client.analyze_image(image_bytes=b"dummy", mime_type="image/jpeg")

    assert exc_info.value.status_code == 503
    assert "GEMINI_API_KEY is not configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_gemini_client_successful_parsing():
    """Verify GeminiClient parses valid structured JSON correctly into ImageAnalysis."""
    client, mock_genai_client = _make_gemini_client()

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = json.dumps({
        "product_category": "wireless headphones",
        "brand": "AudioTech",
        "model": "AT-500",
        "color": "matte black",
        "visible_text": ["AudioTech", "AT-500", "ANC"],
        "identifying_attributes": ["over-ear design", "foldable headband", "type-c port"],
        "uncertainties": ["battery capacity not printed"],
        "search_queries": [
            "AudioTech AT-500 wireless headphones",
            "AudioTech AT-500 matte black ANC",
            "AudioTech over ear headphones",
            "Ignored fourth query",
        ],
    })
    mock_gemini_response.usage_metadata = MagicMock(prompt_token_count=120, candidates_token_count=85)

    # Mock the async generate_content call on client.aio.models
    mock_aio = MagicMock()
    mock_aio.models.generate_content = AsyncMock(return_value=mock_gemini_response)
    type(mock_genai_client).aio = PropertyMock(return_value=mock_aio)

    result = await client.analyze_image(image_bytes=b"dummy-bytes", mime_type="image/jpeg")

    assert isinstance(result, ImageAnalysis)
    assert result.product_category == "wireless headphones"
    assert result.brand == "AudioTech"
    assert result.model == "AT-500"
    assert result.color == "matte black"
    assert "ANC" in result.visible_text
    assert len(result.identifying_attributes) == 3
    # Query bounding rule: max 3 queries
    assert len(result.search_queries) == 3
    assert "AudioTech AT-500 wireless headphones" in result.search_queries
    assert "Ignored fourth query" not in result.search_queries


@pytest.mark.asyncio
async def test_gemini_client_cleans_null_strings_and_empty_lists():
    """Verify literal 'null', 'unknown', or empty strings are converted to None."""
    client, mock_genai_client = _make_gemini_client()

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = json.dumps({
        "product_category": "running shoes",
        "brand": "null",
        "model": "unknown",
        "color": "",
        "visible_text": None,
        "identifying_attributes": ["thick foam sole"],
        "uncertainties": [],
        "search_queries": [],
    })
    mock_gemini_response.usage_metadata = None

    mock_aio = MagicMock()
    mock_aio.models.generate_content = AsyncMock(return_value=mock_gemini_response)
    type(mock_genai_client).aio = PropertyMock(return_value=mock_aio)

    result = await client.analyze_image(image_bytes=b"dummy", mime_type="image/jpeg")

    assert result.brand is None
    assert result.model is None
    assert result.color is None
    assert result.visible_text == []
    assert result.identifying_attributes == ["thick foam sole"]
    # Fallback query automatically created if queries were empty
    assert len(result.search_queries) == 1
    assert result.search_queries[0] == "running shoes"


@pytest.mark.asyncio
async def test_gemini_client_malformed_json_retry_and_failure():
    """Verify GeminiClient retries once on malformed JSON and raises 502 ExternalProviderError if it fails."""
    client, mock_genai_client = _make_gemini_client()

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "This is not JSON at all: { broken json ... "
    mock_gemini_response.usage_metadata = None

    mock_aio = MagicMock()
    mock_generate = AsyncMock(return_value=mock_gemini_response)
    mock_aio.models.generate_content = mock_generate
    type(mock_genai_client).aio = PropertyMock(return_value=mock_aio)

    with pytest.raises(ExternalProviderError) as exc_info:
        await client.analyze_image(image_bytes=b"dummy", mime_type="image/jpeg", max_retries=1)

    assert exc_info.value.status_code == 502
    assert "could not be parsed as valid JSON" in exc_info.value.message
    # Verify 2 attempts were made (initial + 1 retry)
    assert mock_generate.call_count == 2


@pytest.mark.asyncio
async def test_gemini_client_timeout_handling():
    """Verify timeout triggers ExternalProviderError with status 504."""
    client, mock_genai_client = _make_gemini_client()

    async def slow_call(*args, **kwargs):
        await asyncio.sleep(0.1)

    mock_aio = MagicMock()
    mock_aio.models.generate_content = slow_call
    type(mock_genai_client).aio = PropertyMock(return_value=mock_aio)

    client.timeout_seconds = 0.01

    with pytest.raises(ExternalProviderError) as exc_info:
        await client.analyze_image(image_bytes=b"dummy", mime_type="image/jpeg", max_retries=0)

    assert exc_info.value.status_code == 504
    assert "timed out" in exc_info.value.message


@pytest.mark.asyncio
async def test_gemini_client_google_api_error():
    """Verify GoogleAPIError is translated to ExternalProviderError."""
    client, mock_genai_client = _make_gemini_client()

    mock_aio = MagicMock()
    mock_aio.models.generate_content = AsyncMock(
        side_effect=GoogleAPIError("Quota exceeded: Resource has been exhausted")
    )
    type(mock_genai_client).aio = PropertyMock(return_value=mock_aio)

    with pytest.raises(ExternalProviderError) as exc_info:
        await client.analyze_image(image_bytes=b"dummy", mime_type="image/jpeg", max_retries=0)

    assert exc_info.value.status_code == 502
    assert "Gemini API call failed" in exc_info.value.message


@pytest.mark.asyncio
async def test_analysis_service_orchestration(mock_validated_image):
    """Verify AnalysisService calls GeminiClient and returns the structured ImageAnalysis."""
    mock_client = MagicMock(spec=GeminiClient)
    expected_analysis = ImageAnalysis(
        product_category="Smartwatch",
        brand="PulseBand",
        model="FitPro 3",
        color="Black",
        visible_text=["PulseBand", "FitPro"],
        identifying_attributes=["OLED screen", "Silicone strap"],
        uncertainties=[],
        search_queries=["PulseBand FitPro 3", "PulseBand Smartwatch"],
    )
    mock_client.analyze_image = AsyncMock(return_value=expected_analysis)

    service = AnalysisService(gemini_client=mock_client)
    result = await service.analyze_product_image(mock_validated_image)

    assert result == expected_analysis
    mock_client.analyze_image.assert_awaited_once_with(
        image_bytes=mock_validated_image.data,
        mime_type=mock_validated_image.mime_type,
    )
