import pytest
from httpx import ASGITransport, AsyncClient

from app.database import init_db
from app.main import app


@pytest.fixture(autouse=True)
def initialize_test_database():
    """Ensure database schema exists for all tests."""
    init_db()


@pytest.fixture
async def client():
    """Async test client using httpx ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def async_client(client):
    """Alias for client fixture."""
    return client
