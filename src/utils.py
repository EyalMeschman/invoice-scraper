import asyncio
import base64
import json
import logging
import os
from pathlib import Path

import pyotp
from playwright.async_api import BrowserContext, Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from google_secrets_client import GoogleSecretsClient


class RulesNotFoundError(Exception):
    """Exception raised when the url provided does not match any rules.

    Attributes:
        url -- the url that didn't match any rules
    """

    def __init__(self, url: str):
        self.url = url
        super().__init__(f"No rules found for URL: {self.url}")


class CookieExpiredError(Exception):
    """Exception raised when the loaded cookies are expired.

    Attributes:
        domain - the site for which the cookies expired.
    """

    def __init__(self, domain: str):
        self.domain = domain
        super().__init__(f"Authentication cookies expired for: {self.domain}")


class Utils:
    @staticmethod
    def cover_footprints(context: BrowserContext) -> None:
        context.add_init_script(FINGERPRINT_SHIM)

    @staticmethod
    def get_mandatory_env(key: str) -> str:
        value = os.getenv(key)

        if not value:
            raise OSError(f"{key} env var is missing")

        return value

    @staticmethod
    def get_secret_from_google_secrets_client(
        google_secrets_client: GoogleSecretsClient,
        secret_name: str,
        version: str = "latest",
    ) -> str:
        return google_secrets_client.get_secret(secret_name, version)

    @staticmethod
    async def record_state(
        page: Page,
        platform: str,
        logger: logging.Logger,
        include_session_storage: bool = False,
    ):
        path = "playwright/.auth"
        full_path = os.path.join(path, f"{platform}.json")

        if not os.path.exists(path):
            os.makedirs(path)

        # Save standard storage state (cookies + localStorage)
        await page.context.storage_state(path=full_path)

        # Optionally save sessionStorage if requested
        if include_session_storage:
            await Utils._append_session_storage_to_state(page, full_path, logger)

        logger.info(f"Successfully saved state for {platform}, path: {full_path}")

    @staticmethod
    async def _append_session_storage_to_state(
        page: Page, state_file_path: str, logger: logging.Logger
    ):
        """
        Private helper method to capture sessionStorage and append it to an existing state file.
        """
        # Capture sessionStorage from the page
        session_storage = await page.evaluate(
            """() => {
            const items = {};
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                items[key] = sessionStorage.getItem(key);
            }
            return items;
        }"""
        )

        if not session_storage:
            logger.warning("No sessionStorage found to save")
            return

        # Load the existing state file
        with open(state_file_path, "r", encoding="utf-8") as file:
            state = json.load(file)

        # Add sessionStorage to the appropriate origin
        origin = page.url.split("/")[0] + "//" + page.url.split("/")[2]
        origin_found = False

        for origin_data in state.get("origins", []):
            if origin_data["origin"] == origin:
                origin_data["sessionStorage"] = [
                    {"name": k, "value": v} for k, v in session_storage.items()
                ]
                origin_found = True
                break

        if not origin_found:
            state.setdefault("origins", []).append(
                {
                    "origin": origin,
                    "sessionStorage": [
                        {"name": k, "value": v} for k, v in session_storage.items()
                    ],
                }
            )

        # Save back with sessionStorage included
        with open(state_file_path, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

        logger.info("Successfully appended sessionStorage to state file")

    @staticmethod
    def get_totp(secret: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.now()

    @staticmethod
    async def wait_for_authenticated_page(
        page: Page, url: str, platform: str, timeout=5000
    ):
        try:
            await page.wait_for_url(url, timeout=timeout)
        except PlaywrightTimeoutError as exc:
            raise CookieExpiredError(platform) from exc

    @staticmethod
    async def wait_for_authenticated_selector(
        page: Page, selector: str, should_exist: bool, platform: str, timeout=5000
    ):
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            if not should_exist:
                raise CookieExpiredError(platform)
        except PlaywrightTimeoutError as exc:
            if not should_exist:
                return
            raise CookieExpiredError(platform) from exc

    @staticmethod
    async def wait_for_selector(
        page: Page, selector: str, timeout=3000
    ) -> Locator | None:
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            locator = page.locator(selector)
            if await locator.count() > 0:
                return locator
            return None
        except PlaywrightTimeoutError:
            return None

    @staticmethod
    async def click_selector_if_exists(page: Page, selector: str, timeout=3000):
        locator = await Utils.wait_for_selector(page, selector, timeout)
        if locator:
            await locator.click()

    @staticmethod
    async def wait_for_locator(locator: Locator, timeout=3000) -> Locator | None:
        try:
            await locator.wait_for(timeout=timeout)
            if await locator.count() > 0:
                return locator
            return None
        except PlaywrightTimeoutError:
            return None

    @staticmethod
    async def download_pdf_from_blob_url(page: Page, blob_url: str) -> bytes:
        pdf_base64 = await page.evaluate(
            """async (blobUrl) => {
            const response = await fetch(blobUrl);
            const blob = await response.blob();
            const reader = new FileReader();
            return new Promise((resolve) => {
                reader.onloadend = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(blob);
            });
        }""",
            blob_url,
        )

        return base64.b64decode(pdf_base64)

    @staticmethod
    async def direct_download(
        new_page: Page,
        download_dir: Path,
        timeout: int = 5000,
    ) -> bytes:
        async with new_page.expect_download(timeout=timeout) as download_info:
            pass  # Download triggers automatically from page load
        download = await download_info.value

        temp_path = download_dir / "temp_invoice.pdf"
        await download.save_as(temp_path)
        pdf_content = temp_path.read_bytes()
        temp_path.unlink()

        return pdf_content

    @staticmethod
    async def blob_download_with_timeout(
        page: Page, new_page: Page, timeout: int = 10000
    ) -> bytes:
        # Wait for the page to load the blob URL
        start_wait = asyncio.get_event_loop().time()
        while not new_page.url.startswith("blob:"):
            if (asyncio.get_event_loop().time() - start_wait) * 1000 > timeout:
                raise TimeoutError("Timeout waiting for blob URL to load")
            await new_page.reload()
            await asyncio.sleep(1)

        # Download from blob URL using the original page context
        blob_url = new_page.url
        return await Utils.download_pdf_from_blob_url(page, blob_url)


FINGERPRINT_SHIM = r"""
(() => {
  // --- helpers ---
  const defineGetter = (obj, prop, value) => {
    try {
      Object.defineProperty(obj, prop, { get: () => value, configurable: true });
    } catch {}
  };

  // --- Navigator: language(s), platform, webdriver, concurrency ---
  defineGetter(Navigator.prototype, "hardwareConcurrency", 8);
  defineGetter(Navigator.prototype, "language", "en-GB");
  defineGetter(Navigator.prototype, "languages", ["en-GB", "en"]);
  defineGetter(Navigator.prototype, "platform", "MacIntel");
  defineGetter(Navigator.prototype, "webdriver", undefined);

  // --- Permissions: avoid Illegal return + keep shape predictable ---
  if (navigator.permissions && navigator.permissions.query) {
    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (parameters) => {
      try {
        if (parameters && parameters.name === "notifications") {
          // PermissionStatus-like object
          return Promise.resolve({
            state: Notification.permission,
            onchange: null,
          });
        }
      } catch {}
      return originalQuery(parameters);
    };
  }

  // --- Canvas: deterministic, lightweight perturbation ---
  // NOTE: This is for reproducible testing. It intentionally avoids heavy per-pixel loops.
  const seed = 1337; // make this configurable per test run if you want
  let s = seed >>> 0;
  const rand = () => (s = (s * 1664525 + 1013904223) >>> 0) / 2**32;

  const patchCanvasExport = (name) => {
    const orig = HTMLCanvasElement.prototype[name];
    if (!orig) return;

    Object.defineProperty(HTMLCanvasElement.prototype, name, {
      value: function(...args) {
        try {
          const ctx = this.getContext("2d");
          if (ctx) {
            // tiny, deterministic 1px shift in a corner (minimal impact, low cost)
            const w = this.width | 0, h = this.height | 0;
            if (w > 0 && h > 0) {
              const x = (rand() * Math.min(8, w)) | 0;
              const y = (rand() * Math.min(8, h)) | 0;
              const img = ctx.getImageData(x, y, 1, 1);
              // slight clamped change
              img.data[0] = (img.data[0] + 1) & 255;
              ctx.putImageData(img, x, y);
            }
          }
        } catch {
          // ignore tainted canvas / security errors
        }
        return orig.apply(this, args);
      },
      configurable: true
    });
  };

  patchCanvasExport("toDataURL");
  patchCanvasExport("toBlob");

  // --- WebGL: patch safely (WebGL1 + WebGL2) ---
  const patchWebGL = (proto) => {
    if (!proto || !proto.getParameter) return;
    const origGetParameter = proto.getParameter;

    Object.defineProperty(proto, "getParameter", {
      value: function(parameter) {
        // 37445/37446 are often used, but many scripts use WEBGL_debug_renderer_info constants.
        // We only override known IDs and otherwise call through.
        if (parameter === 37445) return "ANGLE (Intel, Intel(R) Iris(TM) Graphics, OpenGL 4.1)";
        if (parameter === 37446) return "Google Inc.";
        return origGetParameter.call(this, parameter);
      },
      configurable: true
    });

    const origGetExtension = proto.getExtension;
    if (origGetExtension) {
      Object.defineProperty(proto, "getExtension", {
        value: function(name) {
          const ext = origGetExtension.call(this, name);
          if (name === "WEBGL_debug_renderer_info" && ext) {
            // keep ext but ensure constants exist
            return ext;
          }
          return ext;
        },
        configurable: true
      });
    }
  };

  patchWebGL(WebGLRenderingContext && WebGLRenderingContext.prototype);
  patchWebGL(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
})();
"""
