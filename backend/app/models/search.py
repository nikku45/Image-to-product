from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SearchModel(Base):
    __tablename__ = "searches"

    id = Column(String(64), primary_key=True, index=True)
    status = Column(String(32), nullable=False, default="completed")
    selected_asin = Column(String(16), nullable=True, index=True)
    created_at = Column(String(64), nullable=False, default=_utc_now_iso)
    updated_at = Column(String(64), nullable=False, default=_utc_now_iso, onupdate=_utc_now_iso)

    # Relationships
    analysis = relationship(
        "ImageAnalysisModel",
        back_populates="search",
        uselist=False,
        cascade="all, delete-orphan",
    )
    candidates = relationship(
        "ProductCandidateModel",
        back_populates="search",
        cascade="all, delete-orphan",
        order_by="desc(ProductCandidateModel.match_score)",
    )
    feedbacks = relationship(
        "MatchFeedbackModel",
        back_populates="search",
        cascade="all, delete-orphan",
    )


class ImageAnalysisModel(Base):
    __tablename__ = "image_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(
        String(64),
        ForeignKey("searches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    product_category = Column(String(128), nullable=False)
    brand = Column(String(128), nullable=True)
    model = Column(String(128), nullable=True)
    color = Column(String(64), nullable=True)
    visible_text = Column(JSON, nullable=False, default=list)
    identifying_attributes = Column(JSON, nullable=False, default=list)
    uncertainties = Column(JSON, nullable=False, default=list)
    search_queries = Column(JSON, nullable=False, default=list)
    created_at = Column(String(64), nullable=False, default=_utc_now_iso)

    search = relationship("SearchModel", back_populates="analysis")


class ProductCandidateModel(Base):
    __tablename__ = "product_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(
        String(64),
        ForeignKey("searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asin = Column(String(16), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    product_url = Column(String(512), nullable=False)
    image_url = Column(String(512), nullable=True)
    price_amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False, default="INR")
    seller_count = Column(Integer, nullable=True)
    seller_count_type = Column(String(32), nullable=True)
    match_score = Column(Float, nullable=False)
    match_confidence = Column(String(16), nullable=False)
    match_signals = Column(JSON, nullable=True)
    source = Column(String(32), nullable=False, default="serpapi")
    retrieved_at = Column(String(64), nullable=False, default=_utc_now_iso)

    __table_args__ = (
        UniqueConstraint("search_id", "asin", name="uq_search_candidate_asin"),
    )

    search = relationship("SearchModel", back_populates="candidates")


class MatchFeedbackModel(Base):
    __tablename__ = "match_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(
        String(64),
        ForeignKey("searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_asin = Column(String(16), nullable=False)
    is_correct = Column(Boolean, nullable=True)
    created_at = Column(String(64), nullable=False, default=_utc_now_iso)

    search = relationship("SearchModel", back_populates="feedbacks")
