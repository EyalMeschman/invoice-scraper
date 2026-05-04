import logging

import pytest
from playwright.async_api import Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.scanners.chatgpt import PLATFORM, download_invoice_by_period
from invoice_scraper.utils import Utils


@pytest.mark.manual
async def test_chatgpt_manual_login(
    page: Page,
    logger: logging.Logger,
):
    username = Utils.get_mandatory_env("CHATGPT_USERNAME")
    password = Utils.get_mandatory_env("CHATGPT_PASSWORD")

    url = "https://chatgpt.com"
    await page.goto(url)
    await page.get_by_role("button", name="Log in").first.click()
    await page.get_by_role("button", name="Continue with Google").click()
    await page.wait_for_url("https://accounts.google.com/**")
    await page.locator("#identifierId").fill(username)
    await page.keyboard.press("Enter")
    await page.locator('input[name="Passwd"]').fill(password)
    await page.keyboard.press("Enter")
    await page.pause()
    await page.wait_for_url(url)

    await Utils.record_state(page=page, platform=PLATFORM, logger=logger, include_session_storage=True)


@pytest.mark.using_state(PLATFORM)
async def test_chatgpt(
    page: Page,
    logger: logging.Logger,
):
    url = "https://chatgpt.com"
    await page.goto(url)
    await Utils.wait_for_authenticated_page(page=page, url=url, platform=PLATFORM)
    await page.get_by_test_id("accounts-profile-button").first.click()
    await page.get_by_role("menuitem", name="Settings").click()
    await page.get_by_test_id("account-tab").click()
    payment_section = page.locator('div:has-text("Payment")')
    await payment_section.get_by_role("button", name="Manage").last.click()
    await page.wait_for_url("https://pay.openai.com/**")

    periods = get_periods_to_download(PLATFORM)

    # If downloading more than 3 periods, press "view more"
    if len(periods) > 3:
        await page.get_by_test_id("view-more-button").click()

    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
