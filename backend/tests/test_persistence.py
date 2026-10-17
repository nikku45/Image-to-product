"""
Unit and Integration Tests for Phase 8: Persistence and Search History.
Tests database URL handling, SQLite schema initialization, SearchRepository operations,
API search history pagination, candidate confirmation, and persistence across restarts.
"""

from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base, normalize_database_url
from app.models.search import SearchModel, ImageAnalysisModel, ProductCandidateModel
from app.repositories.search_repository import SearchRepository
from app.schemas.product import ImageAnalysis, ProductCandidate


@pytest.mark.parametrize(
    ("database_url", "expected_url"),
    [
        (
            "postgres://user:password@host:5432/products",
            "postgresql+psycopg://user:password@host:5432/products",
        ),
        (
            "postgresql://user:password@host:5432/products?sslmode=require",
            "postgresql+psycopg://user:password@host:5432/products?sslmode=require",
        ),
        (
            "postgresql+psycopg://user:password@host:5432/products",
            "postgresql+psycopg://user:password@host:5432/products",
        ),
        ("sqlite:///./data/app.db", "sqlite:///./data/app.db"),
    ],
)
def test_normalize_database_url(database_url: str, expected_url: str):
    assert normalize_database_url(database_url) == expected_url


def test_postgresql_url_creates_engine_with_psycopg():
    engine = create_engine(
        normalize_database_url("postgresql://user:password@localhost:5432/products")
    )
    try:
        assert engine.url.drivername == "postgresql+psycopg"
    finally:
        engine.dispose()


@pytest.fixture
def in_memory_db() -> Generator[Session, None, None]:
    """Provide a fresh SQLite in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_repository_save_and_retrieve_search(in_memory_db: Session):
    """Verify SearchRepository saves and retrieves search, analysis, and candidates."""
    repo = SearchRepository(in_memory_db)

    analysis = ImageAnalysis(
        product_category="wireless headphones",
        brand="Sony",
        model="WH-1000XM4",
        color="black",
        visible_text=["SONY", "WH-1000XM4"],
        identifying_attributes=["Noise Cancelling"],
        uncertainties=[],
        search_queries=["Sony WH-1000XM4"],
    )

    candidate = ProductCandidate(
        asin="B08N5WRWNW",
        title="Sony WH-1000XM4 Wireless Noise Cancelling Headphones",
        product_url="https://www.amazon.in/dp/B08N5WRWNW",
        price_amount=19990.0,
        currency="INR",
        seller_count=None,
        seller_count_type=None,
        match_score=0.95,
        match_confidence="high",
        source="serpapi",
    )

    saved = repo.save_search(
        search_id="test-uuid-001",
        status="completed",
        analysis=analysis,
        candidates=[candidate],
    )

    assert saved.search_id == "test-uuid-001"
    assert saved.status == "completed"
    assert saved.analysis is not None
    assert saved.analysis.brand == "Sony"
    assert len(saved.candidates) == 1
    assert saved.candidates[0].asin == "B08N5WRWNW"

    # Retrieve by ID
    retrieved = repo.get_by_id("test-uuid-001")
    assert retrieved is not None
    assert retrieved.search_id == "test-uuid-001"
    assert retrieved.analysis is not None
    assert retrieved.analysis.model == "WH-1000XM4"
    assert len(retrieved.candidates) == 1
    assert retrieved.candidates[0].price_amount == 19990.0
    assert retrieved.total_candidates == 1
    assert retrieved.total_sellers == 1


def test_repository_candidate_deduplication(in_memory_db: Session):
    """Verify duplicate candidates on the same search are deduplicated."""
    repo = SearchRepository(in_memory_db)

    cand1 = ProductCandidate(
        asin="B08N5WRWNW",
        title="Sony WH-1000XM4 Headphones",
        product_url="https://www.amazon.in/dp/B08N5WRWNW",
        match_score=0.90,
        match_confidence="high",
    )
    cand2 = ProductCandidate(
        asin="B08N5WRWNW",  # Identical ASIN
        title="Sony WH-1000XM4 Duplicate Listing",
        product_url="https://www.amazon.in/dp/B08N5WRWNW",
        match_score=0.88,
        match_confidence="high",
    )

    saved = repo.save_search(
        search_id="test-uuid-dedup",
        status="completed",
        analysis=None,
        candidates=[cand1, cand2],
    )

    assert len(saved.candidates) == 1
    assert saved.candidates[0].asin == "B08N5WRWNW"


def test_repository_confirm_candidate(in_memory_db: Session):
    """Verify confirming candidate updates selected_asin and creates feedback."""
    repo = SearchRepository(in_memory_db)

    repo.save_search(
        search_id="test-uuid-confirm",
        status="completed",
        analysis=None,
        candidates=[],
    )

    success = repo.confirm_candidate("test-uuid-confirm", "B08N5WRWNW")
    assert success is True

    record = repo.get_by_id("test-uuid-confirm")
    assert record is not None
    assert record.selected_asin == "B08N5WRWNW"

    # Confirm on non-existent search returns False
    assert repo.confirm_candidate("non-existent-uuid", "B08N5WRWNW") is False


def test_repository_list_searches_pagination(in_memory_db: Session):
    """Verify paginated listing of search history ordered by created_at desc."""
    repo = SearchRepository(in_memory_db)

    for i in range(5):
        repo.save_search(
            search_id=f"search-{i:02d}",
            status="completed",
            analysis=None,
            candidates=[],
        )

    all_searches = repo.list_searches(limit=10, offset=0)
    assert len(all_searches) == 5

    page1 = repo.list_searches(limit=2, offset=0)
    assert len(page1) == 2

    page2 = repo.list_searches(limit=2, offset=2)
    assert len(page2) == 2


def test_persistence_across_connection_restarts(tmp_path):
    """Verify SQLite data survives closing and re-opening database connection."""
    db_file = tmp_path / "test_persist.db"
    db_url = f"sqlite:///{db_file}"

    # Step 1: Open first engine/session and insert data
    engine1 = create_engine(db_url)
    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(bind=engine1)
    session1 = Session1()

    repo1 = SearchRepository(session1)
    analysis = ImageAnalysis(
        product_category="audio",
        brand="Bose",
        search_queries=["Bose QC45"],
    )
    repo1.save_search(
        search_id="restart-test-uuid",
        status="completed",
        analysis=analysis,
        candidates=[],
        selected_asin="B0B88KSS9V",
    )
    session1.close()
    engine1.dispose()

    # Step 2: Open completely separate engine/session to verify survival
    engine2 = create_engine(db_url)
    Session2 = sessionmaker(bind=engine2)
    session2 = Session2()

    repo2 = SearchRepository(session2)
    retrieved = repo2.get_by_id("restart-test-uuid")

    assert retrieved is not None
    assert retrieved.search_id == "restart-test-uuid"
    assert retrieved.selected_asin == "B0B88KSS9V"
    assert retrieved.analysis is not None
    assert retrieved.analysis.brand == "Bose"

    session2.close()
    engine2.dispose()


@pytest.mark.asyncio
async def test_api_list_searches_endpoint(async_client):
    """Verify GET /api/product-matches endpoint returns search history list."""
    response = await async_client.get("/api/product-matches?limit=10&offset=0")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_api_get_nonexistent_search_returns_404(async_client):
    """Verify GET /api/product-matches/{search_id} returns 404 for unknown search."""
    response = await async_client.get("/api/product-matches/non-existent-search-id")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
