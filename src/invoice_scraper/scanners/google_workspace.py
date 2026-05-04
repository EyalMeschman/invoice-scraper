import logging
from pathlib import Path

from playwright.async_api import Locator, Page

from invoice_scraper.config import YEAR, Platform

PLATFORM = Platform.GOOGLE_WORKSPACE


async def download_invoice_by_period(page: Page, period: str, download_dir: Path, logger: logging.Logger) -> Path:
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

    logger.info(f"Downloaded {period} to {save_path}")

    return save_path
