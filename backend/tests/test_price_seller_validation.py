"""
Unit tests for Phase 6: Price and Seller-Count Validation.
Validates price parsing, currency handling, null handling for missing prices,
and null seller counts per ADR-004.
"""

from typing import Any, Dict
import pytest

from app.integrations.serpapi_client import _extract_currency, _extract_price_amount
from app.schemas.product import ProductCandidate


def test_extract_price_amount_from_extracted_price():
    """Verify numeric extracted_price formats."""
    assert _extract_price_amount({"extracted_price": 19990.0}) == 19990.0
    assert _extract_price_amount({"extracted_price": 2499}) == 2499.0
    assert _extract_price_amount({"extracted_price": "1499.50"}) == 1499.50
    assert _extract_price_amount({"extracted_price": 0.0}) == 0.0
    assert _extract_price_amount({"extracted_price": -50.0}) is None


def test_extract_price_amount_from_direct_numeric_price():
    """Verify numeric values inside 'price' key directly."""
    assert _extract_price_amount({"price": 4999.0}) == 4999.0
    assert _extract_price_amount({"price": 350}) == 350.0


def test_extract_price_amount_from_formatted_strings():
    """Verify parsing Indian Rupee strings with commas, symbols, and decimals."""
    assert _extract_price_amount({"price": "₹19,990.00"}) == 19990.00
    assert _extract_price_amount({"price": "₹1,24,999"}) == 124999.0
    assert _extract_price_amount({"price": "Rs. 4,500"}) == 4500.0
    assert _extract_price_amount({"price": "INR 2,499.99"}) == 2499.99
    assert _extract_price_amount({"price": "₹1,499 - ₹2,199"}) == 1499.0
    assert _extract_price_amount({"price": "From ₹999"}) == 999.0


def test_extract_price_amount_from_prices_array():
    """Verify parsing when SerpApi includes a 'prices' array of objects."""
    item = {
        "prices": [
            {"value": 18499.0, "currency": "₹"},
            {"value": 19990.0, "currency": "₹"},
        ]
    }
    assert _extract_price_amount(item) == 18499.0

    item_extracted = {
        "prices": [
            {"extracted_value": 799.0}
        ]
    }
    assert _extract_price_amount(item_extracted) == 799.0


def test_extract_price_amount_missing_or_corrupt_returns_none():
    """Verify missing, corrupt, or non-numeric price data resolves strictly to None."""
    assert _extract_price_amount({}) is None
    assert _extract_price_amount({"price": None}) is None
    assert _extract_price_amount({"price": ""}) is None
    assert _extract_price_amount({"price": "Currently unavailable"}) is None
    assert _extract_price_amount({"price": "Out of stock"}) is None
    assert _extract_price_amount({"extracted_price": "not-a-number"}) is None
    assert _extract_price_amount({"prices": []}) is None


def test_extract_currency_handling():
    """Verify explicit currency extraction and fallback handling."""
    # Explicit currency field in item
    assert _extract_currency({"currency": "INR"}) == "INR"
    assert _extract_currency({"currency": "USD"}) == "USD"

    # Inferred from price string
    assert _extract_currency({"price": "₹1,499"}) == "INR"
    assert _extract_currency({"price": "Rs. 2,999"}) == "INR"
    assert _extract_currency({"price": "$49.99"}) == "USD"
    assert _extract_currency({"price": "€89.00"}) == "EUR"
    assert _extract_currency({"price": "£12.50"}) == "GBP"

    # Default fallback for Amazon.in
    assert _extract_currency({}, default="INR") == "INR"
    assert _extract_currency({"price": "1499"}, default="INR") == "INR"


def test_product_candidate_schema_null_handling():
    """Verify ProductCandidate accepts None for price_amount and seller_count."""
    candidate = ProductCandidate(
        asin="B08N5WRWNW",
        title="Sony WH-1000XM4 Wireless Headphones",
        product_url="https://www.amazon.in/dp/B08N5WRWNW",
        price_amount=None,
        currency="INR",
        seller_count=None,
        seller_count_type=None,
        match_score=0.95,
        match_confidence="high",
        source="serpapi",
    )
    assert candidate.price_amount is None
    assert candidate.seller_count is None
    assert candidate.seller_count_type is None
    assert candidate.currency == "INR"
    assert candidate.retrieved_at is not None
