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


PLATFORM = Platform.CHATGPT
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)
]


async def download_invoice_by_period(
    page: Page, period: InvoicePeriod, download_dir: Path, logger: logging.Logger
) -> Path:
    invoice_row = (
        page.get_by_test_id("billing-portal-invoice-row")
        .filter(has_text=period)
        .filter(has_text=str(YEAR))
    )

    async with page.context.expect_page() as new_page_info:
        await invoice_row.click()

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
async def test_meitav_manual_login(
    page: Page,
    logger: logging.Logger,
) -> None:
    username = Utils.get_mandatory_env("CHATGPT_USERNAME")
    password = Utils.get_mandatory_env("CHATGPT_PASSWORD")

    url = "https://chatgpt.com"
    await page.goto(url)
    await page.get_by_role("button", name="Log in").click()
    await page.get_by_role("button", name="Continue with Google").click()
    await page.wait_for_url("https://accounts.google.com/**")
    await page.locator("#identifierId").fill(username)
    await page.keyboard.press("Enter")
    await page.locator('input[name="Passwd"]').fill(password)
    await page.keyboard.press("Enter")
    await page.pause()
    await page.wait_for_url(url)

    await Utils.record_state(
        page=page, platform=PLATFORM, logger=logger, include_session_storage=True
    )


@pytest.mark.using_state(PLATFORM)
async def test_chatgpt(
    page: Page,
    logger: logging.Logger,
) -> None:
    url = "https://chatgpt.com"
    await page.goto(url)
    await page.get_by_test_id("accounts-profile-button").last.click()
    await page.get_by_role("menuitem", name="Settings").click()
    await page.get_by_test_id("account-tab").click()
    payment_section = page.locator('div:has-text("Payment")')
    await payment_section.get_by_role("button", name="Manage").last.click()
    await page.wait_for_url("https://pay.openai.com/**")

    # If downloading more than 3 periods, press "view more"
    if len(PERIODS_TO_DOWNLOAD) > 3:
        await page.get_by_test_id("view-more-button").click()

    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(
            page=page, period=period, download_dir=download_dir, logger=logger
        )

    logger.info(f"All downloads completed in {download_dir}")
