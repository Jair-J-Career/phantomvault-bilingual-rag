import io
import pytest
from unittest.mock import patch, MagicMock


# Minimal valid PDF bytes (real magic number + enough structure to pass validation)
_FAKE_PDF = b"%PDF-1.4 fake pdf content for testing"


@pytest.mark.anyio
async def test_upload_rejects_non_pdf(client):
    response = await client.post(
        "/api/upload",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_rejects_wrong_magic_bytes(client):
    response = await client.post(
        "/api/upload",
        files={
            "file": (
                "bad.pdf",
                io.BytesIO(b"NOTPDF content here"),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_valid_pdf(client):
    """Happy-path upload with mocked PDF loader and vector store."""
    from langchain_core.documents import Document

    fake_chunks = [Document(page_content=f"chunk {i}") for i in range(5)]

    with (
        patch(
            "app.api.endpoints.upload.load_and_split", return_value=fake_chunks
        ),
        patch(
            "app.api.endpoints.upload.get_vector_store_manager"
        ) as mock_mgr_factory,
    ):
        mock_mgr = MagicMock()
        mock_mgr.create_session.return_value = "abc123"
        mock_mgr_factory.return_value = mock_mgr

        response = await client.post(
            "/api/upload",
            files={
                "file": (
                    "sample.pdf",
                    io.BytesIO(_FAKE_PDF),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "abc123"
    assert data["chunks"] == 5
    assert data["filename"] == "sample.pdf"


@pytest.mark.anyio
async def test_upload_too_large(client):
    big_content = b"%PDF" + b"x" * (21 * 1024 * 1024)  # 21MB
    response = await client.post(
        "/api/upload",
        files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
    )
    assert response.status_code == 413
