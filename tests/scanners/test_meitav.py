import logging

import pytest
from playwright.async_api import Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.scanners.meitav import PLATFORM, download_invoice_by_period
from invoice_scraper.secrets_client import GoogleSecretsClient
from invoice_scraper.utils import Utils


@pytest.mark.manual
async def test_meitav_manual_login(
    page: Page,
    logger: logging.Logger,
    google_secrets_client: GoogleSecretsClient,
):
    password = Utils.get_secret_from_google_secrets_client(google_secrets_client, "MEITAV_PASSWORD")

    user_id = Utils.get_mandatory_env("JESS_ID")

    url = "https://www.my-meitav.co.il/appartments"
    await page.goto(url)
    await page.get_by_role("button", name="כניסה באמצעות סיסמה").click()
    await page.locator("#pasportNumber").fill(user_id)
    await page.locator("#password").fill(password)
    await page.pause()
    try:
        await page.get_by_role("button", name="כניסה").click()
    except Exception:
        pass
    await page.wait_for_url(url)

    await Utils.record_state(page=page, platform=PLATFORM, logger=logger, include_session_storage=True)


@pytest.mark.using_state(PLATFORM)
async def test_meitav(
    page: Page,
    logger: logging.Logger,
):
    url = "https://www.my-meitav.co.il/appartments"
    await page.goto(url)
    await Utils.wait_for_authenticated_page(page=page, url=url, platform=PLATFORM)
    await page.locator("#allInfo").click()

    periods = get_periods_to_download(PLATFORM)
    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
