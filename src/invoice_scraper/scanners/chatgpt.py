import logging
from pathlib import Path

from playwright.async_api import Page

from invoice_scraper.config import YEAR, Platform

PLATFORM = Platform.CHATGPT


async def download_invoice_by_period(page: Page, period: str, download_dir: Path, logger: logging.Logger) -> Path:
    invoice_row = page.get_by_test_id("billing-portal-invoice-row").filter(has_text=period).filter(has_text=str(YEAR))

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

    logger.info(f"Downloaded {period} to {save_path}")

    return save_path
