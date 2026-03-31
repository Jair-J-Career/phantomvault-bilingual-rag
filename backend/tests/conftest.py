import os
import pytest
import tempfile

# Set env vars before any app import so Settings doesn't fail
os.environ.setdefault("GOOGLE_API_KEY", "test-key-placeholder")
os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp())
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp())

from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
