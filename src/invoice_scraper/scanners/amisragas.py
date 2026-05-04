import logging
from pathlib import Path

from playwright.async_api import Page

from invoice_scraper.config import YEAR, Platform

PLATFORM = Platform.AMISRAGAS


async def download_invoice_by_period(page: Page, period: str, download_dir: Path, logger: logging.Logger) -> Path:
    card = page.locator(f".vue-contracts__invoice:has-text('{period}/{YEAR}')").first
    download_button = card.locator(".vue-contracts__invoice-form-curr button")

    async with page.expect_download() as download_info:
        await download_button.click()
    download = await download_info.value

    save_path = download_dir / f"חשמל {period}.pdf"
    await download.save_as(save_path)

    logger.info(f"Downloaded {period} to {save_path}")
    return save_path
