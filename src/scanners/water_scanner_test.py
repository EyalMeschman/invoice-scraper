import asyncio
import logging
from enum import StrEnum
from pathlib import Path

import pytest
from playwright.async_api import Page

from google_secrets_client import GoogleSecretsClient
from src.scanner_config import Platform, YEAR, get_periods_to_download
from src.utils import Utils


class InvoicePeriod(StrEnum):
    PERIOD_1 = f"1-{YEAR}"  # Jan-Feb
    PERIOD_2 = f"2-{YEAR}"  # Mar-Apr
    PERIOD_3 = f"3-{YEAR}"  # May-Jun
    PERIOD_4 = f"4-{YEAR}"  # Jul-Aug
    PERIOD_5 = f"5-{YEAR}"  # Sep-Oct
    PERIOD_6 = f"6-{YEAR}"  # Nov-Dec


PLATFORM = Platform.MEITAV
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod[period_name] for period_name in get_periods_to_download(PLATFORM)
]


async def download_invoice_by_period(
    page: Page,
    period: InvoicePeriod,
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

    # Wait for the first one to succeed
    done, pending = await asyncio.wait(
        [direct_task, blob_task], return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel the other task
    for task in pending:
        task.cancel()

    # Get the result from the completed task
    pdf_content = None
    for task in done:
        pdf_content = task.result()

    await new_page.close()

    if pdf_content is None:
        raise ValueError(f"Failed to download invoice for period {period.name}")

    save_path = download_dir / f"water_{period}.pdf"
    save_path.write_bytes(pdf_content)

    logger.info(f"Downloaded {period.name} to {save_path}")

    return save_path


@pytest.mark.manual
async def test_meitav_manual_login(
    page: Page,
    logger: logging.Logger,
    google_secrets_client: GoogleSecretsClient,
):
    password = Utils.get_secret_from_google_secrets_client(
        google_secrets_client, "MEITAV_PASSWORD"
    )

    user_id = Utils.get_mandatory_env("JESS_ID")

    url = "https://www.my-meitav.co.il/appartments"
    await page.goto(url)
    await page.get_by_role("button", name="כניסה באמצעות סיסמה").click()
    await page.locator("#pasportNumber").fill(user_id)
    await page.locator("#password").fill(password)
    await page.pause()
    try:
        await page.get_by_role("button", name="כניסה").click()
    # pylint: disable=broad-exception-caught
    except Exception:
        pass
    await page.wait_for_url(url)

    await Utils.record_state(
        page=page, platform=PLATFORM, logger=logger, include_session_storage=True
    )


@pytest.mark.using_state(PLATFORM)
async def test_meitav(
    page: Page,
    logger: logging.Logger,
) -> None:
    url = "https://www.my-meitav.co.il/appartments"
    await page.goto(url)
    await Utils.wait_for_authenticated_page(page=page, url=url, platform=PLATFORM)
    await page.locator("#allInfo").click()

    download_dir = Path(f"downloads/{YEAR}/{PLATFORM}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS_TO_DOWNLOAD:
        await download_invoice_by_period(
            page=page, period=period, download_dir=download_dir, logger=logger
        )

    logger.info(f"All downloads completed in {download_dir}")
