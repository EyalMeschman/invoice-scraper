import logging

import pytest
from playwright.async_api import Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.arnona import PLATFORM, download_invoice_by_period
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.utils import Utils


@pytest.mark.manual
async def test_arnona_manual_login(
    page: Page,
    logger: logging.Logger,
):
    user_id = Utils.get_mandatory_env("DEFAULT_ID")

    url = "https://city4u.co.il/PortalServicesSite/_portal/279000"
    await page.goto(url)
    await page.get_by_role("button", name="כניסה לחשבון").click()
    await page.locator("#UserNameOTP").click()
    await page.locator("#UserNameOTP").fill(user_id)
    await page.keyboard.press("Enter")
    await page.pause()
    await page.wait_for_url(url)

    await Utils.record_state(page=page, platform=PLATFORM, logger=logger, include_session_storage=True)


@pytest.mark.using_state(PLATFORM)
async def test_arnona(
    page: Page,
    logger: logging.Logger,
) -> None:
    url = "https://city4u.co.il/PortalServicesSite/city4u/279000/waterDocuments"
    await page.goto(url)
    await page.wait_for_selector("table#datatable")

    periods = get_periods_to_download(PLATFORM)
    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
