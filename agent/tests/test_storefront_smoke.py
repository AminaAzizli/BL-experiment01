from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from agent.browser import LocalBrowser
from agent.config import AgentConfig


APP_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5173")


def test_rendered_t1_and_t5_start_states_reset_consistently():
    try:
        import requests

        requests.get(APP_URL, timeout=2).raise_for_status()
        requests.get("http://localhost:8000/api/bookstore/versions", timeout=2).raise_for_status()
    except Exception as error:
        pytest.skip(f"Local storefront and API are required for browser smoke test: {error}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        agent_browser = LocalBrowser(
            page,
            context,
            AgentConfig(APP_URL, "http://localhost:8000", "test-model", ""),
            Path(os.getenv("TEMP", ".")),
        )
        page.goto(f"{APP_URL}/?task=T5&version=A", wait_until="domcontentloaded")
        page.get_by_test_id("cart-panel").wait_for(state="visible", timeout=15000)
        page.get_by_test_id("quantity-book-1").wait_for(state="visible", timeout=10000)
        assert page.get_by_test_id("quantity-book-1").inner_text() == "1"
        page_inspection = agent_browser.inspect_page()
        assert "BehaviourLens" in page_inspection["visible_text"]
        assert agent_browser.verify_task_state("T5", "book-1")["success"] is False
        initial_subtotal = float(page.get_by_test_id("cart-total").inner_text().replace("$", ""))

        page.get_by_role("button", name="Increase The Last Orion quantity").click()
        assert page.get_by_role("button", name="Update", exact=True).is_visible()
        assert float(page.get_by_test_id("cart-total").inner_text().replace("$", "")) == initial_subtotal
        page.get_by_role("button", name="Update", exact=True).click()
        updated_subtotal = float(page.get_by_test_id("cart-total").inner_text().replace("$", ""))
        assert page.get_by_test_id("quantity-book-1").inner_text() == "2"
        assert updated_subtotal == initial_subtotal * 2
        assert agent_browser.verify_task_state("T5", "book-1")["success"] is True

        page.get_by_role("button", name="Version B", exact=True).click()
        page.get_by_role("button", name="T5", exact=True).click()
        assert page.get_by_test_id("quantity-book-1").inner_text() == "1"
        assert float(page.get_by_test_id("cart-total").inner_text().replace("$", "")) == initial_subtotal

        page.get_by_role("button", name="T1", exact=True).click()
        assert page.get_by_placeholder("Title or author").input_value() == ""
        assert page.locator('[data-testid="cart-panel"] .cart-item').count() == 0
        page.get_by_label("Search books by title or author").fill("Signal in the Dust")
        page.get_by_role("button", name="Add Signal in the Dust to cart", exact=True).click()
        assert page.locator('[data-testid="cart-panel"] .cart-item').get_attribute("data-product-id") == "book-2"
        assert agent_browser.verify_task_state("T1", "book-2")["success"] is True
        context.close()
        browser.close()


def test_offline_event_queue_flushes_events_added_during_inflight_batch():
    try:
        import requests

        requests.get(APP_URL, timeout=2).raise_for_status()
    except Exception as error:
        pytest.skip(f"Local storefront is required for browser queue test: {error}")

        with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(APP_URL, wait_until="domcontentloaded")
                result = page.evaluate(
                        """async () => {
                            const queue = await import('/src/lib/eventQueue.ts')
                            localStorage.clear()
                            const sessionId = 'queue-drain-test'
                            queue.enqueueResearchEvent(sessionId, { event_type: 'task_started', task_id: 'T1' })
                            let requestNumber = 0
                            window.fetch = async (_url, options) => {
                                requestNumber += 1
                                if (requestNumber === 1) {
                                    await new Promise((resolve) => setTimeout(resolve, 50))
                                    queue.enqueueResearchEvent(sessionId, { event_type: 'session_completed', task_id: 'T1' })
                                }
                                const batch = JSON.parse(options.body).events.length
                                return new Response(JSON.stringify({ accepted: batch, duplicates: 0 }), { status: 200 })
                            }
                            const flushed = await queue.flushQueuedResearchEvents(sessionId)
                            return { flushed, remaining: queue.getQueuedResearchEventCount(sessionId), requestNumber }
                        }"""
                )
                assert result == {"flushed": 2, "remaining": 0, "requestNumber": 2}
                browser.close()
