from __future__ import annotations

import json
import time
from typing import Any

from openai import OpenAI

from .browser import BROWSER_TOOLS, LocalBrowser
from .config import AgentConfig
from .personas import Persona


def run_browser_agent(
    config: AgentConfig,
    persona: Persona,
    task_instruction: str,
    browser: LocalBrowser,
) -> dict[str, Any]:
    if not config.api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Set it in agent/.env before running the AI agent.")

    client = OpenAI(api_key=config.api_key, timeout=min(30, config.timeout_seconds), max_retries=1)
    deadline = time.monotonic() + config.timeout_seconds
    instructions = (
        "You are participating in a controlled local bookstore usability study. "
        "Complete the task by interacting with the rendered website using only the supplied browser tools. "
        "Use the exact accessible names reported by inspect_page when clicking. "
        "After changing search or filters, inspect the visible results before repeating an action. "
        "Do not repeat an action when the visible page already reflects it. "
        "Do not claim success without inspecting the final cart. Do not use any external website. "
        f"Interaction-style configuration: {persona.strategy_guidance} "
        f"Decision style: {persona.decision_style}. Retry limit: {persona.retry_limit}. "
        f"Exploration level: {persona.exploration_level}. Patience level: {persona.patience_level}. "
        f"Verification level: {persona.verification_level}. "
        f"Instruction dependence: {persona.instruction_dependence}."
    )
    response = client.responses.create(
        model=config.model,
        instructions=instructions,
        input=f"Task: {task_instruction}",
        tools=BROWSER_TOOLS,
        tool_choice="auto",
        max_output_tokens=1200,
    )
    model_calls = 1
    tool_calls = 0
    final_text = ""

    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Run stopped: configured time limit reached")
        calls = [item for item in response.output if getattr(item, "type", "") == "function_call"]
        final_text = response.output_text or final_text
        if not calls:
            break
        outputs = []
        for call in calls:
            if tool_calls >= config.max_actions:
                raise RuntimeError("Run stopped: maximum browser actions reached")
            tool_calls += 1
            try:
                arguments = json.loads(call.arguments)
                result = browser.tool_dispatch(call.name, arguments)
            except Exception as error:
                browser.errors += 1
                browser.retries += 1
                result = {"ok": False, "error": str(error)}
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=True),
                }
            )
        if model_calls >= config.max_model_calls:
            raise RuntimeError("Run stopped: maximum model calls reached")
        if time.monotonic() >= deadline:
            raise TimeoutError("Run stopped: configured time limit reached")
        response = client.responses.create(
            model=config.model,
            instructions=instructions,
            previous_response_id=response.id,
            input=outputs,
            tools=BROWSER_TOOLS,
            tool_choice="auto",
            max_output_tokens=1200,
        )
        model_calls += 1

    return {
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "final_text": final_text,
    }
