import logging
from enum import StrEnum
from pathlib import Path

from playwright.async_api import Page

from google_secrets_client import GoogleSecretsClient
from src.scanner_config import Platform, YEAR, get_periods_to_download
from src.utils import Utils


class InvoicePeriod(StrEnum):
    PERIOD_1 = "ארנונה תקופתי 1"  # Jan-Feb (+ Annual)
    PERIOD_2 = "ארנונה תקופתי 2"  # Mar-Apr
    PERIOD_3 = "ארנונה תקופתי 3"  # May-Jun
    PERIOD_4 = "ארנונה תקופתי 4"  # Jul-Aug
    PERIOD_5 = "ארנונה תקופתי 5"  # Sep-Oct
    PERIOD_6 = "ארנונה תקופתי 6"  # Nov-Dec


PLATFORM = Platform.ARNONA
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)
]


async def download_invoice_by_period(
    page: Page, period: InvoicePeriod, download_dir: Path, logger: logging.Logger
) -> Path:
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


async def test_arnona(
    page: Page,
    logger: logging.Logger,
    google_secrets_client: GoogleSecretsClient,
) -> None:
    password = Utils.get_secret_from_google_secrets_client(
        google_secrets_client, "ARNONA_PASSWORD"
    )

    user_id = Utils.get_mandatory_env("DEFAULT_ID")

    url = "https://city4u.co.il/PortalServicesSite/city4u/279000/waterDocuments"
    await page.goto(url)
    await page.get_by_role("button", name="כניסה לחשבון").click()
    await page.locator("#UserName").click()
    await page.locator("#UserName").fill(user_id)
    await page.locator("#Password").click()
    await page.locator("#Password").fill(password)
    await page.get_by_role("button", name="כניסה לחשבון").click()
    await page.wait_for_selector("div#breadcrumbs")
    await page.goto(url)
    await page.wait_for_selector("table#datatable")

    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(page, period, download_dir, logger)

    logger.info(f"All downloads completed in {download_dir}")
