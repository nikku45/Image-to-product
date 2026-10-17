from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ImageAnalysis(BaseModel):
    product_category: str = Field(..., description="Inferred or visible product category")
    brand: Optional[str] = Field(default=None, description="Identified brand name or null if unknown")
    model: Optional[str] = Field(default=None, description="Identified model name/number or null")
    color: Optional[str] = Field(default=None, description="Primary product color")
    visible_text: List[str] = Field(default_factory=list, description="Visible text extracted from packaging/item")
    identifying_attributes: List[str] = Field(
        default_factory=list, description="Distinct physical identifying features"
    )
    uncertainties: List[str] = Field(
        default_factory=list, description="Ambiguities or unconfirmed inferences"
    )
    search_queries: List[str] = Field(
        default_factory=list, description="Focused search queries (max 3)"
    )


class ProductCandidate(BaseModel):
    asin: str = Field(..., description="Amazon Standard Identification Number")
    title: str = Field(..., description="Product title on Amazon.in")
    product_url: str = Field(..., description="Direct link to listing on Amazon.in")
    image_url: Optional[str] = Field(default=None, description="Thumbnail image URL")
    price_amount: Optional[float] = Field(default=None, description="Current price in INR or null if unavailable")
    currency: Optional[str] = Field(default="INR", description="Currency symbol/code")
    seller_count: Optional[int] = Field(
        default=None, description="Number of distinct sellers or null if unavailable"
    )
    seller_count_type: Optional[str] = Field(
        default=None, description="Type of seller/offer metric or null"
    )
    match_score: float = Field(..., ge=0.0, le=1.0, description="Explainable attribute match score")
    match_confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Provisional confidence classification"
    )
    match_signals: Optional[Dict[str, Any]] = Field(
        default=None, description="Breakdown of matching signals for transparency"
    )
    source: str = Field(default="serpapi", description="Source provider of data")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of data retrieval",
    )


class ProductMatchResponse(BaseModel):
    search_id: str = Field(..., description="Internal UUID for this search lookup")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="Lookup processing status"
    )
    analysis: Optional[ImageAnalysis] = Field(
        default=None, description="Extracted product attributes"
    )
    candidates: List[ProductCandidate] = Field(
        default_factory=list, description="All ranked Amazon.in candidates"
    )
    total_candidates: int = Field(
        default=0, description="Total number of unique product listings discovered"
    )
    total_sellers: int = Field(
        default=0,
        description="Estimated number of distinct sellers — derived from unique ASIN listings",
    )
    selected_asin: Optional[str] = Field(
        default=None, description="ASIN confirmed by the seller"
    )
    error_code: Optional[str] = Field(default=None, description="Error code if lookup failed")
    error_message: Optional[str] = Field(default=None, description="Sanitized error description")


class ConfirmCandidateRequest(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10, description="Valid 10-character Amazon ASIN")


class ConfirmCandidateResponse(BaseModel):
    success: bool = True
    confirmed_asin: str
