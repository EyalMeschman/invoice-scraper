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
uv run pytest tests/scanners/test_arnona.py::test_arnona -v
uv run pytest tests/scanners/test_meitav.py::test_meitav -v
```

Run manual login tests (requires user interaction):

```bash
uv run pytest tests/scanners/test_meitav.py::test_meitav_manual_login -v -m manual
```

Run all manual tests:

```bash
uv run pytest -m manual -v
```

### Linting

```bash
uv run ruff check src/
```

## Architecture

### Package Layout

```
src/invoice_scraper/           # Main package (on PYTHONPATH via pyproject.toml)
  config.py                    # Platform enum, period config, env loading
  logger.py                    # Centralized logging setup
  secrets_client.py            # Google Secret Manager wrapper
  utils.py                     # Playwright helpers, download utilities, auth
  scanners/
    base.py                    # Shared download loop helper
    arnona.py                  # Scanner implementations (one per platform)
    ...
tests/
  conftest.py                  # Fixtures: browser, page, logger, secrets
  scanners/
    test_arnona.py             # Test wrappers (one per platform)
    ...
```

### Authentication State Management

The core innovation is a custom authentication state system that extends Playwright's built-in `storage_state()`:

**Standard Playwright state (cookies + localStorage):**

- Saved via `await page.context.storage_state(path=state_file)`
- Loaded via `context = await browser.new_context(storage_state=state_file)`

**Custom sessionStorage extension:**

- Many sites (e.g., Meitav) store auth tokens in sessionStorage, which Playwright doesn't capture
- `Utils._append_session_storage_to_state()` captures sessionStorage via JavaScript evaluation and appends to state JSON
- `page` fixture in `tests/conftest.py` automatically injects sessionStorage when `@pytest.mark.using_state(platform)` is used
- State file structure includes custom `origins[].sessionStorage` array alongside standard fields

### Pytest Markers & Fixtures

**Custom markers (defined in `tests/conftest.py`):**

- `@pytest.mark.manual` - Tests requiring manual user interaction (login with captcha/2FA)
- `@pytest.mark.using_state(platform)` - Tests that load saved authentication state for the given platform

**Key fixtures:**

- `page` fixture - Creates browser page, handles state loading, injects sessionStorage
- `browser` fixture - Creates Chromium browser instance with `headless=False`
- `logger` fixture - Session-scoped logger
- `google_secrets_client` fixture - Access to Google Secret Manager

### Browser Fingerprinting

`Utils.cover_footprints()` injects `FINGERPRINT_SHIM` script to mask automation:

- Spoofs navigator properties (platform, language, webdriver)
- Patches Canvas/WebGL fingerprinting methods
- Deterministic perturbation with seeded randomness

### Concurrent Download Racing

For blob URL downloads (meitav scanner), two methods race concurrently:

1. `Utils.direct_download()` - Expects Playwright download event
2. `Utils.blob_download_with_timeout()` - Fetches blob URL content via JavaScript

Uses `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` to take whichever succeeds first, eliminating timeout waits.

### Scanner Pattern

Each scanner is split into implementation (`src/invoice_scraper/scanners/`) and test (`tests/scanners/`).

**Implementation** defines:

- `PLATFORM` constant
- `download_invoice_by_period(page, period, download_dir, logger)` - platform-specific download logic

**Tests** follow a two-test pattern:

1. **Manual login test** (marked `@pytest.mark.manual`):
   - Opens browser non-headless
   - Fills credentials
   - Calls `page.pause()` for manual intervention (captcha, 2FA)
   - Saves state with `Utils.record_state(..., include_session_storage=True)`

2. **Regular test** (marked `@pytest.mark.using_state(platform)`):
   - Automatically loads saved state via fixture
   - Verifies authentication with `Utils.wait_for_authenticated_page()`
   - Calls `run_download_loop()` from `scanners/base.py` with platform-specific download function

### Configuration

**Period configuration** in `config.py`:

- `PERIOD_VALUES` maps each platform to its period label strings
- `get_periods_to_download(platform)` returns the slice of periods based on `PERIODS_CONFIG`

**Environment** loaded via `load_config()` in `config.py` (called explicitly from `tests/conftest.py`):

- `.env.defaults` loaded first
- `.env` overrides defaults

Secrets retrieved via `GoogleSecretsClient` from Google Secret Manager:

- Requires `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS_PATH` env vars
- Use `Utils.get_secret_from_google_secrets_client(google_secrets_client, "SECRET_NAME")`

### File Structure Conventions

```
downloads/{YEAR}/{platform}/       # Downloaded PDFs organized by year and platform
playwright/.auth/{platform}.json   # Saved authentication states (git-ignored)
src/invoice_scraper/scanners/      # Scanner implementations
tests/scanners/                    # Test wrappers
```

## Pytest Configuration

In `pyproject.toml`:

- `asyncio_mode = "auto"` - Enables async test functions without explicit decorators
- `asyncio_default_fixture_loop_scope = "function"` - Each test gets its own event loop
- `testpaths = ["tests"]` - Test discovery root
- `pythonpath = ["src"]` - Makes `invoice_scraper` importable

## Important Notes

- Browser always runs with `headless=False` for debugging and manual login tests
- SessionStorage injection happens via `context.add_init_script()` to run before page JS
- State files contain sensitive auth tokens - ensure they're git-ignored
- When authentication expires, re-run the manual login test to refresh state
- TOTP support available via `Utils.get_totp(secret)` using pyotp library
