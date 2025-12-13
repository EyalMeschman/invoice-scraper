import logging
from enum import StrEnum
from pathlib import Path

import pytest
from playwright.async_api import Page

from src.scanner_config import Platform, YEAR, get_periods_to_download
from src.utils import Utils


class InvoicePeriod(StrEnum):
    PERIOD_1 = "Jan"  # January
    PERIOD_2 = "Feb"  # February
    PERIOD_3 = "Mar"  # March
    PERIOD_4 = "Apr"  # April
    PERIOD_5 = "May"  # May
    PERIOD_6 = "Jun"  # June
    PERIOD_7 = "Jul"  # July
    PERIOD_8 = "Aug"  # August
    PERIOD_9 = "Sep"  # September
    PERIOD_10 = "Oct"  # October
    PERIOD_11 = "Nov"  # November
    PERIOD_12 = "Dec"  # December


PLATFORM = Platform.CLAUDECODE
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)
]


async def download_invoice_by_period(
    page: Page, period: InvoicePeriod, download_dir: Path, logger: logging.Logger
) -> Path:
    invoice_list = page.get_by_test_id("invoice-list")

    row = (
        invoice_list.locator("tbody tr")
        .filter(has_text=period)
        .filter(has_text=str(YEAR))
    )

    async with page.context.expect_page() as new_page_info:
        await row.get_by_role("link", name="View").click()

    new_page = await new_page_info.value
    await new_page.wait_for_url("https://invoice.stripe.com/**")

    async with new_page.expect_download() as download_info:
        await new_page.get_by_test_id("download-invoice-receipt-pdf-button").click()

    download = await download_info.value

    save_path = download_dir / f"{PLATFORM}_{period}_{YEAR}.pdf"
    await download.save_as(save_path)

    await new_page.close()

    logger.info(f"Downloaded {period.name} to {save_path}")

    return save_path


@pytest.mark.manual
@pytest.mark.cdp
async def test_claudecode_manual_login(
    cdp_page: Page,
    logger: logging.Logger,
) -> None:
    # pylint: disable=line-too-long
    """
    Manual login for Claude Code via CDP.

    Before running this test, start Chrome with:
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\Temp\\chrome_dev_session"

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

    await Utils.record_state(
        page=cdp_page, platform=PLATFORM, logger=logger, include_session_storage=True
    )


@pytest.mark.using_state(PLATFORM)
async def test_claudecode(
    page: Page,
    logger: logging.Logger,
) -> None:
    url = "https://claude.ai/settings/billing"
    await page.goto(url)

    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(
            page=page, period=period, download_dir=download_dir, logger=logger
        )

    logger.info(f"All downloads completed in {download_dir}")
