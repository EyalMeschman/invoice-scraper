# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated invoice download system using async Playwright for web scraping Israeli municipal and utility services (Arnona, Water/Meitav). The system uses sophisticated authentication state management with sessionStorage support to maintain login sessions across runs.

## Development Commands

### Install Dependencies
```bash
uv sync
```

### Install Playwright Browsers
```bash
uv run playwright install chromium
```

### Run Tests

Run a specific test:
```bash
uv run pytest src/scanners/arnona_scanner_test.py::test_arnona -v
uv run pytest src/scanners/water_scanner_test.py::test_meitav -v
```

Run manual login tests (requires user interaction):
```bash
uv run pytest src/scanners/water_scanner_test.py::test_meitav_manual_login -v -m manual
```

Run all manual tests:
```bash
uv run pytest -m manual -v
```

### Linting
```bash
uv run pylint src/
```

## Architecture

### Authentication State Management

The core innovation is a custom authentication state system that extends Playwright's built-in `storage_state()`:

**Standard Playwright state (cookies + localStorage):**
- Saved via `await page.context.storage_state(path=state_file)`
- Loaded via `context = await browser.new_context(storage_state=state_file)`

**Custom sessionStorage extension:**
- Many sites (e.g., Meitav) store auth tokens in sessionStorage, which Playwright doesn't capture
- `Utils._append_session_storage_to_state()` captures sessionStorage via JavaScript evaluation and appends to state JSON
- `page` fixture in conftest.py:39 automatically injects sessionStorage when `@pytest.mark.using_state(platform)` is used
- State file structure includes custom `origins[].sessionStorage` array alongside standard fields

### Pytest Markers & Fixtures

**Custom markers (defined in conftest.py:93-98):**
- `@pytest.mark.manual` - Tests requiring manual user interaction (login with captcha/2FA)
- `@pytest.mark.using_state(platform)` - Tests that load saved authentication state for the given platform

**Key fixtures:**
- `page` fixture (conftest.py:39) - Creates browser page, handles state loading, injects sessionStorage
- `browser` fixture (conftest.py:31) - Creates Chromium browser instance with `headless=False`
- `logger` fixture (conftest.py:21) - Session-scoped logger
- `google_secrets_client` fixture (conftest.py:26) - Access to Google Secret Manager

### Browser Fingerprinting

`Utils.cover_footprints()` (src/utils.py:147) injects `FINGERPRINT_SHIM` script to mask automation:
- Spoofs navigator properties (platform, language, webdriver)
- Patches Canvas/WebGL fingerprinting methods
- Deterministic perturbation with seeded randomness

### Concurrent Download Racing

For blob URL downloads (water_scanner_test.py:68-116), two methods race concurrently:
1. `try_direct_download()` - Expects Playwright download event
2. `try_blob_download()` - Fetches blob URL content via JavaScript

Uses `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` to take whichever succeeds first, eliminating timeout waits.

### Scanner Pattern

Each scanner in `src/scanners/` follows a two-test pattern:

1. **Manual login test** (marked `@pytest.mark.manual`):
   - Opens browser non-headless
   - Fills credentials
   - Calls `page.pause()` for manual intervention (captcha, 2FA)
   - Saves state with `Utils.record_state(..., include_session_storage=True)`

2. **Regular test** (marked `@pytest.mark.using_state(platform)`):
   - Automatically loads saved state via fixture
   - Verifies authentication with `Utils.wait_for_authenticated_page()`
   - Downloads invoices

### Environment & Secrets

Configuration loaded via dotenv (conftest.py:16-17):
- `.env.defaults` loaded first
- `.env` overrides defaults

Secrets retrieved via `GoogleSecretsClient` from Google Secret Manager:
- Requires `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS_PATH` env vars
- Use `Utils.get_secret_from_google_secrets_client(google_secrets_client, "SECRET_NAME")`

### Utils Module Organization

`src/utils.py` contains reusable utilities:
- **State management**: `record_state()`, `_append_session_storage_to_state()`
- **Authentication helpers**: `wait_for_authenticated_page()`, `wait_for_authenticated_selector()`
- **Selector utilities**: `wait_for_selector()`, `click_selector_if_exists()`, `wait_for_locator()`
- **Download utilities**: `download_pdf_from_blob_url()`
- **Security**: `cover_footprints()`, `get_totp()`
- **Environment**: `get_mandatory_env()`

### File Structure Conventions

```
downloads/{YEAR}/{platform}/       # Downloaded PDFs organized by year and platform
playwright/.auth/{platform}.json   # Saved authentication states (git-ignored)
src/scanners/{platform}_scanner_test.py  # Scanner implementations
```

## Pytest Configuration

In `pyproject.toml`:
- `asyncio_mode = "auto"` - Enables async test functions without explicit decorators
- `asyncio_default_fixture_loop_scope = "function"` - Each test gets its own event loop

## Important Notes

- Browser always runs with `headless=False` for debugging and manual login tests
- SessionStorage injection happens via `page.goto(origin)` then JavaScript evaluation (conftest.py:78-85)
- State files contain sensitive auth tokens - ensure they're git-ignored
- When authentication expires, re-run the manual login test to refresh state
- TOTP support available via `Utils.get_totp(secret)` using pyotp library
