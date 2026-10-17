from typing import Optional
from app.config import get_settings
from app.integrations.gemini_client import GeminiClient
from app.schemas.product import ImageAnalysis
from app.utils.image_validation import ValidatedImage
from app.utils.logging import logger


class AnalysisService:
    """Coordinates product image visual understanding and attribute extraction."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.settings = get_settings()
        self.gemini_client = gemini_client or GeminiClient()

    async def analyze_product_image(
        self,
        validated_image: ValidatedImage,
    ) -> ImageAnalysis:
        """
        Analyze validated product photograph to produce structured attributes and search queries.
        """
        logger.info(
            f"Starting image analysis: format={validated_image.format}, "
            f"resolution={validated_image.width}x{validated_image.height}, "
            f"mime={validated_image.mime_type}"
        )

        analysis = await self.gemini_client.analyze_image(
            image_bytes=validated_image.data,
            mime_type=validated_image.mime_type,
        )

        logger.info(
            f"Image analysis completed successfully: category='{analysis.product_category}', "
            f"brand='{analysis.brand}', model='{analysis.model}', color='{analysis.color}', "
            f"queries_count={len(analysis.search_queries)}"
        )

        return analysis
