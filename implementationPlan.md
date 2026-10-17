Implementation Plan — Image-to-Amazon.in Product Matching Platform

Document type: Phase-by-Phase Engineering Execution Plan
Version: 1.0
Target coding environment: Google Antigravity
Primary goal: Build and validate a working prototype using Gemini API and SerpApi Amazon Search API.

1. Purpose

This document instructs Antigravity how to implement the platform incrementally.

Follow the phases in order. Each phase has an objective, tasks, expected files, acceptance criteria, and testing requirements.

Do not attempt to build the entire application in a single code-generation step.

Do not proceed past a phase's critical acceptance criteria until they are satisfied or the unresolved blocker is explicitly documented.

Global rules for Antigravity
Read AGENTS.md and docs/TECHNICAL_ARCHITECTURE.md before modifying code.
Inspect the existing repository before creating files.
Preserve existing working functionality unless a change is explicitly required.
Use small, reviewable changes.
Explain the implementation approach before major structural changes.
Write tests alongside business logic.
Run relevant tests after every meaningful change.
Never invent API responses, API capabilities, or successful test results.
Use mocks for normal automated tests and real credentials only for explicitly requested smoke tests.
Ask before introducing paid services, destructive database operations, or major architecture changes.
Do not add unrelated features.
Update documentation when an implementation decision changes.
Report completed work, files changed, commands run, test outcomes, and remaining issues at the end of each phase.
If blocked by unavailable credentials, implement the adapter and mocked tests, then clearly document the live integration as unverified.
Keep all external API calls on the backend.
2. Phase Overview
Phase	Deliverable	Estimated duration
0	Repository and requirements baseline	0.5 day
1	Backend and frontend skeleton	1 day
2	Image upload and validation	0.5–1 day
3	Gemini image analysis	1 day
4	SerpApi Amazon Search integration	1 day
5	Candidate ranking and result normalization	1 day
6	Price and seller-count validation	0.5–1 day
7	Complete frontend workflow	1–2 days
8	Persistence and search history	1 day
9	Evaluation and reliability	1–2 days
10	Deployment and handover	1 day

These are estimates for a focused prototype. Actual duration depends on development experience, API access, debugging, and provider limitations.

3. Phase 0 — Repository and Requirements Baseline
Objective

Establish the implementation contract and confirm that the chosen external services can support the critical product workflow.

Tasks
Inspect the repository.
Identify existing source code, dependency files, documentation, and configuration.
Read the technical architecture specification.
Verify current Gemini API documentation and the selected model's image-input and structured-output capabilities.
Verify SerpApi Amazon Search API documentation, country/domain parameters, response fields, and usage limits.
Obtain a representative live response when credentials are available.
Determine which fields are actually returned:
ASIN.
Product title.
Product URL.
Product image.
Price.
Seller/offer count, if any.
Record any unavailable fields as explicit integration risks.
Deliverables
AGENTS.md.
Root README.md.
.gitignore.
.env.example.
Updated documentation identifying verified and unverified API capabilities.
Acceptance criteria
The repository structure is understood.
Required environment variables are documented.
The Gemini model is selected based on current availability and capability.
The SerpApi endpoint and response structure are documented from current official documentation or actual responses.
No assumption is made that seller count is available without evidence.
Antigravity instruction

Do not begin a broad implementation before verifying the external integration contract. If credentials are unavailable, use documented schemas and mock responses, clearly labelling live integration as unverified.

4. Phase 1 — Application Skeleton
Objective

Create the smallest runnable frontend and backend.

Backend tasks
Initialize the Python project.
Configure the FastAPI application.
Add configuration management using environment variables.
Add GET /api/health.
Configure structured logging.
Add a consistent error-response format.
Configure pytest.
Add initial unit tests.
Frontend tasks
Initialize Next.js with TypeScript.
Enable strict TypeScript checks.
Add a basic application layout.
Create the main product-search page.
Create a typed API client.
Add an initial upload/results layout.
Configure frontend environment variables for the backend base URL.
Deliverables
Runnable frontend.
Runnable backend.
Dependency lockfiles.
.env.example.
Health endpoint.
Basic automated tests.
Acceptance criteria
Backend starts using documented commands.
Frontend starts using documented commands.
GET /api/health returns a successful response.
Frontend can reach the backend.
Missing required configuration produces a clear startup or request error.
No API secrets are exposed to the frontend.
5. Phase 2 — Image Upload and Validation
Objective

Allow users to submit product images safely.

Backend tasks
Implement POST /api/product-matches as a multipart upload endpoint.
Accept JPEG, PNG, and WebP.
Validate the file signature and actual image decoding.
Reject unsupported formats.
Enforce the configured upload-size limit.
Normalize image orientation.
Strip unnecessary metadata.
Resize oversized images while preserving product details.
Create an internal search UUID.
Return clear validation errors.
Clean up temporary files after processing or failure.
Frontend tasks
Implement ImageUploader.tsx.
Support file selection.
Display an image preview.
Validate obvious client-side errors before submission.
Show upload and processing states.
Show server-side validation errors.

Client-side checks are for user experience only; backend validation remains mandatory.

Deliverables
Image validation utility.
Upload endpoint.
Image uploader component.
Tests for invalid and valid files.
Acceptance criteria
A valid image is accepted.
Corrupt and unsupported images are rejected.
Oversized uploads are rejected.
File extensions cannot bypass content validation.
Temporary files are cleaned up according to the implementation policy.
No Gemini or SerpApi call occurs before validation succeeds.
6. Phase 3 — Gemini Image Analysis
Objective

Extract product attributes and useful text search queries from the uploaded image.

Tasks
Create backend/app/integrations/gemini_client.py.
Encapsulate Gemini-specific API code in the adapter.
Add the selected model and API key to configuration.
Implement backend/app/services/analysis_service.py.
Construct a prompt that requests:
Product category.
Brand, if visible or reliably identifiable.
Model number, if visible.
Color and variant attributes.
Visible packaging or product text.
Identifying physical attributes.
Uncertainties.
Up to three focused search queries.
Define Pydantic schemas for the structured output.
Validate every response.
Handle timeouts, quota exhaustion, and malformed output.
Log request duration and available usage metadata without logging secrets.
Add mocked unit and integration tests.
Example analysis schema
{
  "product_category": "wireless headphones",
  "brand": "ExampleBrand",
  "model": "X200",
  "color": "black",
  "visible_text": ["X200"],
  "identifying_attributes": ["over-ear design"],
  "uncertainties": [],
  "search_queries": [
    "ExampleBrand X200 wireless headphones",
    "ExampleBrand X200 black headphones"
  ]
}


Example values are illustrative only.

Deliverables
Gemini adapter.
Analysis service.
Validated analysis schema.
Prompt and error-handling tests.
Acceptance criteria
A sample image produces valid structured output when live credentials are available.
Unknown attributes can be represented as null or empty collections according to the schema.
Malformed model responses do not crash the application.
The number of search queries is bounded.
Provider errors produce controlled application errors.
Unit tests pass without requiring a live Gemini API key.
Important constraint

Do not implement a custom-trained vision model, CLIP embeddings, or a vector database in this phase.

7. Phase 4 — SerpApi Amazon Search Integration
Objective

Search Amazon.in using the queries generated by Gemini.

Tasks
Create backend/app/integrations/serpapi_client.py.
Implement the documented Amazon Search endpoint.
Use the documented parameter for the Indian marketplace.
Keep the API key exclusively on the backend.
Set connection and request timeouts.
Validate response status and schema.
Normalize provider-specific errors.
Parse available candidate listings.
Capture available ASIN, title, URL, image URL, and price fields.
Add bounded retries for transient failures.
Add tests using saved, sanitized fixture responses.
Track the number of SerpApi requests per lookup.
Search policy
Start with one primary query.
If results are insufficient, allow one additional distinct query.
Configure the maximum number of queries per lookup.
Deduplicate candidates by ASIN.
Avoid repeating identical requests.
Respect provider quotas and terms.
Deliverables
SerpApi adapter.
Candidate response schema.
Search service.
Mocked provider tests.
A live smoke-test script.
Acceptance criteria
Search requests use Amazon.in as the target marketplace.
Candidate results are parsed using verified provider fields.
Malformed provider responses fail safely.
Duplicate ASINs are removed.
Provider credentials do not appear in logs.
The application handles empty results gracefully.
Live test

With valid credentials, search for a known product and verify the resulting ASIN and URL against the listing.

Do not claim that the integration works with live Amazon.in results until this test has actually passed.

8. Phase 5 — Candidate Ranking and Normalization
Objective

Select the most promising candidates without incorrectly assuming that the first search result is correct.

Tasks
Create backend/app/services/matching_service.py.
Implement a pure candidate-scoring function.
Normalize product attributes for comparison.
Compare brand, model, category, color, size, and pack quantity when available.
Deduplicate by ASIN.
Penalize verified attribute conflicts.
Preserve missing information as unknown rather than as a mismatch.
Return the top three candidates.
Attach a provisional score and confidence label.
Include explainable match signals for debugging.
Initial scoring weights
Brand: 25%.
Model: 30%.
Category: 15%.
Variant attributes: 20%.
Other descriptive attributes: 10%.

These weights are initial configuration values, not empirically validated constants.

Acceptance criteria
Exact model conflicts lower the score.
Color, size, and pack-count differences affect ranking.
Missing attributes do not automatically become mismatches.
Scores remain within the documented range.
Candidate order is deterministic for identical inputs.
Tests cover exact matches, near matches, variant mismatches, and no-result cases.
Confidence rules

Initial thresholds:

high: score at least 0.85 with no critical contradiction.
medium: score from 0.60 to below 0.85.
low: score below 0.60.

Treat these as ranking heuristics, not calibrated probabilities.

Always allow the seller to select a different candidate.

9. Phase 6 — Validate Price and Seller Count
Objective

Determine which required marketplace metrics are actually available through the selected provider.

Tasks
Review the current Amazon Search API response schema.
Identify the exact price field and its units.
Determine whether the price is current and whether it refers to the expected listing offer.
Identify whether a seller-count field exists.
If present, document what the field measures.
If absent, mark seller count as unavailable.
Test a sample of at least 20 manually verified Amazon.in listings.
Record price availability and seller-count availability separately.
Record the data retrieval timestamp.
Document any gap that requires another data source.
Important distinction

The following are not interchangeable:

Number of distinct sellers.
Number of available offers.
Number of offers for a specific condition.
Number of sellers competing for the Buy Box.

The product must use a clearly labelled metric.

Do not infer seller count from the number of search results, product ratings, or other unrelated values.

Acceptance criteria
Price parsing is covered by tests.
Currency handling is explicit.
Missing prices are represented as null.
Missing seller counts are represented as null.
Every displayed metric has a documented meaning and retrieval timestamp.
The 20-listing validation results are recorded.
Decision gate

If seller count is not exposed by the chosen endpoint, do not fabricate a workaround. Document the limitation and request approval before adding a separate data source.

10. Phase 7 — Complete the Frontend Workflow
Objective

Connect the working backend pipeline to a usable seller-facing application.

Tasks
Complete the main upload page.
Display the selected image preview.
Submit the image to the backend.
Display loading and progress states.
Show the extracted product attributes.
Display the top three candidates.
Show product image, title, ASIN, and Amazon.in URL.
Display the available price and currency.
Display seller count when verified.
Display "Unavailable" for missing fields.
Display the last-retrieved timestamp.
Show match confidence and the main matching signals.
Allow the seller to open the product listing.
Allow the seller to confirm a candidate.
Allow retry after recoverable failures.
Design requirements
Keep the interface simple and responsive.
Clearly distinguish verified data from inferred attributes.
Do not use fake product data in production paths.
Include empty, loading, success, and failure states.
Provide useful feedback for low-confidence matches.
Ensure external product links are safely rendered.
Acceptance criteria

A seller can complete the end-to-end workflow without using API tools or manually editing JSON.

11. Phase 8 — Persistence and Search History
Objective

Save enough information to support repeat searches, debugging, and evaluation.

Tasks
Implement the Search entity.
Implement the ImageAnalysis entity.
Implement the ProductCandidate entity.
Implement the MatchFeedback entity.
Add database migrations.
Persist completed searches and normalized results.
Record creation and completion timestamps.
Add paginated search history.
Avoid storing image files permanently unless necessary.
Keep database operations behind repository functions.
Acceptance criteria
Search records survive application restarts.
Candidate results can be retrieved by search ID.
Duplicate candidates cannot be inserted for the same search.
Database errors are handled gracefully.
User-specific access is enforced once authentication is enabled.

SQLite is sufficient for local development. Use PostgreSQL when deployment requirements justify it.

12. Phase 9 — Evaluation and Reliability
Objective

Measure whether the system actually solves the matching problem.

Tasks
Assemble at least 100 labelled product images.
Record the expected ASIN for each image.
Label exact variants where known.
Execute the matching pipeline against the dataset.
Record top-1 and top-3 exact-match accuracy.
Measure variant-confusion rate.
Measure no-match rate.
Measure price and seller-count availability.
Measure average latency.
Estimate provider cost per lookup.
Inspect common errors.
Adjust prompts, query strategy, and scoring weights based on results.
Required metrics
Top-1 exact-match accuracy.
Top-3 exact-match accuracy.
Exact-variant accuracy.
Price availability rate.
Seller-count availability rate.
Average and percentile lookup latency.
Failed lookup rate.
API requests per lookup.
Estimated cost per successful lookup.

Do not report an unmeasured accuracy percentage.

Reliability work
Test timeouts and retries.
Test provider rate limits.
Verify graceful handling of empty results.
Prevent duplicate requests where practical.
Add bounded request limits.
Ensure temporary image cleanup.
Review logging for sensitive information.
Acceptance criteria

The project has a repeatable evaluation procedure, recorded baseline metrics, and documented limitations.

13. Phase 10 — Deployment and Handover
Objective

Deploy a small working prototype and document how another developer can operate it.

Tasks
Select a deployment target compatible with the budget and current service limits.
Verify current free-tier availability before committing.
Configure production environment variables.
Configure frontend-to-backend connectivity.
Configure CORS.
Configure persistent database storage.
Verify upload limits and temporary storage cleanup.
Run migrations.
Execute backend tests.
Execute frontend checks.
Execute a live end-to-end smoke test.
Document deployment and rollback steps.
Deliverables
Deployment configuration.
Updated README.
Environment-variable guide.
Local development commands.
Smoke-test procedure.
Known limitations.
API usage and cost notes.
Acceptance criteria
A developer can run the application from a clean checkout.
Deployment secrets are not committed.
The deployed frontend can reach the backend.
A real image can be analyzed and searched using valid credentials.
Missing seller data is displayed honestly.
Failure handling and operational instructions are documented.
14. Required Development Commands

Document the actual commands used by the generated repository.

Expected backend commands may resemble:

cd backend
python -m venv .venv


Activate the virtual environment using the appropriate command for the operating system, then install dependencies using the repository's selected package manager.

Run the backend:

uvicorn app.main:app --reload


Run backend tests:

pytest


Expected frontend commands may resemble:

cd frontend
npm install
npm run dev


Run frontend checks using the scripts actually defined in package.json, such as:

npm run lint
npm run build


Do not document a command as working unless the relevant configuration exists and it has been verified.

15. Antigravity Execution Protocol

At the start of each phase:

Read the relevant architecture and implementation documents.
Inspect existing files.
Summarize the tasks for the phase.
Identify dependencies and risks.
Implement only the phase's scope.

At the end of each phase, report:

Files created.
Files modified.
Main implementation decisions.
Commands executed.
Tests passed.
Tests failed.
Live integrations verified.
Integrations still mocked or unverified.
Remaining blockers.
Recommended next phase.

Do not mark a phase complete simply because code was generated.

A phase is complete only when its acceptance criteria are satisfied, or the outstanding limitations are explicitly recorded.

If a critical assumption proves false, stop the dependent work, explain the issue, propose alternatives, and wait for approval when the alternative changes the architecture, introduces paid services, or materially changes product scope.

16. Final Prototype Acceptance Criteria

The prototype is ready for demonstration when:

A seller can upload a product photograph.
Gemini analyzes the image and produces validated attributes.
SerpApi performs text-based Amazon.in product searches.
The backend normalizes and ranks candidate products.
The UI displays the top three candidates when available.
A seller can confirm a candidate.
The correct Amazon product URL is displayed for validated candidates.
Price is displayed only when retrieved and validated.
Seller count is displayed only when its meaning and source are verified.
Missing information is explicitly identified.
Search results and timestamps are persisted.
Automated tests pass.
A labelled evaluation dataset has been tested.
Setup and deployment instructions are complete.
API limitations, usage limits, and remaining risks are documented.
17. Scope Protection

Do not expand the initial prototype into a production-scale system prematurely.

Do not add the following without evidence that the current design is insufficient:

Microservices.
Kubernetes.
A vector database.
Custom-trained AI models.
Google Lens integration.
Automated Amazon page scraping.
Real-time price monitoring.
Complex background orchestration.
Subscription billing.

Prioritize the end-to-end workflow, correct product matching, verified marketplace data, and measurable results.

The primary success criterion is not how much code has been generated. It is whether the system can correctly match real seller-uploaded images to Amazon.in listings and return trustworthy, traceable product information.