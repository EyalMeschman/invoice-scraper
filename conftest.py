import json
import logging
import os

import pytest
from pytest import FixtureRequest, Item
from dotenv import load_dotenv
from playwright.async_api import Browser, async_playwright

from google_secrets_client import GoogleSecretsClient
from logger import Logger
from src.utils import Utils

PLATFORM_PATH = 0

load_dotenv(".env.defaults")
load_dotenv(".env", override=True)


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
    # Check if test has using_state marker
    item: Item = request.node
    marker = item.get_closest_marker("using_state")
    storage_state = None
    session_storage_data = None

    if marker:
        platform = marker.args[PLATFORM_PATH]
        state_path = os.path.join("playwright", ".auth", f"{platform}.json")

        if not os.path.exists(state_path):
            raise FileNotFoundError(f"State file not found: {state_path}")

        storage_state = state_path
        logger.info(f"Loading state from {state_path}")

        # Load sessionStorage if present in the state file
        with open(state_path, "r", encoding="utf-8") as f:
            state_data = json.load(f)
            for origin_data in state_data.get("origins", []):
                if "sessionStorage" in origin_data:
                    session_storage_data = {
                        "origin": origin_data["origin"],
                        "items": origin_data["sessionStorage"],
                    }
                    logger.info(
                        f"Found sessionStorage for {origin_data['origin']} with {len(origin_data['sessionStorage'])} items"
                    )
                    break

    context = await browser.new_context(
        storage_state=storage_state,
        bypass_csp=True,
        ignore_https_errors=True,
    )
    Utils.cover_footprints(context)

    page = await context.new_page()
    page.on("console", lambda msg: logger.debug(msg.text))

    # Inject sessionStorage if we loaded it
    if session_storage_data:
        await page.goto(session_storage_data["origin"])
        for item in session_storage_data["items"]:
            # Use parameterized evaluation to prevent JavaScript injection
            await page.evaluate(
                "(data) => sessionStorage.setItem(data.name, data.value)",
                {"name": item["name"], "value": item["value"]},
            )
        logger.info(
            f"Injected {len(session_storage_data['items'])} sessionStorage items"
        )

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
            raise RuntimeError(f"Could not connect to Chrome.\n" f"Error: {e}") from e

        if not browser.contexts:
            raise RuntimeError(
                "No browser contexts found. Make sure Chrome has at least one window open."
            )

        context = browser.contexts[0]

        page = context.pages[0] if context.pages else await context.new_page()

        yield page

        logger.info("Disconnecting from Chrome (browser will stay open)")
        await browser.close()


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "manual: mark test as manual login")
    config.addinivalue_line(
        "markers", "cdp: mark test to use CDP connection to manual Chrome"
    )
    config.addinivalue_line(
        "markers",
        "using_state(platform): mark test to use state for the given platform",
    )
