import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from invoice_scraper.config import YEAR, Platform

DownloadFn = Callable[[Any, str, Path, logging.Logger], Coroutine[Any, Any, Path]]


async def run_download_loop(
    page: Any,
    platform: Platform,
    periods: list[str],
    download_fn: DownloadFn,
    logger: logging.Logger,
) -> Path:
    download_dir = Path(f"downloads/{YEAR}/{platform}")
    download_dir.mkdir(parents=True, exist_ok=True)

    for period in periods:
        await download_fn(page, period, download_dir, logger)

    logger.info(f"All downloads completed in {download_dir}")
    return download_dir
