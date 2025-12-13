import logging
from enum import StrEnum
from pathlib import Path

from playwright.async_api import Page, Locator

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


PLATFORM = Platform.GOOGLE_WORKSPACE
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)
]


async def download_invoice_by_period(
    page: Page, period: InvoicePeriod, download_dir: Path, logger: logging.Logger
) -> Path:
    iframe_frame: Locator = page.locator('iframe[name^="embeddedBilling"]')

    content_frame = iframe_frame.content_frame
    if content_frame is None:
        raise ValueError("Could not find billing iframe")

    period_heading = content_frame.get_by_role("heading", name=f"{period} 1")
    await period_heading.wait_for()

    is_expanded = await period_heading.get_attribute("aria-expanded") == "true"

    if not is_expanded:
        await period_heading.click()
        await page.wait_for_timeout(500)

    section_id = await period_heading.get_attribute("aria-controls")
    if not section_id:
        raise ValueError(f"Heading for {period} has no aria-controls attribute")

    period_section = content_frame.locator(f"#{section_id}")
    pdf_invoice_button = period_section.get_by_role("button", name="(Created:").first
    await pdf_invoice_button.click()

    async with page.expect_download() as download_info:
        await content_frame.get_by_role("menuitem", name="Download").click()

    download = await download_info.value

    save_path = download_dir / f"{PLATFORM}_{period}_{YEAR}.pdf"
    await download.save_as(save_path)

    logger.info(f"Downloaded {period.name} to {save_path}")

    return save_path


async def test_google_workspace(
    page: Page,
    logger: logging.Logger,
) -> None:
    username = Utils.get_mandatory_env("GOOGLE_WORKSPACE_USERNAME")
    password = Utils.get_mandatory_env("GOOGLE_WORKSPACE_PASSWORD")

    url = "https://admin.google.com/u/7/ac/billing/accounts/w2D_un6NA_-1iXkWulbFKw/transactions?hl=en"
    await page.goto(url)
    await page.locator("#identifierId").fill(username)
    await page.keyboard.press("Enter")
    await page.locator('input[name="Passwd"]').fill(password)
    await page.keyboard.press("Enter")
    await page.wait_for_url("**/transactions?**")

    # If downloading more than 2 periods, change filter to "This year"
    if len(PERIODS_TO_DOWNLOAD) > 2:
        iframe_frame: Locator = page.locator('iframe[name^="embeddedBilling"]')
        content_frame = iframe_frame.content_frame
        if not content_frame:
            raise ValueError("Could not find billing iframe")

        await content_frame.get_by_role("listbox").filter(
            has_text="Last 3 months"
        ).click()
        await content_frame.get_by_role("menuitem", name="This year").click()
        await content_frame.get_by_role("heading", name="Jan 1").wait_for()

    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(
            page=page, period=period, download_dir=download_dir, logger=logger
        )

    logger.info(f"All downloads completed in {download_dir}")
