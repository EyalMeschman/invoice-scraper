import logging
from pathlib import Path

from playwright.async_api import Page

from invoice_scraper.config import Platform
from invoice_scraper.utils import Utils

PLATFORM = Platform.PARTNER


async def download_invoice_by_period(page: Page, period: str, download_dir: Path, logger: logging.Logger) -> Path:
    link = page.locator('[role="group"]').filter(has_text=period).first
    await link.click()

    async with page.context.expect_page() as new_page_info:
        await page.get_by_role("button", name="לחשבונית חתומה דיגיטלית").click()
    new_page: Page = await new_page_info.value
    await new_page.wait_for_load_state()

    pdf_content = await Utils.blob_download_with_timeout(page, new_page)

    save_path = download_dir / f"{PLATFORM}_{period}.pdf".replace(" ", "_")
    save_path.write_bytes(pdf_content)

    logger.info(f"Downloaded {period} to {save_path}")
    await new_page.close()

    return save_path
