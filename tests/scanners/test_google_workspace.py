import logging

from playwright.async_api import Locator, Page

from invoice_scraper.config import get_periods_to_download
from invoice_scraper.scanners.base import run_download_loop
from invoice_scraper.scanners.google_workspace import PLATFORM, download_invoice_by_period
from invoice_scraper.utils import Utils


async def test_google_workspace(
    page: Page,
    logger: logging.Logger,
):
    username = Utils.get_mandatory_env("GOOGLE_WORKSPACE_USERNAME")
    password = Utils.get_mandatory_env("GOOGLE_WORKSPACE_PASSWORD")

    url = "https://admin.google.com/u/7/ac/billing/accounts/w2D_un6NA_-1iXkWulbFKw/transactions?hl=en"
    await page.goto(url)
    await page.locator("#identifierId").fill(username)
    await page.keyboard.press("Enter")
    await page.locator('input[name="Passwd"]').fill(password)
    await page.keyboard.press("Enter")
    await page.wait_for_url("**/transactions?**")

    periods = get_periods_to_download(PLATFORM)

    # If downloading more than 2 periods, change filter to "This year"
    if len(periods) > 2:
        iframe_frame: Locator = page.locator('iframe[name^="embeddedBilling"]')
        content_frame = iframe_frame.content_frame
        if not content_frame:
            raise ValueError("Could not find billing iframe")

        await content_frame.get_by_role("listbox").filter(has_text="Last 3 months").click()
        await content_frame.get_by_role("menuitem", name="This year").click()
        await content_frame.get_by_role("heading", name="Jan 1").wait_for()

    await run_download_loop(page, PLATFORM, periods, download_invoice_by_period, logger)
