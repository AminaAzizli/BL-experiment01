from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from agent.browser import LocalBrowser
from agent.browser import BROWSER_TOOLS
from agent.config import AgentConfig, load_config
from agent.personas import PERSONAS, get_persona, persona_parameters
from agent.report import write_reports


def test_all_documented_personas_load_structured_parameters():
    expected = {
        "neutral_baseline",
        "low_digital_experience",
        "low_patience",
        "low_risk_tolerance",
        "high_experience",
    }
    assert set(PERSONAS) == expected
    assert get_persona("low_patience").retry_limit == 1
    assert persona_parameters("neutral_baseline")["decision_style"] == "balanced"
    with pytest.raises(ValueError):
        get_persona("unknown")


def test_agent_config_rejects_non_local_urls(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://example.com")
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8000")
    with pytest.raises(ValueError, match="localhost"):
        load_config()


def test_browser_navigation_rejects_external_origin():
    config = AgentConfig(
        app_base_url="http://localhost:5173",
        api_base_url="http://localhost:8000",
        model="test-model",
        api_key="",
    )
    browser = LocalBrowser(SimpleNamespace(), SimpleNamespace(), config, Path("unused"))
    with pytest.raises(ValueError, match="restricted"):
        browser._local_navigation("https://example.com")
    assert browser._local_navigation("http://localhost:5173/?task=T1") == "http://localhost:5173/?task=T1"
    assert {tool["name"] for tool in BROWSER_TOOLS} == {
        "navigate_page",
        "inspect_page",
        "click_element",
        "fill_input",
        "select_option",
        "press_key",
        "inspect_cart",
        "take_screenshot",
    }


def test_report_generation_exports_observed_runs_and_human_sessions(monkeypatch):
    monkeypatch.setattr(
        "agent.report.requests.get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: [
                {
                    "session_id": "human-session",
                    "actor_type": "human",
                    "persona": "human_participant",
                    "version": "A",
                    "task_id": "T1",
                    "status": "completed",
                    "success": True,
                    "event_count": 4,
                    "actions": 2,
                    "retries": 0,
                    "errors": 0,
                    "cart": [{"product_id": "book-2", "quantity": 1}],
                }
            ],
        ),
    )
    observed_run = {
        "run_id": "ai-run",
        "session_id": "ai-session",
        "actor_type": "ai",
        "persona": "neutral_baseline",
        "version": "B",
        "task_id": "T1",
        "success": True,
        "duration_seconds": 4.5,
        "actions": 3,
        "retries": 0,
        "errors": 0,
    }
    with TemporaryDirectory() as directory:
        paths = write_reports("http://localhost:8000", [observed_run], Path(directory))
        assert all(path.exists() for path in paths)
        content = paths[2].read_text(encoding="utf-8")
        assert "ai-run" in content
        assert "human-session" in content
        summary = paths[0].read_text(encoding="utf-8")
        assert "Preliminary" in summary
        assert "Version B" in summary
        assert "Human/AI actor comparison" in summary
