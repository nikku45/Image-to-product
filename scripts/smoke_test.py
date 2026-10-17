"""
End-to-End Live Smoke Test Script
Image-to-Amazon.in Product Matching Platform

Usage:
    python scripts/smoke_test.py [--base-url http://127.0.0.1:8000]
"""

import argparse
import io
import sys
import time
from typing import Any, Dict
import httpx
from PIL import Image, ImageDraw


def generate_sample_product_image() -> bytes:
    """Generate an in-memory sample retail packaging photograph for Sony WH-1000XM4."""
    img = Image.new("RGB", (400, 400), color=(245, 245, 245))
    d = ImageDraw.Draw(img)

    # Product packaging box
    d.rectangle([50, 50, 350, 350], fill=(25, 25, 30), outline=(220, 38, 38), width=4)
    # Labeled text on package
    d.text((80, 110), "SONY", fill=(255, 255, 255))
    d.text((80, 150), "WH-1000XM4", fill=(255, 255, 255))
    d.text((80, 190), "Wireless Noise Cancelling", fill=(200, 200, 200))
    d.text((80, 225), "30hr Battery / Mic / LDAC", fill=(160, 160, 160))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def run_smoke_test(base_url: str = "http://127.0.0.1:8000") -> bool:
    print("=" * 70, flush=True)
    print("IMAGE-TO-AMAZON.IN MATCHING PLATFORM — LIVE SMOKE TEST", flush=True)
    print(f"Target Base URL: {base_url}", flush=True)
    print("=" * 70, flush=True)

    client = httpx.Client(base_url=base_url, timeout=45.0)

    # Step 1: Health Check
    print("\n[1/5] Checking Backend Service Health...")
    try:
        health_resp = client.get("/api/health")
        if health_resp.status_code != 200:
            print(f"FAILED: Health endpoint returned HTTP {health_resp.status_code}")
            return False
        health_data = health_resp.json()
        print(f"  Status: {health_data.get('status')}")
        print(f"  Environment: {health_data.get('environment')}")
        print(f"  Gemini Configured: {health_data.get('gemini_configured')}")
        print(f"  SerpApi Configured: {health_data.get('serpapi_configured')}")
    except Exception as e:
        print(f"FAILED: Could not reach backend at {base_url}: {str(e)}")
        print("  Make sure backend is running: python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
        return False

    # Step 2: Generate Test Image
    print("\n[2/5] Synthesizing Test Product Photograph...")
    img_bytes = generate_sample_product_image()
    print(f"  Generated JPEG buffer: {len(img_bytes)} bytes")

    # Step 3: Execute End-to-End Match Request
    print("\n[3/5] Dispatching POST /api/product-matches (Vision AI + SerpApi Search)...")
    start_time = time.time()
    files = {"image": ("test_headphone_box.jpg", img_bytes, "image/jpeg")}

    try:
        match_resp = client.post("/api/product-matches", files=files)
        
        # If Gemini free-tier RPM limit was hit, wait and retry once
        if match_resp.status_code == 502 and "quota" in match_resp.text.lower():
            print("  Note: Hit Gemini free tier 5 RPM limit. Waiting 8s for quota window before retry...")
            time.sleep(8)
            files = {"image": ("test_headphone_box.jpg", img_bytes, "image/jpeg")}
            match_resp = client.post("/api/product-matches", files=files)

        elapsed = time.time() - start_time

        if match_resp.status_code != 200:
            print(f"FAILED: /api/product-matches returned HTTP {match_resp.status_code}: {match_resp.text}")
            return False

        match_data = match_resp.json()
        search_id = match_data.get("search_id")
        print(f"  Response received in {elapsed:.2f}s")
        print(f"  Search ID: {search_id}")
        print(f"  Lookup Status: {match_data.get('status')}")

        # Validate Extracted Vision Attributes
        analysis = match_data.get("analysis") or {}
        print("\n  Extracted Gemini Vision Attributes:")
        print(f"    - Category: {analysis.get('product_category')}")
        print(f"    - Brand: {analysis.get('brand')}")
        print(f"    - Model: {analysis.get('model')}")
        print(f"    - Visible Text: {analysis.get('visible_text')}")
        print(f"    - Search Queries ({len(analysis.get('search_queries', []))}):")
        for q in analysis.get("search_queries", []):
            print(f"        * '{q}'")

        # Validate Candidates Discovered
        candidates = match_data.get("candidates") or []
        print(f"\n  Amazon.in Candidates Discovered: {len(candidates)}")
        for idx, c in enumerate(candidates[:5]):
            print(f"    [{idx + 1}] ASIN: {c.get('asin')}")
            print(f"        Title: {c.get('title')[:60]}...")
            print(f"        URL: {c.get('product_url')}")
            print(f"        Price: INR {c.get('price_amount')} (Currency: {c.get('currency')})")
            print(f"        Seller Count: {c.get('seller_count') or 'Unavailable (per ADR-004)'}")
            print(f"        Match Score: {c.get('match_score')} ({c.get('match_confidence')})")

        if not candidates:
            print("  WARNING: No candidates were returned. Check SerpApi query or quota.")

    except Exception as e:
        print(f"FAILED: Error calling /api/product-matches: {str(e)}")
        return False

    # Step 4: Retrieve by Search ID
    print("\n[4/5] Verifying GET /api/product-matches/{search_id}...")
    try:
        get_resp = client.get(f"/api/product-matches/{search_id}")
        if get_resp.status_code != 200:
            print(f"FAILED: GET returned HTTP {get_resp.status_code}")
            return False
        assert get_resp.json()["search_id"] == search_id
        print("  Retrieved match result matches search_id successfully.")
    except Exception as e:
        print(f"FAILED: Could not retrieve search by ID: {str(e)}")
        return False

    # Step 5: Confirm a Candidate ASIN
    if candidates:
        first_asin = candidates[0].get("asin")
        print(f"\n[5/5] Testing Candidate Confirmation (POST .../confirm for ASIN {first_asin})...")
        try:
            confirm_resp = client.post(
                f"/api/product-matches/{search_id}/confirm",
                json={"asin": first_asin},
            )
            if confirm_resp.status_code != 200:
                print(f"FAILED: Confirm returned HTTP {confirm_resp.status_code}")
                return False
            confirm_data = confirm_resp.json()
            assert confirm_data.get("success") is True
            assert confirm_data.get("confirmed_asin") == first_asin
            print(f"  Successfully confirmed ASIN: {confirm_data.get('confirmed_asin')}")
        except Exception as e:
            print(f"FAILED: Could not confirm candidate: {str(e)}")
            return False
    else:
        print("\n[5/5] Skipping candidate confirmation (no candidates found to confirm).")

    print("\n" + "=" * 70)
    print("SMOKE TEST STATUS: ALL CHECKS PASSED")
    print("=" * 70)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Smoke Test for Product Matching Platform")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of FastAPI backend")
    args = parser.parse_args()

    success = run_smoke_test(base_url=args.base_url)
    sys.exit(0 if success else 1)
