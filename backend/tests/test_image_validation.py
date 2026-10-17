import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from PIL import Image
from app.exceptions import ImageValidationError
from app.schemas.product import ImageAnalysis
from app.utils.image_validation import (
    validate_and_preprocess_image,
    verify_image_signature,
)


def create_test_image(format: str = "JPEG", size=(100, 100), color=(255, 0, 0)) -> bytes:
    """Helper to generate in-memory valid image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_verify_image_signature_jpeg():
    data = create_test_image(format="JPEG")
    fmt = verify_image_signature(data[:16])
    assert fmt == "JPEG"


def test_verify_image_signature_png():
    data = create_test_image(format="PNG")
    fmt = verify_image_signature(data[:16])
    assert fmt == "PNG"


def test_verify_image_signature_webp():
    data = create_test_image(format="WEBP")
    fmt = verify_image_signature(data[:16])
    assert fmt == "WEBP"


def test_reject_spoofed_file_extension():
    """A text file renamed to .jpg should fail signature check."""
    fake_data = b"This is not a real image file, just plain text."
    with pytest.raises(ImageValidationError) as exc:
        verify_image_signature(fake_data)
    assert "Unsupported image format" in str(exc.value)


def test_reject_empty_image():
    with pytest.raises(ImageValidationError) as exc:
        validate_and_preprocess_image(b"")
    assert "empty" in str(exc.value)


def test_reject_oversized_image():
    data = create_test_image(format="JPEG")
    # Set max size smaller than data length
    with pytest.raises(ImageValidationError) as exc:
        validate_and_preprocess_image(data, max_size_bytes=10)
    assert "exceeds the maximum" in str(exc.value)


def test_valid_image_preprocessing():
    data = create_test_image(format="JPEG", size=(300, 200))
    result = validate_and_preprocess_image(data, original_filename="test.jpg")
    assert result.format == "JPEG"
    assert result.mime_type == "image/jpeg"
    assert result.width == 300
    assert result.height == 200
    assert len(result.data) > 0


@pytest.mark.asyncio
async def test_upload_valid_image_endpoint(client: AsyncClient):
    """Test POST /api/product-matches accepts a valid image."""
    img_bytes = create_test_image(format="PNG", size=(150, 150))
    files = {"image": ("sample.png", img_bytes, "image/png")}

    mock_analysis = ImageAnalysis(
        product_category="Electronics",
        brand="TestBrand",
        model="Model1",
        color="red",
        visible_text=["SampleText"],
        identifying_attributes=["Square shape"],
        uncertainties=[],
        search_queries=["TestBrand Model1 Electronics"],
    )

    with patch("app.api.products.analysis_service.analyze_product_image", new=AsyncMock(return_value=mock_analysis)), \
         patch("app.api.products.search_service.discover_candidates", new=AsyncMock(return_value=[])):
        response = await client.post("/api/product-matches", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "search_id" in data
        assert data["status"] in ["pending", "completed"]
        assert "analysis" in data
        assert data["analysis"]["brand"] == "TestBrand"
        assert len(data["search_id"]) > 0

        # Retrieve by search_id
        search_id = data["search_id"]
        get_res = await client.get(f"/api/product-matches/{search_id}")
        assert get_res.status_code == 200
        assert get_res.json()["search_id"] == search_id


@pytest.mark.asyncio
async def test_upload_corrupt_file_endpoint(client: AsyncClient):
    """Test POST /api/product-matches returns 400 for corrupt image bytes."""
    corrupt_bytes = b"\xff\xd8\xff\xe0" + b"randomcorruptgarbage" * 10
    files = {"image": ("bad.jpg", corrupt_bytes, "image/jpeg")}

    response = await client.post("/api/product-matches", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "IMAGE_VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_confirm_candidate_endpoint(client: AsyncClient):
    """Test POST /api/product-matches/{search_id}/confirm updates candidate selection."""
    img_bytes = create_test_image(format="JPEG")
    files = {"image": ("item.jpg", img_bytes, "image/jpeg")}

    mock_analysis = ImageAnalysis(
        product_category="Footwear",
        brand="SneakerBrand",
        model="AirX",
        color="white",
        visible_text=[],
        identifying_attributes=[],
        uncertainties=[],
        search_queries=["SneakerBrand AirX"],
    )

    with patch("app.api.products.analysis_service.analyze_product_image", new=AsyncMock(return_value=mock_analysis)), \
         patch("app.api.products.search_service.discover_candidates", new=AsyncMock(return_value=[])):
        upload_res = await client.post("/api/product-matches", files=files)
        search_id = upload_res.json()["search_id"]

        confirm_res = await client.post(
            f"/api/product-matches/{search_id}/confirm",
            json={"asin": "B08N5WRWNW"},
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["success"] is True
        assert confirm_res.json()["confirmed_asin"] == "B08N5WRWNW"
