import uuid
from typing import Tuple
from app.config import get_settings
from app.utils.image_validation import ValidatedImage, validate_and_preprocess_image
from app.utils.logging import logger


class ImageService:
    """Handles image upload validation, normalization, and temporary processing buffers."""

    def __init__(self):
        self.settings = get_settings()

    async def process_uploaded_image(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> Tuple[str, ValidatedImage]:
        """
        Validates the incoming bytes, applies orientation and EXIF sanitization,
        and generates an internal search UUID.
        """
        search_id = str(uuid.uuid4())
        logger.info(
            f"Processing image upload for search_id={search_id}, filename='{filename}', size={len(file_bytes)} bytes"
        )

        validated_image = validate_and_preprocess_image(
            file_bytes=file_bytes,
            original_filename=filename,
            max_size_bytes=self.settings.max_upload_size_bytes,
        )

        logger.info(
            f"Image validated successfully: search_id={search_id}, format={validated_image.format}, "
            f"dims={validated_image.width}x{validated_image.height}, sanitized_size={len(validated_image.data)} bytes"
        )

        return search_id, validated_image
