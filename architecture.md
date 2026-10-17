Technical Architecture — Image-to-Amazon.in Product Matching Platform

Document type: Technical Architecture Specification
Version: 1.0
Status: Initial prototype
Primary implementation agent: Google Antigravity
Target marketplace: Amazon.in
Architecture style: Modular monolith with asynchronous processing where needed

1. Project Overview

Build a web application that allows a seller to upload a product photograph and discover matching products on Amazon.in.

The application uses Gemini API to understand the uploaded image, generates text-based search queries, and uses SerpApi's Amazon Search API to retrieve candidate listings.

The system returns:

Amazon.in product URL.
Product title and ASIN.
Current listed price, when available.
Number of sellers or offers, when reliably available.
Match confidence and the reason for the match.
Timestamp indicating when marketplace data was retrieved.

The first release is a working prototype, not a full enterprise marketplace intelligence platform.

1.1 Primary user flow
A seller opens the web application.
The seller uploads a product image.
The backend validates and stores the image temporarily.
Gemini analyzes the image and returns structured product attributes.
The backend generates and validates search queries.
SerpApi searches Amazon.in using those queries.
The backend normalizes and deduplicates candidate listings.
The application ranks candidates using available product attributes.
The seller sees the top three candidates and confirms the correct product.
The application displays available price and seller/offer information.
1.2 Initial scope

Included:

Single-image upload.
Image understanding through Gemini.
Text-based Amazon.in product discovery through SerpApi.
Candidate ranking and manual confirmation.
Product URL, title, ASIN, price, and seller/offer data where available.
Search history for the prototype.
Basic error handling, logging, and API usage controls.

Excluded from the first release:

Google Lens or reverse-image search.
Automated web scraping of Amazon pages outside permitted provider interfaces.
Custom model training.
A dedicated vector database.
Multiple marketplace integrations.
Price history and notifications.
Multi-tenant enterprise administration.
Payment processing and subscriptions.
Microservices and Kubernetes.

Do not implement excluded features unless explicitly requested.

2. Non-Negotiable Engineering Principles
Keep the implementation simple enough for one developer to understand and operate.
Use official SDKs or documented HTTP APIs where practical.
Never invent API fields or assume a response contains seller counts.
Keep Gemini and SerpApi behind separate service interfaces.
Keep API keys on the backend. Never expose them to the browser.
Validate every external API response before using it.
Do not represent missing information as zero.
Do not label a search result an exact match without sufficient evidence.
Store timestamps with marketplace data.
Add tests for core business logic before expanding features.
Use environment variables for secrets and deployment configuration.
Prefer free or free-tier infrastructure, but document usage limits and possible future costs.
Follow the applicable Gemini, SerpApi, and marketplace terms.
Do not bypass CAPTCHAs, access controls, or provider restrictions.
3. Technology Stack
3.1 Frontend
Next.js with App Router.
React.
TypeScript with strict mode.
Tailwind CSS for styling.
A lightweight, accessible component system.
Native browser image preview and upload.

Responsibilities:

Accept image uploads.
Show upload progress and analysis status.
Display extracted product attributes.
Show ranked Amazon candidates.
Let the seller select or reject a candidate.
Display product details, price, seller count, and data timestamps.
Show useful errors and retry options.

The frontend must never call Gemini or SerpApi directly.

3.2 Backend
Python 3.12 or a currently supported compatible Python release.
FastAPI.
Pydantic for request and response validation.
HTTPX for external HTTP calls where needed.
Pillow for image validation and preprocessing.
pytest for testing.

Use a supported Gemini SDK version or documented API integration. Pin dependency versions and record the selected Gemini model in configuration.

3.3 Data storage

Initial storage:

SQLite for local development and a small single-instance prototype.
Local temporary image storage for development.
PostgreSQL and managed object storage when a deployed multi-user environment requires them.

Use a repository abstraction for persistence so the application can migrate from SQLite to PostgreSQL without rewriting the matching logic.

Do not store uploaded images permanently unless required by a documented product feature.

3.4 External services

Gemini API

Responsibilities:

Image understanding.
Extraction of visible text and product attributes.
Generation of a small set of search queries.
Structured JSON output.

SerpApi Amazon Search API

Responsibilities:

Execute text-based Amazon.in searches.
Retrieve candidate product listings.
Return available listing metadata.
Supply candidate ASINs, titles, URLs, images, and prices where the documented response provides them.

Use the official SerpApi documentation and verify the current endpoint, country/domain parameters, supported filters, and response schema.

Documentation:

Gemini API: https://ai.google.dev/gemini-api/docs
SerpApi Amazon Search: https://serpapi.com/amazon-search-api

Do not introduce Google Lens in this release.

4. High-Level Architecture
                  SELLER
                    |
                    v
        +-------------------------+
        | Next.js Web Application |
        | Upload / Results / UI   |
        +------------+------------+
                     |
                     v
        +-------------------------+
        | FastAPI Backend         |
        | Validation / Orchestration
        +------------+------------+
                     |
          +----------+-----------+
          |                      |
          v                      v
 +----------------+     +------------------+
 | Image Service  |     | Search Service   |
 | Validate image |     | Build queries    |
 | Normalize      |     | Call SerpApi     |
 +-------+--------+     +---------+--------+
         |                        |
         v                        v
 +----------------+     +------------------+
 | Gemini Adapter |     | SerpApi Adapter  |
 +-------+--------+     +---------+--------+
         |                        |
         v                        v
 +----------------+     +------------------+
 | Product        |     | Candidate        |
 | Attributes     |     | Listings         |
 +----------------+     +---------+--------+
                                   |
                                   v
                         +------------------+
                         | Ranking Engine   |
                         | Deduplicate      |
                         | Score candidates |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         | Result Service   |
                         | Persistence      |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         | Seller Results UI|
                         +------------------+


For the initial prototype, this can run as one FastAPI application. Do not deploy separate microservices.

If model calls or search operations make requests too slow, introduce a background worker and job queue in a later phase.

5. Suggested Repository Structure
product-matcher/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── TECHNICAL_ARCHITECTURE.md
│   └── IMPLEMENTATION_PLAN.md
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── history/
│   │   ├── components/
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── AnalysisStatus.tsx
│   │   │   ├── ProductCard.tsx
│   │   │   └── ResultsList.tsx
│   │   ├── lib/
│   │   │   └── api.ts
│   │   └── types/
│   │       └── product.ts
│   └── tests/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   └── products.py
│   │   ├── schemas/
│   │   │   ├── image.py
│   │   │   ├── analysis.py
│   │   │   └── product.py
│   │   ├── services/
│   │   │   ├── image_service.py
│   │   │   ├── analysis_service.py
│   │   │   ├── search_service.py
│   │   │   ├── matching_service.py
│   │   │   └── result_service.py
│   │   ├── integrations/
│   │   │   ├── gemini_client.py
│   │   │   └── serpapi_client.py
│   │   ├── repositories/
│   │   │   └── search_repository.py
│   │   ├── models/
│   │   │   └── search.py
│   │   └── utils/
│   │       ├── image_validation.py
│   │       └── scoring.py
│   └── tests/
├── data/
│   └── .gitkeep
└── scripts/
    └── smoke_test.py


This is a target structure, not a requirement to create every file before the first feature. Add files incrementally as their responsibilities become necessary.

Never commit .env, API keys, uploaded private images, local database files, or generated secrets.

6. Image Analysis Pipeline
6.1 Image validation

Before calling Gemini:

Accept JPEG, PNG, and WebP.
Verify actual file contents, not only the filename extension.
Set a configurable upload-size limit, initially 10 MB.
Reject empty, corrupt, or unsupported files.
Apply image dimension limits to prevent resource exhaustion.
Normalize orientation.
Strip unnecessary EXIF metadata.
Resize oversized images while preserving useful product details.
Use temporary storage and clean up files after processing.

The 10 MB value is an initial engineering default and may be adjusted after testing.

6.2 Gemini input and output

Send the validated image to Gemini with an instruction to identify visible attributes without guessing.

The output must follow a validated schema similar to:

{
  "product_category": "wireless headphones",
  "brand": "ExampleBrand",
  "model": "X200",
  "color": "black",
  "visible_text": ["X200"],
  "identifying_attributes": [
    "over-ear design",
    "foldable headband"
  ],
  "uncertainties": [],
  "search_queries": [
    "ExampleBrand X200 wireless headphones",
    "ExampleBrand X200 black headphones"
  ]
}


The values above are examples only.

Use null for unknown brand, model, or color. Do not treat a model-generated guess as verified information.

6.3 Prompt requirements

The Gemini prompt must instruct the model to:

Describe only attributes supported by visible evidence.
Distinguish visible text from inferred attributes.
Avoid inventing a brand or model.
Identify variant-sensitive attributes.
Generate no more than three focused search queries.
Return valid structured output matching the agreed schema.

If the response is malformed, validate and retry once when appropriate. If it remains invalid, return a controlled error instead of passing arbitrary text to the search layer.

7. Amazon Product Discovery
7.1 Search strategy

For each upload:

Receive the structured Gemini analysis.
Generate up to three distinct queries.
Call SerpApi's Amazon Search endpoint for the Indian marketplace.
Request a small number of relevant results per query.
Normalize the response into an internal candidate schema.
Deduplicate by ASIN.
Rank candidates and return the best three.

Do not send multiple nearly identical queries simply to increase result counts.

Make the number of searches configurable. For the first implementation, use one primary query and allow a second query only if the initial results are insufficient. Add a third only when justified by testing.

7.2 Internal candidate schema

Normalize provider results into a stable structure:

{
  "asin": "EXAMPLE123",
  "title": "Example product title",
  "product_url": "https://www.amazon.in/dp/EXAMPLE123",
  "image_url": null,
  "price_amount": null,
  "currency": "INR",
  "seller_count": null,
  "seller_count_type": null,
  "source": "serpapi",
  "retrieved_at": "2026-10-15T12:00:00Z"
}


This is an internal schema example. Do not hardcode the example ASIN or assume all fields are present.

Only construct a canonical Amazon product URL when a valid ASIN has been verified. Otherwise, use the validated provider URL.

7.3 Seller count and price

Seller count is a required product goal but is not guaranteed by the search endpoint.

Before implementation:

Read the current SerpApi Amazon Search documentation.
Inspect representative real responses.
Identify whether price is present and how it is represented.
Determine whether any seller-count field exists.
Distinguish total offers from unique sellers and Buy Box competitors.
Record source and timestamp for every retrieved metric.

If seller count is absent, store null and show "Unavailable." Never infer seller count from the number of search results.

Do not make undocumented calls or scrape Amazon product pages as a hidden fallback.

If the selected endpoint does not expose the required metric, document the limitation and propose a separately approved data-source integration.

8. Candidate Ranking

The initial version should use explainable attribute-based scoring rather than a complex model.

Suggested initial weights:

Signal	Weight
Brand match	25%
Model or model-number match	30%
Product category match	15%
Variant attributes	20%
Other descriptive attributes	10%

These weights are starting hypotheses and must be calibrated using a labelled evaluation dataset.

Rules:

A verified model-number conflict should substantially reduce the score.
A known size, color, or pack-count mismatch should reduce the score.
Missing attributes should not automatically count as a mismatch.
Brand conflicts should lower confidence.
Scores must not be described as statistically calibrated probabilities.

Initial decision thresholds:

Score >= 0.85: eligible for a high-confidence suggestion, subject to contradiction checks.
Score 0.60–0.84: show as a possible match requiring seller confirmation.
Score < 0.60: show low-confidence candidates or request a clearer image.

These thresholds are provisional and must be evaluated against the test dataset.

The first release should allow manual selection even when a result scores highly.

9. API Contracts
9.1 Health check

GET /api/health

Response:

{
  "status": "ok"
}


The endpoint should verify application health. Dependency health checks may be added separately.

9.2 Create product match

POST /api/product-matches

Content type: multipart/form-data

Fields:

image: required product image.

Expected response:

{
  "search_id": "generated-uuid",
  "status": "completed",
  "analysis": {
    "product_category": "wireless headphones",
    "brand": "ExampleBrand",
    "model": "X200"
  },
  "candidates": [
    {
      "asin": "EXAMPLE123",
      "title": "Example product title",
      "product_url": "https://www.amazon.in/dp/EXAMPLE123",
      "price_amount": null,
      "currency": "INR",
      "seller_count": null,
      "seller_count_type": null,
      "match_score": 0.87,
      "match_confidence": "high",
      "retrieved_at": "2026-10-15T12:00:00Z"
    }
  ]
}


This is an example of the application's response contract. Production code must populate values from validated API responses and internal scoring. It must not return fabricated data.

If processing is synchronous for the MVP, return the result directly when completed. If processing later moves to a background worker, return 202 Accepted with a search_id and provide a status endpoint.

9.3 Retrieve search result

GET /api/product-matches/{search_id}

Return the stored analysis, candidate list, processing status, and error information where applicable.

9.4 Confirm a candidate

POST /api/product-matches/{search_id}/confirm

Body:

{
  "asin": "EXAMPLE123"
}


Validate that the ASIN belongs to the search's candidate set.

Store the confirmation for future evaluation.

9.5 Search history

GET /api/product-matches

Return paginated search history. Apply user scoping and authorization when authentication is introduced.

10. Data Model

Create the following logical entities.

Search
id: UUID primary key.
user_id: nullable until authentication is implemented.
status: pending, processing, completed, failed.
created_at.
completed_at.
error_code: nullable.
error_message: nullable, sanitized.
ImageAnalysis
id.
search_id: foreign key.
product_category.
brand: nullable.
model: nullable.
color: nullable.
visible_text: JSON.
attributes: JSON.
search_queries: JSON.
model_name.
created_at.
ProductCandidate
id.
search_id: foreign key.
asin.
title.
product_url.
image_url: nullable.
price_amount: nullable decimal.
currency: nullable until verified.
seller_count: nullable integer.
seller_count_type: nullable.
match_score.
match_confidence.
source.
retrieved_at.

Add a unique constraint on (search_id, asin).

MatchFeedback
id.
search_id.
selected_asin.
is_correct: nullable if not independently verified.
created_at.

Use migrations from the beginning. Never store currency amounts as floating-point values.

11. Configuration and Secrets

Create .env.example:

APP_ENV=development
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

GEMINI_API_KEY=
GEMINI_MODEL=

SERPAPI_API_KEY=

DATABASE_URL=sqlite:///./data/app.db

MAX_UPLOAD_SIZE_MB=10
MAX_SEARCH_QUERIES=2
MAX_CANDIDATES_PER_QUERY=10


Use current supported Gemini model identifiers and document the chosen model.

The MAX_CANDIDATES_PER_QUERY value is a configurable cap, not a guarantee that SerpApi will return that many results.

Additional requirements:

Fail clearly if required credentials are missing.
Never log API keys or full authorization headers.
Keep .env out of version control.
Use separate development and production credentials.
Set provider timeouts and bounded retries.
Respect provider quotas and rate limits.
12. Error Handling and Resilience

Handle the following cases explicitly:

Invalid or corrupt image.
Image too large.
Gemini timeout.
Gemini rate limit or quota exhaustion.
Malformed Gemini response.
SerpApi timeout.
SerpApi quota exhaustion.
No search results.
Invalid or missing ASIN.
Missing price.
Missing seller count.
Database failure.
Duplicate candidate results.

Use bounded exponential backoff with jitter for transient failures. Do not repeatedly retry invalid requests or quota failures that cannot recover within the request deadline.

Do not silently substitute fabricated product data when a provider fails.

Return stable application error codes and human-readable messages.

13. Security and Privacy
Validate MIME types and file signatures.
Limit upload sizes and image dimensions.
Generate internal identifiers for uploaded files.
Keep temporary images outside publicly served directories.
Delete temporary files according to a documented retention policy.
Avoid storing unnecessary image metadata.
Never expose provider credentials in frontend bundles.
Restrict CORS to configured frontend origins.
Add rate limits to upload and search endpoints.
Sanitize logs and error messages.
Apply authorization checks to user-specific searches when authentication is enabled.
Verify provider terms and image-data handling requirements before production deployment.
14. Testing and Quality Gates

Required tests:

Unit tests for image validation.
Unit tests for Gemini response validation.
Unit tests for query generation and deduplication.
Unit tests for candidate normalization.
Unit tests for match scoring.
API tests for upload and error responses.
Integration tests with mocked Gemini and SerpApi responses.
Live smoke tests using real credentials, executed explicitly rather than during every unit-test run.
Regression tests using manually labelled product photos.

Create a labelled evaluation dataset of at least 100 images, with the correct ASIN and variant where known.

Measure:

Top-1 exact-match accuracy.
Top-3 exact-match accuracy.
No-match rate.
Variant-confusion rate.
Price availability rate.
Seller-count availability rate.
Average lookup latency.
Estimated cost per lookup.

Do not claim production readiness until these metrics have been measured.

15. Observability

Record structured events for:

Search created.
Image validation completed.
Gemini request completed or failed.
SerpApi request completed or failed.
Candidate count.
Matching completed.
Seller confirmation received.
Total request duration.
Provider latency.
Retry count.

Never include API secrets or unnecessary private image contents in logs.

Track estimated Gemini usage and SerpApi search consumption. This is essential for a free-tier prototype.

16. Definition of Done

The architecture is implemented when:

The application runs locally using documented commands.
A seller can upload a valid image.
Gemini returns validated structured attributes.
SerpApi returns real candidate listings for Amazon.in.
Candidate results are deduplicated and ranked.
The top three candidates can be shown in the UI.
A seller can confirm a candidate.
The application displays the real listing URL and any verified price or seller data.
Missing fields are explicitly shown as unavailable.
Automated tests pass.
Secrets are not committed or exposed to the browser.
Setup instructions and known limitations are documented.

Final implementation rule: Prefer a working, testable vertical slice over a large amount of unfinished scaffolding. Verify external API capabilities before designing dependent features.