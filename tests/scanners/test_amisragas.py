import logging

import pytest
from playwright.async_api import Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.amisragas import PLATFORM, download_invoice_by_period
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.utils import Utils


@pytest.mark.manual
async def test_amisragas_manual_login(
    page: Page,
    logger: logging.Logger,
):
    phone_num = Utils.get_mandatory_env("PARTIAL_PHONE_NUMBER")
    phone_initial = Utils.get_mandatory_env("PHONE_NUMBER_INITIAL")
    user_id = Utils.get_mandatory_env("DEFAULT_ID")

    url = "https://www.amisragas.co.il/recipts/"
    await page.goto(url)
    await page.locator("#govId").fill(user_id)
    await page.select_option("#phoneCode", value=phone_initial)
    await page.locator("#phoneNumber").fill(phone_num)
    await page.keyboard.press("Enter")
    await page.pause()
    await page.wait_for_url(url)

    await Utils.record_state(page=page, platform=PLATFORM, logger=logger, include_session_storage=True)

    periods = get_periods_to_download(PLATFORM)
    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)


############################################################
### Saving the state is not working for this site currently ###
############################################################
# @pytest.mark.using_state(PLATFORM)
# async def test_amisragas(
#     page: Page,
#     logger: logging.Logger,
# ):
#     url = "https://www.amisragas.co.il/recipts/"
#     await page.goto(url)
#     await Utils.wait_for_authenticated_selector(page=page, selector="text=בחירת כתובת", should_exist=True, platform=PLATFORM)

#     periods = get_periods_to_download(PLATFORM)
#     await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
