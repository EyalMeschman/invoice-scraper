import asyncio
import logging
from pathlib import Path

from playwright.async_api import Page

from invoice_scraper.config import Platform
from invoice_scraper.utils import Utils

PLATFORM = Platform.MEITAV


async def download_invoice_by_period(
    page: Page,
    period: str,
    download_dir: Path,
    logger: logging.Logger,
) -> Path:
    row = page.locator(f"tr:has-text('{period}')").first
    link = row.locator("a").filter(has_text="חשבונית").first

    async with page.context.expect_page() as new_page_info:
        await link.click()
    new_page = await new_page_info.value

    # Race both download methods concurrently
    direct_task = asyncio.create_task(Utils.direct_download(new_page, download_dir))
    blob_task = asyncio.create_task(Utils.blob_download_with_timeout(page, new_page))

    done, pending = await asyncio.wait([direct_task, blob_task], return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()

    pdf_content = None
    for task in done:
        pdf_content = task.result()

    await new_page.close()

    if pdf_content is None:
        raise ValueError(f"Failed to download invoice for period {period}")

    save_path = download_dir / f"water_{period}.pdf"
    save_path.write_bytes(pdf_content)

    logger.info(f"Downloaded {period} to {save_path}")

    return save_path
