from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from playwright.sync_api import sync_playwright

from .browser import LocalBrowser, install_local_request_guard
from .config import AgentConfig, ROOT, load_config
from .event_logger import EventLogger
from .openai_client import run_browser_agent
from .personas import PERSONAS, get_persona, persona_parameters
from .report import write_reports

TASKS = {
    "T1": "Find the book Signal in the Dust and add it to your shopping cart.",
    "T5": "Change the quantity of the book in your cart from one to two and verify that the cart total has been updated.",
}


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def _create_session(config: AgentConfig, version: str, task_id: str, persona_name: str, run_id: str) -> tuple[str, str]:
    study = _post_json(
        f"{config.api_base_url}/api/studies",
        {
            "name": "BehaviourLens Mini Experiment",
            "study_code": f"AI-{run_id[:12]}",
            "ethics_status": "local_demo",
            "preregistration_version": "mini-v1",
        },
    )
    session = _post_json(
        f"{config.api_base_url}/api/sessions",
        {
            "study_id": study["id"],
            "participant_id": f"AI-{run_id}",
            "actor_type": "ai",
            "persona": persona_name,
            "persona_parameters": persona_parameters(persona_name),
            "model_name": config.model,
            "run_id": run_id,
            "assigned_version": version,
            "ui_language": "en",
            "task_instructions": TASKS[task_id],
        },
    )
    return session["session_id"], f"{config.app_base_url}/?{urlencode({'version': version, 'task': task_id, 'session_id': session['session_id'], 'actor': 'ai'})}"


def _catalog_target(config: AgentConfig, task_id: str) -> str:
    response = requests.get(f"{config.api_base_url}/api/bookstore/versions", timeout=10)
    response.raise_for_status()
    data = response.json()
    if data["parity_check"]["status"] != "passed":
        raise RuntimeError(f"A/B catalogue parity failed: {data['parity_check']['message']}")
    products = data["version_a"]["products"]
    if task_id == "T1":
        target = next((product for product in products if product["title"] == "Signal in the Dust"), None)
    else:
        target = products[0] if products else None
    if target is None:
        raise RuntimeError(f"Could not resolve hidden verification product for {task_id}")
    return target["id"]


def _run_once(config: AgentConfig, version: str, task_id: str, persona_name: str, repetition: int) -> dict[str, Any]:
    persona = get_persona(persona_name)
    run_id = str(uuid.uuid4())
    session_id, app_url = _create_session(config, version, task_id, persona_name, run_id)
    target_product_id = _catalog_target(config, task_id)
    started_at = datetime.now(timezone.utc)
    start_clock = time.monotonic()
    evidence_dir = config.screenshot_directory / run_id
    logger = EventLogger(config.api_base_url, session_id, task_id)
    logger.record("session_started", {"actor_type": "ai", "version": version, "persona": persona_name, "run_id": run_id})
    logger.record("task_started", {"task_id": task_id})
    result: dict[str, Any] = {
        "run_id": run_id,
        "session_id": session_id,
        "actor_type": "ai",
        "model_name": config.model,
        "persona": persona_name,
        "persona_parameters": persona_parameters(persona_name),
        "version": version,
        "task_id": task_id,
        "started_at": started_at.isoformat(),
        "success": False,
        "cart": [],
        "subtotal": 0,
        "actions": 0,
        "retries": 0,
        "errors": 0,
        "model_calls": 0,
        "screenshots": [],
        "error_message": "",
    }

    browser = None
    playwright = None
    try:
        with sync_playwright() as playwright:
            chromium = playwright.chromium.launch(headless=True)
            context = chromium.new_context(viewport={"width": 1440, "height": 1000})
            install_local_request_guard(context, config)
            page = context.new_page()
            page.set_default_timeout(5000)
            browser = LocalBrowser(
                page,
                context,
                config,
                evidence_dir,
                event_callback=lambda event_type, payload: logger.record(event_type, payload),
            )
            navigation = browser.navigate(app_url)
            if not navigation.get("ok"):
                raise RuntimeError(navigation.get("error", "Local site navigation failed"))
            page.get_by_test_id("cart-panel").wait_for(state="visible", timeout=20000)
            page.get_by_role("heading", name=task_id, exact=True).wait_for(state="visible", timeout=10000)
            result["screenshots"].append(browser.take_screenshot().get("screenshot", ""))
            agent_result = run_browser_agent(config, persona, TASKS[task_id], browser)
            result["model_calls"] = agent_result["model_calls"]
            result["agent_final_text"] = agent_result["final_text"]
            verification = browser.verify_task_state(task_id, target_product_id)
            result.update(verification)
            logger.record("task_completed" if verification["success"] else "task_failed", {
                "success": verification["success"],
                "subtotal": verification["subtotal"],
                "cart": verification["cart"],
            })
            screenshot = browser.take_screenshot()
            result["screenshots"].append(screenshot.get("screenshot", ""))
            result["actions"] = browser.actions
            result["retries"] = browser.retries
            result["errors"] = browser.errors
            result["browser_tool_calls"] = agent_result["tool_calls"]
            context.close()
            chromium.close()
    except Exception as error:
        result["error_message"] = str(error)
        result["errors"] = (browser.errors if browser else 0) + 1
        if browser:
            result["actions"] = browser.actions
            result["retries"] = browser.retries
            try:
                screenshot = browser.take_screenshot()
                result["screenshots"].append(screenshot.get("screenshot", ""))
            except Exception:
                pass
        logger.record("task_failed", {"success": False, "reason": str(error)[:500]})
    finally:
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        result["duration_seconds"] = round(time.monotonic() - start_clock, 3)
        result["repetition"] = repetition
        logger.record(
            "run_metrics",
            {
                "actions": result["actions"],
                "retries": result["retries"],
                "errors": result["errors"],
                "success": result["success"],
            },
        )
        logger.record("session_completed", {"success": result["success"]})
        result["event_log"] = list(logger.all_events)
        try:
            logger.flush()
            _post_json(
                f"{config.api_base_url}/api/sessions/{session_id}/complete",
                {"status": "completed" if result["success"] else "failed"},
            )
        except Exception as error:
            result["error_message"] = "; ".join(filter(None, [result["error_message"], f"Could not finalize session: {error}"]))

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local BehaviourLens AI bookstore experiments")
    parser.add_argument("--version", choices=["A", "B"], required=True)
    parser.add_argument("--persona", choices=sorted(PERSONAS), default="neutral_baseline")
    parser.add_argument("--task", choices=sorted(TASKS), required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-actions", type=int, default=None)
    parser.add_argument("--max-model-calls", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.repeat < 1 or args.repeat > 20:
        raise SystemExit("--repeat must be between 1 and 20")
    config = load_config()
    if args.model:
        config = AgentConfig(**{**config.__dict__, "model": args.model})
    if args.max_actions:
        config = AgentConfig(**{**config.__dict__, "max_actions": args.max_actions})
    if args.max_model_calls:
        config = AgentConfig(**{**config.__dict__, "max_model_calls": args.max_model_calls})
    if not config.api_key:
        raise SystemExit("OPENAI_API_KEY is missing. Copy agent/.env.example to agent/.env and set the key.")

    results = []
    for repetition in range(1, args.repeat + 1):
        result = _run_once(config, args.version, args.task, args.persona, repetition)
        results.append(result)
        print(json.dumps({key: result[key] for key in ("run_id", "success", "duration_seconds", "actions", "retries", "errors", "error_message")}, ensure_ascii=True))
    report_paths = write_reports(config.api_base_url, results, ROOT / "reports")
    print("Reports:")
    for path in report_paths:
        print(path)


if __name__ == "__main__":
    main()
