import json
import logging
import os

import pytest
from playwright.async_api import Browser, async_playwright
from pytest import FixtureRequest, Item

from invoice_scraper.config import load_config
from invoice_scraper.logger import Logger
from invoice_scraper.secrets_client import GoogleSecretsClient
from invoice_scraper.utils import Utils

PLATFORM_PATH = 0

load_config()


@pytest.fixture(name="logger", scope="session")
def fixture_logger() -> logging.Logger:
    return Logger.create()


@pytest.fixture(name="google_secrets_client", scope="session")
def fixture_google_secrets_client(logger: logging.Logger) -> GoogleSecretsClient:
    return GoogleSecretsClient(logger=logger)


@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser, logger: logging.Logger, request: FixtureRequest):
    node: Item = request.node
    marker = node.get_closest_marker("using_state")
    storage_state = None
    session_storage_data = None

    if marker:
        platform = marker.args[PLATFORM_PATH]
        state_path = os.path.join("playwright", ".auth", f"{platform}.json")

        if not os.path.exists(state_path):
            raise FileNotFoundError(f"State file not found: {state_path}")

        storage_state = state_path
        logger.info(f"Loading state from {state_path}")

        with open(state_path, "r", encoding="utf-8") as f:
            state_data = json.load(f)
            for origin_data in state_data.get("origins", []):
                if "sessionStorage" in origin_data or "localStorage" in origin_data:
                    origin = origin_data["origin"]
                    local_storage = origin_data.get("localStorage", [])
                    session_storage = origin_data.get("sessionStorage", [])

                    session_storage_data = {
                        "origin": origin,
                        "localStorage": local_storage,
                        "sessionStorage": session_storage,
                    }
                    logger.info(
                        "Found storage for %s with %d localStorage + %d sessionStorage items",
                        origin,
                        len(local_storage),
                        len(session_storage),
                    )
                    break

    context = await browser.new_context(
        storage_state=storage_state,
        bypass_csp=True,
        ignore_https_errors=True,
    )
    Utils.cover_footprints(context)

    if session_storage_data:
        script_lines = []

        script_lines.append("try {")
        for entry in session_storage_data["localStorage"]:
            name = json.dumps(entry["name"])
            value = json.dumps(entry["value"])
            script_lines.append(f"  localStorage.setItem({name}, {value});")

        for entry in session_storage_data["sessionStorage"]:
            name = json.dumps(entry["name"])
            value = json.dumps(entry["value"])
            script_lines.append(f"  sessionStorage.setItem({name}, {value});")

        script_lines.append("} catch(e) { console.error('Storage injection failed:', e); }")
        init_script = "\n".join(script_lines)
        await context.add_init_script(init_script)
        logger.info(
            "Injected init script for %d localStorage + %d sessionStorage items",
            len(session_storage_data["localStorage"]),
            len(session_storage_data["sessionStorage"]),
        )

    page = await context.new_page()
    page.on("console", lambda msg: logger.debug(msg.text))

    yield page

    await page.close()
    await context.close()


@pytest.fixture
async def cdp_page(logger: logging.Logger):
    """
    Connect to a manually opened Chrome instance via CDP.

    Before running the test, start Chrome with:
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\Temp\\chrome_dev_session"
    """
    async with async_playwright() as p:
        logger.info("Connecting to Chrome via CDP on port 9222...")
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            logger.info("Successfully connected to Chrome!")
        except Exception as e:
            raise RuntimeError(f"Could not connect to Chrome.\nError: {e}") from e

        if not browser.contexts:
            raise RuntimeError("No browser contexts found. Make sure Chrome has at least one window open.")

        context = browser.contexts[0]

        page = context.pages[0] if context.pages else await context.new_page()

        yield page

        logger.info("Disconnecting from Chrome (browser will stay open)")
        await browser.close()


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "manual: mark test as manual login")
    config.addinivalue_line("markers", "cdp: mark test to use CDP connection to manual Chrome")
    config.addinivalue_line(
        "markers",
        "using_state(platform): mark test to use state for the given platform",
    )
