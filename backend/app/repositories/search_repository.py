from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.search import (
    ImageAnalysisModel,
    MatchFeedbackModel,
    ProductCandidateModel,
    SearchModel,
)
from app.schemas.product import (
    ImageAnalysis,
    ProductCandidate,
    ProductMatchResponse,
)
from app.utils.logging import logger
from app.utils.marketplace_metrics import compute_listing_metrics


class SearchRepository:
    """Repository abstraction for persisting and retrieving product search lookups."""

    def __init__(self, db: Session):
        self.db = db

    def save_search(
        self,
        search_id: str,
        status: str,
        analysis: Optional[ImageAnalysis],
        candidates: List[ProductCandidate],
        selected_asin: Optional[str] = None,
    ) -> ProductMatchResponse:
        """Persist a search lookup, extracted analysis, and ranked candidates."""
        search = self.db.query(SearchModel).filter(SearchModel.id == search_id).first()
        if not search:
            search = SearchModel(id=search_id, status=status, selected_asin=selected_asin)
            self.db.add(search)
        else:
            search.status = status
            if selected_asin:
                search.selected_asin = selected_asin

        # Save analysis if provided and not yet created
        if analysis:
            existing_analysis = (
                self.db.query(ImageAnalysisModel)
                .filter(ImageAnalysisModel.search_id == search_id)
                .first()
            )
            if not existing_analysis:
                analysis_record = ImageAnalysisModel(
                    search_id=search_id,
                    product_category=analysis.product_category,
                    brand=analysis.brand,
                    model=analysis.model,
                    color=analysis.color,
                    visible_text=analysis.visible_text,
                    identifying_attributes=analysis.identifying_attributes,
                    uncertainties=analysis.uncertainties,
                    search_queries=analysis.search_queries,
                )
                self.db.add(analysis_record)

        # Save candidates (deduplicated by ASIN for this search)
        seen_asins = set()
        for cand in candidates:
            if cand.asin in seen_asins:
                continue
            seen_asins.add(cand.asin)

            existing_cand = (
                self.db.query(ProductCandidateModel)
                .filter(
                    ProductCandidateModel.search_id == search_id,
                    ProductCandidateModel.asin == cand.asin,
                )
                .first()
            )
            if not existing_cand:
                cand_record = ProductCandidateModel(
                    search_id=search_id,
                    asin=cand.asin,
                    title=cand.title,
                    product_url=cand.product_url,
                    image_url=cand.image_url,
                    price_amount=cand.price_amount,
                    currency=cand.currency or "INR",
                    seller_count=cand.seller_count,
                    seller_count_type=cand.seller_count_type,
                    match_score=cand.match_score,
                    match_confidence=cand.match_confidence,
                    match_signals=cand.match_signals,
                    source=cand.source,
                    retrieved_at=cand.retrieved_at,
                )
                self.db.add(cand_record)

        try:
            self.db.commit()
            self.db.refresh(search)
        except IntegrityError as exc:
            self.db.rollback()
            logger.warning(f"Integrity conflict saving search {search_id}: {str(exc)}")
            search = self.db.query(SearchModel).filter(SearchModel.id == search_id).first()

        return self._to_response(search)

    def get_by_id(self, search_id: str) -> Optional[ProductMatchResponse]:
        """Retrieve a search record by ID with analysis and ranked candidates."""
        search = self.db.query(SearchModel).filter(SearchModel.id == search_id).first()
        if not search:
            return None
        return self._to_response(search)

    def list_searches(self, limit: int = 20, offset: int = 0) -> List[ProductMatchResponse]:
        """Retrieve paginated search history ordered by creation time descending."""
        records = (
            self.db.query(SearchModel)
            .order_by(SearchModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self._to_response(r) for r in records]

    def confirm_candidate(
        self,
        search_id: str,
        asin: str,
        is_correct: Optional[bool] = None,
    ) -> bool:
        """Record seller confirmation feedback and update selected ASIN."""
        search = self.db.query(SearchModel).filter(SearchModel.id == search_id).first()
        if not search:
            return False

        search.selected_asin = asin

        feedback = MatchFeedbackModel(
            search_id=search_id,
            selected_asin=asin,
            is_correct=is_correct,
        )
        self.db.add(feedback)
        self.db.commit()
        return True

    def _to_response(self, search: SearchModel) -> ProductMatchResponse:
        """Convert a database SearchModel into a domain ProductMatchResponse."""
        analysis_dto: Optional[ImageAnalysis] = None
        if search.analysis:
            analysis_dto = ImageAnalysis(
                product_category=search.analysis.product_category,
                brand=search.analysis.brand,
                model=search.analysis.model,
                color=search.analysis.color,
                visible_text=search.analysis.visible_text or [],
                identifying_attributes=search.analysis.identifying_attributes or [],
                uncertainties=search.analysis.uncertainties or [],
                search_queries=search.analysis.search_queries or [],
            )

        candidates_dto: List[ProductCandidate] = []
        for c in search.candidates:
            candidates_dto.append(
                ProductCandidate(
                    asin=c.asin,
                    title=c.title,
                    product_url=c.product_url,
                    image_url=c.image_url,
                    price_amount=c.price_amount,
                    currency=c.currency,
                    seller_count=c.seller_count,
                    seller_count_type=c.seller_count_type,
                    match_score=c.match_score,
                    match_confidence=c.match_confidence,
                    match_signals=c.match_signals,
                    source=c.source,
                    retrieved_at=c.retrieved_at,
                )
            )

        total_candidates, total_sellers = compute_listing_metrics(candidates_dto)

        return ProductMatchResponse(
            search_id=search.id,
            status=search.status,  # type: ignore
            analysis=analysis_dto,
            candidates=candidates_dto,
            total_candidates=total_candidates,
            total_sellers=total_sellers,
            selected_asin=search.selected_asin,
        )
