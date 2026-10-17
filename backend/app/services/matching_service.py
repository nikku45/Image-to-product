"""
Candidate Ranking & Normalization Service (Phase 5).

Implements explainable weighted attribute matching between Gemini-extracted
product attributes and SerpApi search candidate titles/metadata.

Scoring Weights (ADR-005, provisional):
    Brand:              25%
    Model:              30%
    Category:           15%
    Variant attributes: 20%
    Other descriptive:  10%

Confidence Thresholds:
    high:   score >= 0.85 with no critical contradiction
    medium: 0.60 <= score < 0.85
    low:    score < 0.60

Design Principles:
    - Missing attributes are treated as unknown (neutral), never mismatches.
    - Verified contradictions apply penalty multipliers.
    - Scores are ranking heuristics, not calibrated probabilities.
    - Candidate order is deterministic for identical inputs.
"""

import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from app.schemas.product import ImageAnalysis, ProductCandidate
from app.utils.logging import logger


# ---------------------------------------------------------------------------
# Scoring weight configuration (ADR-005)
# ---------------------------------------------------------------------------
WEIGHT_BRAND: float = 0.25
WEIGHT_MODEL: float = 0.30
WEIGHT_CATEGORY: float = 0.15
WEIGHT_VARIANT: float = 0.20
WEIGHT_OTHER: float = 0.10

# Contradiction penalty applied when a verified attribute conflict is detected
CONTRADICTION_PENALTY: float = 0.40

# Confidence classification thresholds
CONFIDENCE_HIGH_THRESHOLD: float = 0.85
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.60


# ---------------------------------------------------------------------------
# Text normalization helpers
# ---------------------------------------------------------------------------

_NOISE_WORDS = frozenset({
    "the", "a", "an", "for", "with", "and", "or", "in", "on", "of",
    "by", "to", "from", "is", "new", "latest", "best", "original",
})

_NON_ALNUM = re.compile(r"[^a-z0-9\s]")


def _normalize_text(text: Optional[str]) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    if not text:
        return ""
    cleaned = _NON_ALNUM.sub(" ", text.lower())
    return " ".join(cleaned.split())


def _tokenize(text: str) -> List[str]:
    """Split normalized text into meaningful tokens (removing noise words)."""
    return [t for t in text.split() if t and t not in _NOISE_WORDS]


def _token_overlap_score(reference_tokens: List[str], candidate_tokens: List[str]) -> float:
    """
    Compute directional token overlap: what fraction of reference tokens appear in the candidate.
    Returns 0.0 when reference is empty (treated as unknown/neutral).
    """
    if not reference_tokens:
        return 0.0  # Unknown attribute → neutral (caller handles)
    if not candidate_tokens:
        return 0.0  # Candidate has no tokens → no evidence of match

    ref_set = set(reference_tokens)
    cand_set = set(candidate_tokens)
    overlap = ref_set & cand_set
    return len(overlap) / len(ref_set)


def _exact_match(reference: Optional[str], candidate_text: str) -> Optional[bool]:
    """
    Check if the normalized reference string appears as a substring in the candidate text.
    Returns None if reference is unknown (missing/empty).
    """
    norm_ref = _normalize_text(reference)
    if not norm_ref:
        return None  # Unknown → no comparison possible
    norm_cand = _normalize_text(candidate_text)
    return norm_ref in norm_cand


# ---------------------------------------------------------------------------
# Individual attribute scorers
# ---------------------------------------------------------------------------

def _score_brand(
    brand: Optional[str],
    candidate_title: str,
) -> Tuple[float, Dict[str, Any]]:
    """
    Score brand attribute match.
    Returns (component_score, signal_dict).
    """
    signal: Dict[str, Any] = {"attribute": "brand", "reference": brand, "weight": WEIGHT_BRAND}

    if not brand:
        signal["status"] = "unknown"
        signal["contribution"] = 0.0
        return 0.0, signal

    match_result = _exact_match(brand, candidate_title)
    if match_result is True:
        contribution = WEIGHT_BRAND * 1.0
        signal["status"] = "match"
        signal["contribution"] = contribution
        return contribution, signal
    else:
        # Brand is known but not found → mild penalty (could be abbreviated or missing from title)
        # Use token overlap for partial credit
        ref_tokens = _tokenize(_normalize_text(brand))
        cand_tokens = _tokenize(_normalize_text(candidate_title))
        overlap = _token_overlap_score(ref_tokens, cand_tokens)
        if overlap > 0:
            contribution = WEIGHT_BRAND * overlap * 0.7  # Partial match discount
            signal["status"] = "partial"
            signal["overlap"] = overlap
            signal["contribution"] = contribution
            return contribution, signal
        else:
            signal["status"] = "mismatch"
            signal["contribution"] = 0.0
            return 0.0, signal


def _score_model(
    model: Optional[str],
    candidate_title: str,
) -> Tuple[float, Dict[str, Any]]:
    """
    Score model/SKU attribute match.
    Model mismatches are the strongest contradiction signal.
    Returns (component_score, signal_dict).
    """
    signal: Dict[str, Any] = {"attribute": "model", "reference": model, "weight": WEIGHT_MODEL}

    if not model:
        signal["status"] = "unknown"
        signal["contribution"] = 0.0
        return 0.0, signal

    match_result = _exact_match(model, candidate_title)
    if match_result is True:
        contribution = WEIGHT_MODEL * 1.0
        signal["status"] = "match"
        signal["contribution"] = contribution
        return contribution, signal
    else:
        # Token overlap for partial model matches (e.g., "Galaxy S24" vs "Galaxy S24 Ultra")
        ref_tokens = _tokenize(_normalize_text(model))
        cand_tokens = _tokenize(_normalize_text(candidate_title))
        overlap = _token_overlap_score(ref_tokens, cand_tokens)
        if overlap >= 0.5:
            contribution = WEIGHT_MODEL * overlap * 0.6  # Partial model match with discount
            signal["status"] = "partial"
            signal["overlap"] = overlap
            signal["contribution"] = contribution
            return contribution, signal
        else:
            # Clear model mismatch → contradiction
            signal["status"] = "contradiction"
            signal["contribution"] = 0.0
            signal["is_contradiction"] = True
            return 0.0, signal


def _score_category(
    category: Optional[str],
    candidate_title: str,
) -> Tuple[float, Dict[str, Any]]:
    """
    Score product category match.
    Returns (component_score, signal_dict).
    """
    signal: Dict[str, Any] = {"attribute": "category", "reference": category, "weight": WEIGHT_CATEGORY}

    if not category:
        signal["status"] = "unknown"
        signal["contribution"] = 0.0
        return 0.0, signal

    ref_tokens = _tokenize(_normalize_text(category))
    cand_tokens = _tokenize(_normalize_text(candidate_title))
    overlap = _token_overlap_score(ref_tokens, cand_tokens)

    if overlap >= 0.5:
        contribution = WEIGHT_CATEGORY * min(overlap * 1.2, 1.0)  # Slightly generous for broad categories
        signal["status"] = "match" if overlap >= 0.8 else "partial"
        signal["overlap"] = overlap
        signal["contribution"] = contribution
        return contribution, signal
    else:
        signal["status"] = "mismatch"
        signal["overlap"] = overlap
        signal["contribution"] = 0.0
        return 0.0, signal


def _score_variant_attributes(
    analysis: ImageAnalysis,
    candidate_title: str,
) -> Tuple[float, Dict[str, Any]]:
    """
    Score variant attributes (color, size, pack quantity, visible text features).
    Individual variant sub-attributes are scored and averaged.
    Returns (component_score, signal_dict).
    """
    signal: Dict[str, Any] = {"attribute": "variant", "weight": WEIGHT_VARIANT, "sub_signals": []}
    sub_scores: List[float] = []

    # Color matching
    if analysis.color:
        color_match = _exact_match(analysis.color, candidate_title)
        color_signal = {"sub_attribute": "color", "reference": analysis.color}
        if color_match is True:
            sub_scores.append(1.0)
            color_signal["status"] = "match"
        else:
            sub_scores.append(0.0)
            color_signal["status"] = "mismatch"
        signal["sub_signals"].append(color_signal)

    # Identifying attributes matching (e.g., "128GB", "6.7 inch", etc.)
    for attr in analysis.identifying_attributes:
        attr_match = _exact_match(attr, candidate_title)
        attr_signal = {"sub_attribute": "identifying", "reference": attr}
        if attr_match is True:
            sub_scores.append(1.0)
            attr_signal["status"] = "match"
        elif attr_match is False:
            sub_scores.append(0.2)  # Partial credit — attribute not visible doesn't mean wrong product
            attr_signal["status"] = "not_found"
        signal["sub_signals"].append(attr_signal)

    if not sub_scores:
        signal["status"] = "unknown"
        signal["contribution"] = 0.0
        return 0.0, signal

    avg_variant_score = sum(sub_scores) / len(sub_scores)
    contribution = WEIGHT_VARIANT * avg_variant_score
    signal["status"] = "evaluated"
    signal["avg_sub_score"] = round(avg_variant_score, 4)
    signal["contribution"] = contribution
    return contribution, signal


def _score_other_descriptive(
    analysis: ImageAnalysis,
    candidate_title: str,
) -> Tuple[float, Dict[str, Any]]:
    """
    Score other descriptive attributes (visible text from packaging/labels).
    Returns (component_score, signal_dict).
    """
    signal: Dict[str, Any] = {"attribute": "other_descriptive", "weight": WEIGHT_OTHER}

    if not analysis.visible_text:
        signal["status"] = "unknown"
        signal["contribution"] = 0.0
        return 0.0, signal

    matches = 0
    total = 0
    for text_fragment in analysis.visible_text:
        norm_fragment = _normalize_text(text_fragment)
        if len(norm_fragment) < 2:
            continue  # Skip trivially short fragments
        total += 1
        if norm_fragment in _normalize_text(candidate_title):
            matches += 1

    if total == 0:
        signal["status"] = "unknown"
        signal["contribution"] = 0.0
        return 0.0, signal

    match_ratio = matches / total
    contribution = WEIGHT_OTHER * match_ratio
    signal["status"] = "evaluated"
    signal["matched_fragments"] = matches
    signal["total_fragments"] = total
    signal["match_ratio"] = round(match_ratio, 4)
    signal["contribution"] = contribution
    return contribution, signal


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def score_candidate(
    analysis: ImageAnalysis,
    candidate: ProductCandidate,
) -> Tuple[float, Literal["high", "medium", "low"], Dict[str, Any]]:
    """
    Compute the composite match score for a single candidate against the extracted analysis.

    Returns:
        (score, confidence, match_signals)

    Score range: [0.0, 1.0]
    Deterministic for identical inputs.
    """
    candidate_title = candidate.title

    # Score each attribute dimension
    brand_score, brand_signal = _score_brand(analysis.brand, candidate_title)
    model_score, model_signal = _score_model(analysis.model, candidate_title)
    category_score, category_signal = _score_category(analysis.product_category, candidate_title)
    variant_score, variant_signal = _score_variant_attributes(analysis, candidate_title)
    other_score, other_signal = _score_other_descriptive(analysis, candidate_title)

    all_signals = [brand_signal, model_signal, category_signal, variant_signal, other_signal]

    # Raw composite score (sum of weighted contributions)
    raw_score = brand_score + model_score + category_score + variant_score + other_score

    # Normalize: compute the maximum achievable score given known attributes
    # Unknown attributes don't contribute to the denominator
    max_possible = 0.0
    if analysis.brand:
        max_possible += WEIGHT_BRAND
    if analysis.model:
        max_possible += WEIGHT_MODEL
    if analysis.product_category:
        max_possible += WEIGHT_CATEGORY
    has_variant = bool(analysis.color or analysis.identifying_attributes)
    if has_variant:
        max_possible += WEIGHT_VARIANT
    if analysis.visible_text:
        max_possible += WEIGHT_OTHER

    # If no attributes are known at all, fall back to base score
    if max_possible == 0.0:
        normalized_score = 0.5  # Neutral — no information to compare
    else:
        normalized_score = raw_score / max_possible

    # Check for critical contradictions (model or brand contradiction)
    has_critical_contradiction = any(
        s.get("is_contradiction", False) for s in all_signals
    )

    # Apply contradiction penalty
    if has_critical_contradiction:
        normalized_score = max(0.0, normalized_score - CONTRADICTION_PENALTY)

    # Clamp to [0.0, 1.0]
    final_score = round(min(max(normalized_score, 0.0), 1.0), 4)

    # Determine confidence level
    if final_score >= CONFIDENCE_HIGH_THRESHOLD and not has_critical_contradiction:
        confidence: Literal["high", "medium", "low"] = "high"
    elif final_score >= CONFIDENCE_MEDIUM_THRESHOLD:
        confidence = "medium"
    else:
        confidence = "low"

    match_signals: Dict[str, Any] = {
        "raw_score": round(raw_score, 4),
        "max_possible": round(max_possible, 4),
        "normalized_score": round(normalized_score, 4),
        "has_critical_contradiction": has_critical_contradiction,
        "contradiction_penalty_applied": has_critical_contradiction,
        "final_score": final_score,
        "confidence": confidence,
        "attribute_signals": all_signals,
    }

    return final_score, confidence, match_signals


# ---------------------------------------------------------------------------
# MatchingService class
# ---------------------------------------------------------------------------

class MatchingService:
    """
    Coordinates candidate ranking and normalization.

    Accepts a list of ProductCandidate objects and an ImageAnalysis,
    scores each candidate, and returns the top candidates sorted by score.
    """

    def __init__(self, max_results: int | None = None):
        self.max_results = max_results

    def rank_candidates(
        self,
        analysis: ImageAnalysis,
        candidates: List[ProductCandidate],
    ) -> List[ProductCandidate]:
        """
        Score, rank, and return the top candidates.

        Steps:
            1. Deduplicate candidates by ASIN (preserve first occurrence).
            2. Score each candidate using explainable weighted attribute matching.
            3. Sort by score descending (deterministic tiebreak by ASIN).
            4. Return the top N candidates with updated scores and signals.
        """
        if not candidates:
            logger.info("No candidates to rank; returning empty list")
            return []

        # Step 1: Deduplicate by ASIN
        seen_asins = set()
        unique_candidates: List[ProductCandidate] = []
        for c in candidates:
            if c.asin not in seen_asins:
                seen_asins.add(c.asin)
                unique_candidates.append(c)

        logger.info(
            f"Ranking {len(unique_candidates)} unique candidates "
            f"(from {len(candidates)} total) against analysis: "
            f"brand='{analysis.brand}', model='{analysis.model}', "
            f"category='{analysis.product_category}'"
        )

        # Step 2: Score each candidate
        scored: List[Tuple[float, str, ProductCandidate]] = []
        for candidate in unique_candidates:
            final_score, confidence, match_signals = score_candidate(analysis, candidate)

            # Update candidate with calibrated score and explainable signals
            candidate.match_score = final_score
            candidate.match_confidence = confidence
            candidate.match_signals = match_signals

            # Tuple for deterministic sorting: (negative score for descending, ASIN for tiebreak)
            scored.append((-final_score, candidate.asin, candidate))

        # Step 3: Deterministic sort (descending score, ascending ASIN for ties)
        scored.sort(key=lambda t: (t[0], t[1]))

        # Step 4: Return all candidates (or top N if max_results is set)
        all_ranked = [item[2] for item in scored]
        ranked = all_ranked[:self.max_results] if self.max_results else all_ranked

        logger.info(
            f"Ranking complete: returning top {len(ranked)} candidates. "
            f"Score range: {ranked[-1].match_score:.4f} – {ranked[0].match_score:.4f}"
            if ranked else "No candidates ranked"
        )
        for i, c in enumerate(ranked):
            logger.debug(
                f"  Rank {i + 1}: ASIN={c.asin}, score={c.match_score:.4f}, "
                f"confidence={c.match_confidence}, title='{c.title[:60]}...'"
            )

        return ranked
