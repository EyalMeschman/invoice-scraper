import logging
from enum import StrEnum
from pathlib import Path

import pytest

from playwright.async_api import Page
from src.scanner_config import YEAR, Platform, get_periods_to_download
from src.utils import Utils


class InvoicePeriod(StrEnum):
    PERIOD_1 = "01"  # January
    PERIOD_2 = "02"  # February
    PERIOD_3 = "03"  # March
    PERIOD_4 = "04"  # April
    PERIOD_5 = "05"  # May
    PERIOD_6 = "06"  # June
    PERIOD_7 = "07"  # July
    PERIOD_8 = "08"  # August
    PERIOD_9 = "09"  # September
    PERIOD_10 = "10"  # October
    PERIOD_11 = "11"  # November
    PERIOD_12 = "12"  # December


PLATFORM = Platform.AMISRAGAS
PERIODS_TO_DOWNLOAD = [InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)]


async def download_invoice_by_period(page: Page, period: InvoicePeriod, download_dir: Path, logger: logging.Logger) -> Path:
    row = page.locator(f"table#datatable tbody tr:has-text('{period}')").first
    link_cell = row.locator("td").first

    async with page.context.expect_page() as new_page_info:
        await link_cell.click()
    new_page: Page = await new_page_info.value
    await new_page.wait_for_load_state()

    blob_url = new_page.url
    pdf_content = await Utils.download_pdf_from_blob_url(new_page, blob_url)

    save_path = download_dir / f"{period}.pdf"
    save_path.write_bytes(pdf_content)

    logger.info(f"Downloaded {period.name} to {save_path}")
    await new_page.close()

    return save_path


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


@pytest.mark.using_state(PLATFORM)
async def test_amisragas(
    page: Page,
    logger: logging.Logger,
):
    url = "https://www.amisragas.co.il/recipts/"
    await page.goto(url)
    await Utils.wait_for_authenticated_selector(page=page, selector="text=בחירת כתובת", platform=PLATFORM)

    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(page, period, download_dir, logger)

    logger.info(f"All downloads completed in {download_dir}")
