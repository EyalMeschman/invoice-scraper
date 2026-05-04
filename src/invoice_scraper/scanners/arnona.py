import logging
from pathlib import Path

from playwright.async_api import Page

from invoice_scraper.config import YEAR, Platform
from invoice_scraper.utils import Utils

PLATFORM = Platform.ARNONA


async def download_invoice_by_period(page: Page, period: str, download_dir: Path, logger: logging.Logger) -> Path:
    row = page.locator(f"table#datatable tbody tr:has-text('{period}')").first
    link_cell = row.locator("td").first

    async with page.context.expect_page() as new_page_info:
        await link_cell.click()
    new_page: Page = await new_page_info.value
    await new_page.wait_for_load_state()

    blob_url = new_page.url
    pdf_content = await Utils.download_pdf_from_blob_url(new_page, blob_url)

    save_path = download_dir / f"{period}_{YEAR}.pdf"
    save_path.write_bytes(pdf_content)

    logger.info(f"Downloaded {period} to {save_path}")
    await new_page.close()

    return save_path
