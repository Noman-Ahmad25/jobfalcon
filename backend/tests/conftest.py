import pytest
from fastapi.testclient import TestClient
from app.main import create_application


@pytest.fixture
def app():
    """Create a clean application instance for testing."""
    return create_application()


@pytest.fixture
def client(app):
    """Synchronous test client using FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client
