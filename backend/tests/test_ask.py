import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.anyio
async def test_ask_missing_session(client):
    response = await client.post(
        "/api/ask",
        json={"session_id": "nonexistent", "question": "What is this?"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ask_returns_answer(client):
    with (
        patch(
            "app.api.endpoints.ask.get_vector_store_manager"
        ) as mock_mgr_factory,
        patch("app.api.endpoints.ask._get_llm") as mock_llm_factory,
        patch("app.api.endpoints.ask.create_retrieval_chain") as mock_chain_factory,
        patch(
            "app.api.endpoints.ask.create_stuff_documents_chain"
        ) as mock_stuff_factory,
    ):
        # Session exists
        mock_mgr = MagicMock()
        mock_mgr.session_exists.return_value = True
        mock_mgr.get_retriever.return_value = MagicMock()
        mock_mgr_factory.return_value = mock_mgr

        # Chain returns a canned answer
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = {"answer": "The sky is blue."}
        mock_chain_factory.return_value = mock_chain

        response = await client.post(
            "/api/ask",
            json={"session_id": "valid_session", "question": "What color is the sky?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The sky is blue."
    assert data["question"] == "What color is the sky?"
    assert data["session_id"] == "valid_session"
