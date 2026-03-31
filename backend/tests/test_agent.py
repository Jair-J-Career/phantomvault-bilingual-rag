import pytest
from unittest.mock import patch, MagicMock
from app.models.schemas import StepResult


@pytest.mark.anyio
async def test_agent_missing_session(client):
    response = await client.post(
        "/api/agent",
        json={"session_id": "ghost", "query": "What is this?", "stream": False},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_agent_sync_returns_answer(client):
    fake_steps = [
        StepResult(tool="detect_language", input_summary="q", output_summary="en", latency_ms=10),
        StepResult(tool="retrieve", input_summary="q", output_summary="5 chunks", latency_ms=20),
        StepResult(tool="answer", input_summary="q", output_summary="The answer is 42.", latency_ms=50),
    ]
    with (
        patch("app.api.endpoints.agent.get_vector_store_manager") as mock_mgr_f,
        patch("app.api.endpoints.agent.PlannerAgent") as mock_agent_cls,
    ):
        mock_mgr = MagicMock()
        mock_mgr.session_exists.return_value = True
        mock_mgr_f.return_value = mock_mgr

        mock_agent = MagicMock()
        mock_agent.run.return_value = ("The answer is 42.", fake_steps)
        mock_agent_cls.return_value = mock_agent

        response = await client.post(
            "/api/agent",
            json={"session_id": "valid", "query": "What is the answer?", "stream": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The answer is 42."
    assert len(data["steps"]) == 3
    assert data["steps"][0]["tool"] == "detect_language"


def test_language_detector_english():
    from app.agents.tools.language_detector import detect_language
    assert detect_language("What are the main findings of this report?") == "en"


def test_language_detector_spanish():
    from app.agents.tools.language_detector import detect_language
    assert detect_language("¿Cuáles son las conclusiones principales?") == "es"


def test_fallback_plan():
    from app.agents.orchestrator import PlannerAgent
    plan = PlannerAgent._fallback_plan("test query")
    tools = [s["tool"] for s in plan]
    assert "detect_language" in tools
    assert "retrieve" in tools
    assert "answer" in tools


def test_plan_validation_removes_unknown_tools():
    from app.agents.orchestrator import PlannerAgent
    agent = PlannerAgent.__new__(PlannerAgent)
    bad_plan = [
        {"tool": "detect_language", "input": {}},
        {"tool": "hack_the_planet", "input": {}},
        {"tool": "answer", "input": {}},
    ]
    valid = agent._validate_plan(bad_plan, "query")
    assert all(s["tool"] != "hack_the_planet" for s in valid)
    assert len(valid) == 2
