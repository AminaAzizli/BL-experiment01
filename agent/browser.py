from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Locator, Page, TimeoutError as PlaywrightTimeoutError

from .config import AgentConfig

ALLOWED_ROLES = {"button", "link", "textbox", "combobox", "checkbox", "radio", "option"}
ALLOWED_KEYS = {"Enter", "Escape", "Tab", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"}


class LocalBrowser:
    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        config: AgentConfig,
        evidence_dir: Path,
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        self.page = page
        self.context = context
        self.config = config
        self.evidence_dir = evidence_dir
        self.event_callback = event_callback
        self.actions = 0
        self.retries = 0
        self.errors = 0
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def _count_action(self) -> None:
        self.actions += 1
        if self.actions > self.config.max_actions:
            raise RuntimeError("Run stopped: maximum browser actions reached")

    def _local_navigation(self, url: str) -> str:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin != self.config.app_base_url:
            raise ValueError("Browser navigation is restricted to the configured local BehaviourLens app")
        return url

    def navigate(self, url: str) -> dict[str, Any]:
        self._count_action()
        try:
            self.page.goto(self._local_navigation(url), wait_until="domcontentloaded", timeout=20000)
            return {"ok": True, "url": self.page.url, "title": self.page.title()}
        except Exception as error:
            self.errors += 1
            return {"ok": False, "error": str(error)}

    def inspect_page(self) -> dict[str, Any]:
        self._count_action()
        try:
            body_text = self.page.locator("body").inner_text(timeout=5000)
            buttons = self.page.get_by_role("button").all()
            headings = self.page.get_by_role("heading").all_text_contents()
            inputs = self.page.get_by_role("textbox").all()
            selects = self.page.get_by_role("combobox").all()
            return {
                "url": self.page.url,
                "title": self.page.title(),
                "headings": headings[:40],
                "buttons": [
                    button.get_attribute("aria-label") or button.inner_text().strip()
                    for button in buttons[:80]
                ],
                "textboxes": [
                    {
                        "label": item.get_attribute("aria-label") or item.get_attribute("placeholder") or "",
                        "type": item.get_attribute("type") or "text",
                    }
                    for item in inputs[:40]
                ],
                "selects": [
                    {"label": item.get_attribute("aria-label") or "", "options": item.locator("option").all_text_contents()}
                    for item in selects[:20]
                ],
                "visible_text": body_text[:12000],
            }
        except Exception as error:
            self.errors += 1
            return {"error": str(error)}

    def _role_locator(self, role: str, name: str) -> Locator:
        if role not in ALLOWED_ROLES:
            raise ValueError(f"Unsupported accessible role: {role}")
        if not name.strip() or len(name) > 160:
            raise ValueError("Accessible name must contain 1 to 160 characters")
        return self.page.get_by_role(role, name=name, exact=True)

    def click_element(self, role: str, name: str) -> dict[str, Any]:
        self._count_action()
        try:
            self._role_locator(role, name).click(timeout=5000)
            return {"ok": True, "clicked": {"role": role, "name": name}}
        except PlaywrightTimeoutError as error:
            self.errors += 1
            return {"ok": False, "error": f"No unique visible {role} named '{name}' was clickable: {error}"}
        except Exception as error:
            self.errors += 1
            return {"ok": False, "error": str(error)}

    def fill_input(self, label: str, value: str) -> dict[str, Any]:
        self._count_action()
        if len(value) > 500:
            return {"ok": False, "error": "Input value is too long"}
        try:
            self.page.get_by_label(label, exact=True).fill(value, timeout=5000)
            return {"ok": True, "filled_label": label}
        except Exception as error:
            self.errors += 1
            return {"ok": False, "error": str(error)}

    def select_option(self, label: str, value: str) -> dict[str, Any]:
        self._count_action()
        try:
            self.page.get_by_label(label, exact=True).select_option(value, timeout=5000)
            return {"ok": True, "selected": value, "label": label}
        except Exception as error:
            self.errors += 1
            return {"ok": False, "error": str(error)}

    def press_key(self, key: str) -> dict[str, Any]:
        self._count_action()
        if key not in ALLOWED_KEYS:
            return {"ok": False, "error": "Key is not in the allowed key set"}
        try:
            self.page.keyboard.press(key)
            return {"ok": True, "pressed": key}
        except Exception as error:
            self.errors += 1
            return {"ok": False, "error": str(error)}

    def inspect_cart(self) -> dict[str, Any]:
        self._count_action()
        try:
            cart_panel = self.page.get_by_test_id("cart-panel")
            return {"visible_cart": cart_panel.inner_text(timeout=5000)}
        except Exception as error:
            self.errors += 1
            return {"error": str(error)}

    def verify_task_state(self, task_id: str, target_product_id: str) -> dict[str, Any]:
        items = self.page.locator('[data-testid="cart-panel"] .cart-item')
        cart_state: list[dict[str, Any]] = []
        for index in range(items.count()):
            item = items.nth(index)
            quantity_text = item.locator('[data-testid^="quantity-"]').inner_text().strip()
            cart_state.append(
                {
                    "product_id": item.get_attribute("data-product-id"),
                    "quantity": int(quantity_text),
                    "unit_price": float(item.get_attribute("data-price") or "0"),
                }
            )

        subtotal_text = self.page.get_by_test_id("cart-total").inner_text()
        subtotal = float(subtotal_text.replace("$", "").replace(",", "").strip())
        if task_id == "T1":
            success = any(item["product_id"] == target_product_id and item["quantity"] >= 1 for item in cart_state)
        elif task_id == "T5":
            success = (
                len(cart_state) == 1
                and cart_state[0]["product_id"] == target_product_id
                and cart_state[0]["quantity"] == 2
                and round(subtotal, 2) == round(cart_state[0]["unit_price"] * 2, 2)
            )
        else:
            success = False
        return {"success": success, "cart": cart_state, "subtotal": subtotal}

    def take_screenshot(self) -> dict[str, Any]:
        self._count_action()
        path = self.evidence_dir / f"page-{self.actions:03d}.png"
        try:
            self.page.screenshot(path=str(path), full_page=True)
            return {"screenshot": str(path)}
        except Exception as error:
            self.errors += 1
            return {"error": str(error)}

    def tool_dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "navigate_page": lambda: self.navigate(arguments["url"]),
            "inspect_page": lambda: self.inspect_page(),
            "click_element": lambda: self.click_element(arguments["role"], arguments["name"]),
            "fill_input": lambda: self.fill_input(arguments["label"], arguments["value"]),
            "select_option": lambda: self.select_option(arguments["label"], arguments["value"]),
            "press_key": lambda: self.press_key(arguments["key"]),
            "inspect_cart": lambda: self.inspect_cart(),
            "take_screenshot": lambda: self.take_screenshot(),
        }
        if name not in handlers:
            self.errors += 1
            return {"ok": False, "error": f"Unknown browser tool: {name}"}
        try:
            result = handlers[name]()
            if isinstance(result, dict) and result.get("ok") is False:
                self.retries += 1
            self._record_tool_event(name, arguments, result)
            return result
        except Exception as error:
            self.errors += 1
            return {"ok": False, "error": str(error)}

    def _record_tool_event(self, name: str, arguments: dict[str, Any], result: Any) -> None:
        if self.event_callback is None or not isinstance(result, dict) or result.get("ok") is False:
            return
        if name == "select_option":
            self.event_callback(
                "filter_changed",
                {
                    "control": arguments.get("label"),
                    "filter_label": arguments.get("label"),
                    "value": arguments.get("value"),
                },
            )
        elif name == "press_key" and arguments.get("key") == "Enter":
            search = self.page.get_by_label("Search books by title or author", exact=True)
            self.event_callback(
                "search_submitted",
                {"query_length": len(search.input_value()), "result_count": self.page.locator(".product-card").count()},
            )
        elif name == "click_element":
            accessible_name = arguments.get("name", "")
            if accessible_name.startswith("Add ") and accessible_name.endswith(" to cart"):
                product_title = accessible_name[4:-8]
                card = self.page.get_by_role("heading", name=product_title, exact=True).locator("xpath=ancestor::article")
                self.event_callback(
                    "product_viewed",
                    {"product_id": card.get_attribute("data-product-id")},
                )
                self.event_callback(
                    "add_to_cart",
                    {
                        "product_id": card.get_attribute("data-product-id"),
                        "low_contrast": card.get_attribute("data-low-contrast") == "true",
                    },
                )
                self.event_callback(
                    "cart_updated",
                    {"product_id": card.get_attribute("data-product-id"), "action": "add"},
                )
            elif accessible_name.startswith(("Increase ", "Decrease ")):
                requires_confirmation = self.page.get_by_role("button", name="Update", exact=True).is_visible()
                self.event_callback(
                    "quantity_changed",
                    {"control": accessible_name, "requires_confirmation": requires_confirmation},
                )
            elif accessible_name == "Update":
                self.event_callback("cart_updated", {"confirmed": True})
            elif accessible_name in {"Continue", "Proceed to checkout"}:
                self.event_callback("checkout_started", {"button_label": accessible_name})
                errors = self.page.locator(".error-message").all_text_contents()
                if any(errors):
                    self.event_callback("validation_error", {"field_count": sum(bool(item.strip()) for item in errors)})


def install_local_request_guard(context: BrowserContext, config: AgentConfig) -> None:
    allowed_origins = {config.app_base_url, config.api_base_url}

    def guard(route: Any) -> None:
        request_url = route.request.url
        parsed = urlparse(request_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in allowed_origins or parsed.scheme in {"data", "blob"}:
            route.continue_()
        else:
            route.abort()

    context.route("**/*", guard)


BROWSER_TOOLS = [
    {
        "type": "function",
        "name": "navigate_page",
        "description": "Navigate only within the configured local BehaviourLens app.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_page",
        "description": "Read visible page text, headings, and button names.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "click_element",
        "description": "Click one visible element by accessible role and exact accessible name.",
        "parameters": {
            "type": "object",
            "properties": {"role": {"type": "string", "enum": sorted(ALLOWED_ROLES)}, "name": {"type": "string"}},
            "required": ["role", "name"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "fill_input",
        "description": "Fill a visible labelled input with text.",
        "parameters": {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "string"}}, "required": ["label", "value"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "select_option",
        "description": "Select an option in a visible labelled select control.",
        "parameters": {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "string"}}, "required": ["label", "value"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "press_key",
        "description": "Press one of Enter, Escape, Tab, or an arrow key.",
        "parameters": {"type": "object", "properties": {"key": {"type": "string", "enum": sorted(ALLOWED_KEYS)}}, "required": ["key"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_cart",
        "description": "Read the visible cart contents and subtotal.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "take_screenshot",
        "description": "Save a screenshot of the current rendered page as run evidence.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
]
