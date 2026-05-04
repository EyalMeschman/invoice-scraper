import logging

import pytest
from playwright.async_api import Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.scanners.partner import PLATFORM, download_invoice_by_period
from invoice_scraper.utils import Utils


@pytest.mark.manual
async def test_partner_manual_login(
    page: Page,
    logger: logging.Logger,
):
    user_id = Utils.get_mandatory_env("DEFAULT_ID")
    phone_num = Utils.get_mandatory_env("DEFAULT_PHONE_NUMBER")

    url = "https://www.partner.co.il/n/mypartner/invoice"
    await page.goto(url)
    await page.get_by_role("textbox", name="אפשר גם ח.פ.").fill(user_id)
    await page.wait_for_timeout(500)
    await page.get_by_role("button", name="המשך").click()
    await page.get_by_role("textbox", name="מספר הנייד הוא").fill(phone_num)
    await page.wait_for_timeout(500)
    await page.get_by_role("button", name="המשך").click()
    await page.pause()
    try:
        await page.get_by_role("button", name="המשך").click()
    except Exception:
        pass
    await page.wait_for_url(url)

    await Utils.record_state(page=page, platform=PLATFORM, logger=logger)


@pytest.mark.using_state(PLATFORM)
async def test_partner(
    page: Page,
    logger: logging.Logger,
):
    url = "https://www.partner.co.il/n/mypartner/invoice"
    await page.goto(url)
    await Utils.wait_for_authenticated_selector(page=page, selector="text=אפשר גם ח.פ.", should_exist=False, platform=PLATFORM)
    await page.get_by_role("button", name="לא, תודה").click()

    periods = get_periods_to_download(PLATFORM)
    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
