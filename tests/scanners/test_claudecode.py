import logging

import pytest
from playwright.async_api import Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.scanners.claudecode import PLATFORM, download_invoice_by_period
from invoice_scraper.utils import Utils


@pytest.mark.manual
@pytest.mark.cdp
async def test_claudecode_manual_login(
    cdp_page: Page,
    logger: logging.Logger,
) -> None:
    """
    Manual login for Claude Code via CDP.

    Before running this test, start Chrome with:
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        --remote-debugging-port=9222 --user-data-dir="C:\\Temp\\chrome_dev_session"

    Then:
    1. Navigate to https://claude.ai
    2. Complete the login
    3. Run this test - it will connect and save the authentication state
    """
    username = Utils.get_mandatory_env("CLAUDECODE_USERNAME")
    url = "https://claude.ai/new"

    await cdp_page.goto(url)
    await cdp_page.locator("#email").fill(username)
    await cdp_page.pause()
    await cdp_page.wait_for_url(url)

    await Utils.record_state(page=cdp_page, platform=PLATFORM, logger=logger, include_session_storage=True)


@pytest.mark.using_state(PLATFORM)
async def test_claudecode(
    page: Page,
    logger: logging.Logger,
):
    url = "https://claude.ai/settings/billing"
    await page.goto(url)
    await Utils.wait_for_authenticated_page(page=page, url=url, platform=PLATFORM)

    periods = get_periods_to_download(PLATFORM)
    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
