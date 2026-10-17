from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.exceptions import AppError, EntityNotFoundError, ImageValidationError
from app.repositories.search_repository import SearchRepository
from app.schemas.product import (
    ConfirmCandidateRequest,
    ConfirmCandidateResponse,
    ImageAnalysis,
    ProductCandidate,
    ProductMatchResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.image_service import ImageService
from app.services.matching_service import MatchingService
from app.services.search_service import SearchService
from app.utils.logging import logger
from app.utils.marketplace_metrics import compute_listing_metrics

router = APIRouter(prefix="/product-matches", tags=["Product Matches"])
image_service = ImageService()
analysis_service = AnalysisService()
search_service = SearchService()
matching_service = MatchingService()  # Return ALL discovered candidates — no truncation


@router.post(
    "",
    response_model=ProductMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload image and initiate product matching",
)
async def create_product_match(
    image: UploadFile = File(..., description="Product photograph (JPEG, PNG, WebP)"),
    db: Session = Depends(get_db),
) -> ProductMatchResponse:
    """
    Accept an uploaded product image, validate signature, sanitize EXIF,
    perform Gemini analysis, discover matching Amazon.in candidates via SerpApi,
    score candidates, and persist search record to database.
    """
    if not image.filename:
        raise ImageValidationError("Uploaded file has no filename")

    content_type = image.content_type or ""
    logger.info(f"Received upload request: filename='{image.filename}', content_type='{content_type}'")

    try:
        file_bytes = await image.read()
    except Exception as e:
        raise ImageValidationError(f"Could not read upload data: {str(e)}")

    # Execute Pillow content verification, EXIF stripping, and normalization
    search_id, validated = await image_service.process_uploaded_image(
        file_bytes=file_bytes,
        filename=image.filename,
    )

    # Perform Gemini visual attribute extraction
    try:
        analysis = await analysis_service.analyze_product_image(validated)
    except Exception as exc:
        logger.error(f"Analysis failed for search_id={search_id}: {str(exc)}")
        raise

    # Discover Amazon.in candidates via SerpApi
    settings = get_settings()
    candidates: List[ProductCandidate] = []
    if settings.has_serpapi_credentials and analysis.search_queries:
        try:
            candidates = await search_service.discover_candidates(analysis.search_queries)
        except Exception as exc:
            logger.error(f"Search discovery failed for search_id={search_id}: {str(exc)}")
            raise

    # Phase 5: Rank candidates using explainable weighted attribute scoring
    if candidates:
        candidates = matching_service.rank_candidates(analysis, candidates)

    total_candidates, total_sellers = compute_listing_metrics(candidates)

    # Phase 8: Persist search, extracted attributes, and ranked candidates to SQLite
    repo = SearchRepository(db)
    persisted = repo.save_search(
        search_id=search_id,
        status="completed",
        analysis=analysis,
        candidates=candidates,
    )

    # Enrich the response with marketplace competition metrics
    persisted.total_candidates = total_candidates
    persisted.total_sellers = total_sellers

    return persisted


@router.get(
    "",
    response_model=List[ProductMatchResponse],
    summary="Retrieve paginated product match search history",
)
async def list_product_matches(
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
) -> List[ProductMatchResponse]:
    """Retrieve search history records ordered by creation date descending."""
    repo = SearchRepository(db)
    return repo.list_searches(limit=limit, offset=offset)


@router.get(
    "/{search_id}",
    response_model=ProductMatchResponse,
    summary="Retrieve product match results by search ID",
)
async def get_product_match(
    search_id: str,
    db: Session = Depends(get_db),
) -> ProductMatchResponse:
    """Retrieve persisted search results, candidate rankings, and status."""
    repo = SearchRepository(db)
    record = repo.get_by_id(search_id)
    if not record:
        raise EntityNotFoundError(entity_name="Search", entity_id=search_id)
    return record


@router.post(
    "/{search_id}/confirm",
    response_model=ConfirmCandidateResponse,
    summary="Confirm matching ASIN for a search",
)
async def confirm_candidate(
    search_id: str,
    payload: ConfirmCandidateRequest,
    db: Session = Depends(get_db),
) -> ConfirmCandidateResponse:
    """Record the seller's confirmation for the matching product ASIN in database."""
    repo = SearchRepository(db)
    success = repo.confirm_candidate(search_id=search_id, asin=payload.asin)
    if not success:
        raise EntityNotFoundError(entity_name="Search", entity_id=search_id)

    logger.info(f"Confirmed ASIN '{payload.asin}' for search_id={search_id}")
    return ConfirmCandidateResponse(success=True, confirmed_asin=payload.asin)
