import logging
from enum import StrEnum
from pathlib import Path

import pytest
from playwright.async_api import Page

from src.scanner_config import YEAR, get_periods_to_download
from src.utils import Utils


class InvoicePeriod(StrEnum):
    PERIOD_1 = f"ינואר {YEAR}"  # January
    PERIOD_2 = f"פברואר {YEAR}"  # February
    PERIOD_3 = f"מרץ {YEAR}"  # March
    PERIOD_4 = f"אפריל {YEAR}"  # April
    PERIOD_5 = f"מאי {YEAR}"  # May
    PERIOD_6 = f"יוני {YEAR}"  # June
    PERIOD_7 = f"יולי {YEAR}"  # July
    PERIOD_8 = f"אוגוסט {YEAR}"  # August
    PERIOD_9 = f"ספטמבר {YEAR}"  # September
    PERIOD_10 = f"אוקטובר {YEAR}"  # October
    PERIOD_11 = f"נובמבר {YEAR}"  # November
    PERIOD_12 = f"דצמבר {YEAR}"  # December


PLATFORM = "partner"
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)
]


async def download_invoice_by_period(
    page: Page, period: InvoicePeriod, download_dir: Path, logger: logging.Logger
) -> Path:
    link = page.locator('[role="group"]').filter(has_text=period).first
    await link.click()

    # Click on the link and handle the new page
    async with page.context.expect_page() as new_page_info:
        await page.get_by_role("button", name="לחשבונית חתומה דיגיטלית").click()
    new_page: Page = await new_page_info.value
    await new_page.wait_for_load_state()

    # # Get the PDF URL and download it using the page's context
    # blob_url = new_page.url
    pdf_content = await Utils.blob_download_with_timeout(page, new_page)

    save_path = download_dir / f"{PLATFORM}_{period}.pdf".replace(" ", "_")
    save_path.write_bytes(pdf_content)

    logger.info(f"Downloaded {period.name} to {save_path}")
    await new_page.close()

    return save_path


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
    await page.get_by_role("button", name="המשך").click()
    await page.wait_for_url(url)

    await Utils.record_state(page=page, platform=PLATFORM, logger=logger)


@pytest.mark.using_state(PLATFORM)
async def test_partner(
    page: Page,
    logger: logging.Logger,
) -> None:
    url = "https://www.partner.co.il/n/mypartner/invoice"
    await page.goto(url)
    await Utils.wait_for_authenticated_page(page=page, url=url, platform=PLATFORM)
    await page.get_by_role("button", name="לא, תודה").click()

    # Create downloads directory
    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(
            page=page, period=period, download_dir=download_dir, logger=logger
        )

    logger.info(f"All downloads completed in {download_dir}")
