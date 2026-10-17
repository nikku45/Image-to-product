# AGENTS.md — Persistent Project Memory & Engineering Context

> **Note for AI Coding Agents and Human Developers**: This file is the primary living project context and operational memory for the Image-to-Amazon.in Product Matching Platform. Always read this file and the authoritative specifications before making changes. Keep this document updated after completing every meaningful task or phase.

---

## A. Project Overview

### Purpose
The **Image-to-Amazon.in Product Matching Platform** allows online marketplace sellers to upload a product photograph and discover the corresponding matching product listings on **Amazon.in**.

### Target Users
Marketplace sellers, catalog managers, and e-commerce operators seeking to match physical inventory or photos against existing Amazon.in ASINs for competitive pricing, catalog creation, and listing intelligence.

### Problem Statement
Identifying the exact Amazon.in listing from a raw product photo is labor-intensive, error-prone, and susceptible to variant confusion (color, size, pack count, model revision). Sellers require an automated pipeline that extracts visual attributes, searches Amazon.in, ranks candidates transparently, and displays verifiable marketplace data (ASIN, title, URL, price, seller count).

### End-to-End User Workflow
1. **Upload**: A seller uploads a single product photograph (JPEG, PNG, or WebP) via a responsive web interface.
2. **Validation & Preprocessing**: The backend verifies file signature, decodes image bytes, validates dimensions and file size (default <= 10MB), strips non-essential EXIF, and normalizes orientation.
3. **Gemini Vision Analysis**: Google Gemini API analyzes the image, extracting structured product attributes (brand, model, category, variant features, visible text) without hallucinating, and generates up to 3 focused search queries.
4. **Amazon.in Search Discovery**: The backend queries SerpApi Amazon Search API (`engine=amazon`, `amazon_domain=amazon.in`) using the generated search queries (starting with the primary query, with bounded fallbacks).
5. **Candidate Normalization & Deduplication**: Results are parsed into a normalized internal candidate schema and deduplicated by ASIN.
6. **Transparent Attribute Ranking**: Candidates are scored using explainable weighted attribute matching (brand, model, category, variant attributes) with penalties for verified conflicts.
7. **Seller Review & Confirmation**: The top 3 candidates are presented in the UI with match scores, confidence levels, and explainable signals. The seller confirms the matching listing or rejects candidates.
8. **Marketplace Metrics Display**: The confirmed listing's verified Amazon.in URL, current listed price, seller/offer count (or explicit "Unavailable"), and data retrieval timestamp are displayed.
9. **Persistence**: Search inputs, extracted attributes, candidate rankings, and seller feedback are stored for search history and pipeline calibration.

---

## B. Authoritative Documentation

The authoritative specifications governing this system are located in the repository root:
1. [architecture.md](file:///c:/Users/aniru/OneDrive/Desktop/test/architecture.md) — Technical Architecture Specification (version 1.0): Defines the intended system design, component responsibilities, API contracts, scoring models, and security principles.
2. [implementationPlan.md](file:///c:/Users/aniru/OneDrive/Desktop/test/implementationPlan.md) — Implementation Plan (version 1.0): Defines the phase-by-phase execution sequence, deliverables, acceptance criteria, and quality gates.

*Note on file paths*: In project instructions these may be referenced as `docs/TECHNICAL_ARCHITECTURE.md` and `docs/IMPLEMENTATION_PLAN.md`. In this repository, `architecture.md` and `implementationPlan.md` at root are the authoritative originals. Do not create duplicate copies.

### Consistency Rule
If implementation realities or provider API updates require a departure from either specification, document the rationale in this file (`AGENTS.md`), update [docs/IMPLEMENTATION_STATUS.md](file:///c:/Users/aniru/OneDrive/Desktop/test/docs/IMPLEMENTATION_STATUS.md), and synchronize the authoritative docs. **Never silently allow code and documentation to contradict each other.**

---

## C. Technology Stack

### Layer Breakdown & Responsibilities

| Layer | Technology | Version / Tooling | Status | Responsibility |
|---|---|---|---|---|
| **Frontend** | Next.js (App Router), React, TypeScript (strict), Tailwind CSS | Next.js 14+, React 18/19, Node v24.13.0 | Planned (Phase 1) | Image upload UI, status indicators, candidate cards, seller confirmation, history view |
| **Backend** | Python, FastAPI, Pydantic v2, Uvicorn | Python 3.13.3, FastAPI 0.115+, Pydantic 2.11+ | Planned (Phase 1) | REST API, validation, orchestration, ranking, session management |
| **Image Processing** | Pillow (PIL) | Pillow 11.2+ | Planned (Phase 2) | MIME/signature verification, orientation normalization, dimension limits, EXIF sanitization |
| **Vision AI** | Google Gemini API | `gemini-1.5-flash` (or `gemini-2.0-flash`) via `google-generativeai` | Planned (Phase 3) | Multimodal visual attribute extraction & structured search query generation |
| **Marketplace Search** | SerpApi Amazon Search API | `engine=amazon`, `amazon_domain=amazon.in`, HTTPX 0.28+ | Planned (Phase 4) | Query Amazon India search results, parse organic listings, retrieve ASIN, title, price |
| **Candidate Ranking** | Pure Python ranking engine | In-memory deterministic scoring | Planned (Phase 5) | Attribute-weighted matching, contradiction penalties, confidence categorization |
| **Database** | SQLite (local) / PostgreSQL (deployed) | SQLAlchemy 2, psycopg 3 | Implemented (Phase 8) | Persist searches, extracted attributes, candidate listings, seller feedback |
| **Testing** | pytest, pytest-asyncio, Jest / Playwright | pytest (Backend) | Planned (Phase 1) | Unit tests, mocked API integration tests, schema validation, live smoke tests |
| **Deployment** | Render free web service / Vercel Hobby | Render Blueprint (`render.yaml`), Vercel Git integration (`frontend/vercel.json`) | Configuration added (Phase 10) | Deploy services and verify using externally provided PostgreSQL URL |

---

## D. Architecture and Data Flow

```
[Seller Client (Next.js)]
         | (1) POST /api/product-matches (multipart image)
         v
[FastAPI Backend: API Router]
         | (2) Byte validation & EXIF normalization
         v
[Image Service (Pillow)]
         | (3) Clean image buffer
         v
[Gemini Adapter (google-generativeai)] -> Calls Gemini API (gemini-1.5-flash)
         | (4) Structured JSON: brand, model, category, variant, queries
         v
[Search Service]
         | (5) Query dispatch with Amazon.in domain
         v
[SerpApi Adapter (HTTPX)] -> Calls SerpApi (`engine=amazon`, `amazon_domain=amazon.in`)
         | (6) Raw organic search results
         v
[Candidate Normalization & Deduplication] -> Normalized Candidate Schema
         | (7) Candidates + Gemini attributes
         v
[Candidate Ranking Engine] -> Weighted scoring (brand 25%, model 30%, category 15%, variant 20%, other 10%)
         | (8) Ranked candidates with confidence & match signals
         v
[Result Service & Repository] -> Persists Search, Analysis, Candidates through SQLAlchemy
         | (9) JSON Response (search_id, status, analysis, top 3 candidates)
         v
[Seller Client (Next.js)]
         | (10) User selects candidate -> POST /api/product-matches/{id}/confirm
         v
[Feedback Persistence]
```

### Component Boundaries
- **Frontend**: Restricted strictly to presentation and user interaction. **Never** calls Gemini or SerpApi directly; contains no API keys or secrets.
- **Backend API Layer**: Handles routing, multipart parsing, request validation, and error wrapping.
- **Integration Adapters**: `gemini_client.py` and `serpapi_client.py` strictly isolate external vendor SDKs and HTTP contracts. All vendor-specific errors are translated into domain-level exceptions.
- **Domain / Services**: Pure business logic (matching algorithms, query planning, candidate normalization) is independent of external network protocols.
- **Persistence Layer**: Repository abstraction decouples domain models from storage. SQLite remains the local default; PostgreSQL is supported through `DATABASE_URL` for deployment.

---

## E. Engineering Rules

All AI coding agents and human contributors must adhere to these non-negotiable rules:
1. **Inspect Before Modifying**: Always check existing code, directory structure, and Git status before generating or modifying files.
2. **Follow the Phase Order**: Execute phases sequentially per [implementationPlan.md](file:///c:/Users/aniru/OneDrive/Desktop/test/implementationPlan.md). Do not jump to later phases prematurely.
3. **No Fabricated Data**: Never invent API fields, ASINs, prices, seller counts, or synthetic test results. If marketplace data is missing from a response, record `null` and display "Unavailable".
4. **Isolate Secrets**: All API keys (`GEMINI_API_KEY`, `SERPAPI_API_KEY`, etc.) must remain on the backend and in `.env`. Never commit secrets, and never leak them in logs, frontend bundles, or test files.
5. **No Blind Scraping or Hidden APIs**: Do not scrape Amazon directly, do not introduce Google Lens, and do not bypass CAPTCHAs or provider terms.
6. **External API Verification**:
   - Understand that SerpApi Amazon Search API (`engine=amazon`) returns search result snippets. It does **not** guarantee seller count.
   - Never infer seller count from the number of search results.
7. **Robust Validation**: Validate every external API response against a Pydantic schema before using it in downstream logic.
8. **Explainable Matching**: Match scores must reflect explainable attribute comparison. Do not present provisional ranking scores as statistically calibrated probabilities.
9. **Test-Driven Delivery**: Write unit tests alongside business logic. Normal automated tests must use mock fixtures and never require active external API keys. Live smoke tests are run on-demand with explicit credentials.
10. **Preserve Working Code**: Do not discard, overwrite, or regress existing working functionality without clear architectural justification.
11. **Update Living Context**: At the end of every meaningful task or phase, update `AGENTS.md` and `docs/IMPLEMENTATION_STATUS.md`.

---

## F. Current Implementation Status

| Phase | Description | Status | Implemented | Remaining | Verified Integrations / Tests | Blockers / Risks |
|---|---|---|---|---|---|---|
| **Phase 0** | Repository & Requirements Baseline | **COMPLETED** | Repo inspection, runtime check (Python 3.13.3, Node v24.13.0), Git init, `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`, `docs/IMPLEMENTATION_STATUS.md`, external API verification | None | Doc verification of Gemini & SerpApi Amazon Search parameters | None |
| **Phase 1** | Application Skeleton | **COMPLETED** | FastAPI backend setup, config, health endpoint, pytest suite, Next.js frontend setup, typed API client, live browser connectivity verification | None | 4 backend unit tests PASS (0.04s), Next.js production build PASS, browser subagent live connectivity check PASS | None |
| **Phase 2** | Image Upload & Validation | **COMPLETED** | Multipart upload endpoint `POST /api/product-matches`, Pillow signature & byte verification, EXIF sanitization & orientation normalization, ImageUploader React component | None | 10 unit tests for validation & uploads PASS, Next.js build PASS | None |
| **Phase 3** | Gemini Image Analysis | **COMPLETED** | `GeminiClient` adapter (`gemini-3.8-flash`), `AnalysisService`, schema validation (`ImageAnalysis`), timeout & retry logic, `AnalysisStatus.tsx` component, live vision test verified | None | 7 unit & mock tests PASS, live multimodal test PASS, Next.js build PASS | None |
| **Phase 4** | SerpApi Amazon Search Integration | **COMPLETED** | `SerpApiClient` adapter, `SearchService` (query dispatch, bounded fallback, ASIN deduplication), price parsing, `scripts/smoke_test.py`, live verification | None | 9 SerpApi tests PASS (30 total tests in 1.62s), live smoke test PASS (9 Amazon.in candidates discovered) | None |
| **Phase 6** | Price & Seller-Count Validation | **COMPLETED** | Price normalization (float/string/prices array), explicit currency (`INR`), null handling for missing prices/seller count, 20-listing manual verification audit | None | 7 unit tests PASS (67 total backend tests PASS), 20-listing audit script PASS, `docs/PRICE_AND_SELLER_COUNT_VALIDATION.md` | Seller count limitation documented per ADR-004 |
| **Phase 7** | Complete Frontend Workflow | **COMPLETED** | Next.js seller UI (`CandidateCard.tsx`, `CandidateList.tsx`), match score meters, confidence categorization, explainable signals breakdown, ASIN copy & external links, candidate confirmation | None | Next.js production build PASS, browser subagent live connectivity check PASS | None |
| **Phase 8** | Persistence & Search History | **COMPLETED** | SQLAlchemy models (`SearchModel`, `ImageAnalysisModel`, `ProductCandidateModel`, `MatchFeedbackModel`), SQLite local default and PostgreSQL URL support, `SearchRepository`, paginated history endpoint `GET /api/product-matches`, confirmation persistence | None | SQLite persistence tests and PostgreSQL URL normalization tests | PostgreSQL connection not yet verified against a provisioned deployment database |
| **Phase 9** | Evaluation & Reliability | **IN_PROGRESS** | Evaluation dataset, metrics framework, latency percentiles | Curate 100-sample labelled dataset, accuracy and reliability evaluation | — | — |
| **Phase 10** | Deployment & Handover | **IN_PROGRESS** | Free Render web service Blueprint, Vercel Next.js project config, and deployment instructions; no managed database is provisioned | Deploy frontend/backend, set provider credentials and external PostgreSQL URL, verify live end-to-end workflow | Configuration reviewed; live deployment not yet performed | Requires external PostgreSQL URL, Gemini and SerpApi keys, and deployment account access |

---

## G. Architecture Decisions and Assumptions

| Decision ID | Decision | Rationale | Alternatives Considered | Status | Date |
|---|---|---|---|---|---|
| **ADR-001** | Modular Monolith architecture | Simplest to develop, test, debug, and run locally without microservice overhead | Microservices, Serverless lambdas | Confirmed | 2026-10-15 |
| **ADR-002** | Google Gemini `gemini-3.8-flash` model for visual attribute extraction | Fast, cost-effective multimodal vision support with native JSON schema formatting; recommended by Google API for current accounts | `gemini-1.5-flash`, `gemini-2.5-flash` (deprecated for new users), CLIP + local embeddings | Confirmed | 2026-10-15 |
| **ADR-003** | SerpApi Amazon Search API with `amazon_domain=amazon.in` | Complies with architectural constraints, avoids direct scraping and IP bans | Custom Playwright/Scrapy scraper, Rainforest API | Confirmed | 2026-10-15 |
| **ADR-004** | Treat Seller Count as `null` / "Unavailable" from SerpApi Search endpoint | Verified that `engine=amazon` does not reliably provide seller/offer counts in search result snippets; scraping or extra calls without approval is prohibited | Guess from number of search results (rejected), call `amazon_product` per result (unapproved extra cost) | Confirmed | 2026-10-15 |
| **ADR-005** | Explainable heuristic scoring (Brand 25%, Model 30%, Category 15%, Variant 20%, Other 10%) | Transparent and debuggable; allows sellers to understand why a candidate matched | Opaque ML classifier, cross-encoder neural model | Provisional (subject to Phase 9 evaluation) | 2026-10-15 |
| **ADR-006** | SQLite with Repository Pattern for local development | Zero-config local persistence that transitions easily to PostgreSQL when deployed | PostgreSQL only (extra local dependency), in-memory dict (lost on restart) | Confirmed | 2026-10-15 |
| **ADR-007** | PostgreSQL through `DATABASE_URL` for deployed service; retain SQLite locally | Render supplies a PostgreSQL URL, and SQLAlchemy can use the same models and repository for both; normalize provider URL schemes to psycopg 3 | SQLite in production (ephemeral filesystem), separate persistence implementations | Confirmed | 2026-10-17 |
| **ADR-008** | Deploy API on Render free web service and frontend on Vercel Hobby; database remains externally managed | Uses the requested free hosting tiers while keeping PostgreSQL outside Render and avoiding a paid managed database | Paid hosting plans, Render-managed PostgreSQL, self-hosted infrastructure | Confirmed | 2026-10-17 |

---

## H. Known Issues, Unresolved Questions, and Technical Risks

1. **SerpApi Search Result Seller Count Limitation**:
   - *Risk*: SerpApi Amazon Search API (`engine=amazon`) returns search listing snippets (`asin`, `title`, `price`, `rating`, `thumbnail`). It does **not** expose total distinct sellers or Buy Box offer counts in organic search results.
   - *Mitigation*: Per architecture rule 7.3, represent seller count as `null` and show "Unavailable" in UI. If the client requires seller count in a future milestone, SerpApi's `engine=amazon_product` or `engine=amazon_offers` can be proposed as an approved secondary query.
2. **External API Credentials**:
   - `GEMINI_API_KEY` and `SERPAPI_API_KEY` are verified and active in `.env`.
   - Automated tests will continue to run against recorded/mocked responses when keys are absent.
3. **Python 3.13 Environment**:
   - Host environment has Python 3.13.3. Standard packages (FastAPI, Pydantic, Pillow, HTTPX, google-generativeai) are operational.

---

## I. Current State and Next Action

- **Current Implementation Phase**: Phase 6 — Price and Seller-Count Validation
- **Last Successfully Completed Milestone**: Phase 5 — Candidate Ranking and Normalization
- **Current Task**: Validate price parsing accuracy and seller count availability per ADR-004
- **Immediate Next Task**: Review price field extraction from SerpApi, execute 20-listing manual validation, document availability gaps
- **Blockers**: None. All 60 backend tests pass.

---

## J. Handover Instructions for Incoming Agents

If resuming or continuing work on this codebase:
1. **Read this file (`AGENTS.md`)** completely to understand the project context, current status, and rules.
2. **Review authoritative specs**: [architecture.md](file:///c:/Users/aniru/OneDrive/Desktop/test/architecture.md) and [implementationPlan.md](file:///c:/Users/aniru/OneDrive/Desktop/test/implementationPlan.md).
3. **Inspect the repository and Git status**: Run `git status` to see what files exist and check uncommitted changes.
4. **Inspect [docs/IMPLEMENTATION_STATUS.md](file:///c:/Users/aniru/OneDrive/Desktop/test/docs/IMPLEMENTATION_STATUS.md)** to see the granular task checklist.
5. **Verify the test suite**: Run the existing test suite (`pytest` in backend, `npm run build` in frontend) to confirm baseline integrity.
6. **Proceed with the immediate next task** identified in Section I.
7. **Never jump ahead across phases** or generate unverified code across multiple phases in one turn.
8. **Update `AGENTS.md` and `docs/IMPLEMENTATION_STATUS.md`** before completing your session.
