from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "agent" / ".env")


@dataclass(frozen=True)
class AgentConfig:
    app_base_url: str
    api_base_url: str
    model: str
    api_key: str
    timeout_seconds: int = 180
    max_actions: int = 30
    max_model_calls: int = 12
    screenshot_directory: Path = ROOT / "reports" / "evidence"


def _local_url(value: str, variable_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError(f"{variable_name} must use a localhost or 127.0.0.1 URL")
    return value.rstrip("/")


def load_config() -> AgentConfig:
    return AgentConfig(
        app_base_url=_local_url(os.getenv("APP_BASE_URL", "http://localhost:5173"), "APP_BASE_URL"),
        api_base_url=_local_url(os.getenv("API_BASE_URL", "http://localhost:8000"), "API_BASE_URL"),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        timeout_seconds=int(os.getenv("AGENT_TIMEOUT_SECONDS", "180")),
        max_actions=int(os.getenv("AGENT_MAX_ACTIONS", "30")),
        max_model_calls=int(os.getenv("AGENT_MAX_MODEL_CALLS", "12")),
    )
