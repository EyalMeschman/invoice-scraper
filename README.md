# Invoice Scraper

Automated invoice download system using Playwright for web scraping and authentication state management.

## Overview

This project automates the downloading of invoices from various Israeli municipal and utility services:

- **Arnona** (Municipal Tax) - from city4u.co.il
- **Water** (Meitav) - from my-meitav.co.il

The system uses async Playwright for concurrent operations and includes sophisticated state management to handle authentication sessions.

## Features

- ✅ **Async/Await Architecture** - Full async support for concurrent downloads
- ✅ **State Management** - Saves authentication state (cookies, localStorage, sessionStorage) to skip login
- ✅ **Concurrent Download Racing** - Handles both blob URLs and direct downloads simultaneously
- ✅ **SessionStorage Support** - Custom implementation for sites requiring sessionStorage authentication
- ✅ **Manual Login Tests** - Save authentication state once, reuse untill token expires

## Project Structure

```
invoice-scraper/
├── src/
│   ├── scanners/
│   │   ├── arnona_scanner_test.py   # Arnona (city tax) automation (For example)
│   └── utils.py                     # Shared utilities (state management, helpers)
├── playwright/.auth/                # Saved authentication states
│   ├── arnona.json                  # Arnona session state (For example)
├── downloads/                       # Downloaded invoices organized by year/service
├── conftest.py                      # Pytest fixtures and configuration
└── README.md
```

## Installation

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Install Playwright browsers:**

   ```bash
   uv run playwright install chromium
   ```

3. **Set up environment variables:**
   Create a `.env` file with required credentials:
   ```env
   DEFAULT_ID=your_id
   JESS_ID=your_id
   ```

## How It Works

### Authentication State Management

The project uses a sophisticated state management system to avoid repeated logins:

1. **Cookies & localStorage** - Standard Playwright `storage_state()`
2. **SessionStorage** - Custom implementation (Playwright doesn't support this natively)

#### Why SessionStorage Matters

Some sites (like Meitav) store authentication tokens in sessionStorage:

```javascript
sessionStorage.setItem(
  "currentUser",
  JSON.stringify({
    access_token: "...",
    token_type: "bearer",
    expires_in: 14399,
  })
);
```

Our custom solution:

- **Saves**: `Utils.record_state(page, platform, logger, include_session_storage=True)`
- **Loads**: Automatically injected by the `page` fixture when using `@pytest.mark.using_state(platform)`

### Concurrent Download Racing

For blob URL downloads, the system races two methods simultaneously:

1. **Direct Download** - Expects a download event
2. **Blob URL Fetch** - Fetches blob content via JavaScript

Whichever succeeds first wins, eliminating timeout waits!

## Example Running Tests

### Arnona (No Manual Login Required)

Arnona doesn't require state management - just run the test directly:

```bash
uv run pytest src/scanners/arnona_scanner_test.py::test_arnona -v
```

**What it does:**

1. Navigates to city4u.co.il
2. Logs in with credentials from `.env`
3. Downloads invoices for specified periods
4. Saves PDFs to `downloads/{YEAR}/arnona/`

### Meitav - Manual Login (First Time Setup)

**Run this ONCE to save authentication state:**

```bash
uv run pytest src/scanners/water_scanner_test.py::test_meitav_manual_login -v -m manual
```

**What it does:**

1. Opens browser (non-headless)
2. Navigates to my-meitav.co.il
3. Enters credentials
4. **PAUSES** - You manually complete login (handle captcha, 2FA, etc.)
5. Saves complete state including sessionStorage to `playwright/.auth/meitav.json`

**Important:** The test includes `page.pause()` - the browser will pause for you to complete the login manually. Press "Resume" in the Playwright inspector once finished with captcha.

### Meitav - Regular Test (Uses Saved State)

**Run this for automated downloads using saved state:**

```bash
uv run pytest src/scanners/water_scanner_test.py::test_meitav -v
```

**What it does:**

1. Loads saved state from `playwright/.auth/meitav.json`
2. Injects sessionStorage items (`currentUser`, `userName`)
3. Navigates to my-meitav.co.il - **already logged in!**
4. Downloads invoices concurrently for specified periods
5. Saves PDFs to `downloads/{YEAR}/meitav/`

**Note:** If the authentication token expires, re-run the manual login test.

## Test Markers

The project uses pytest markers for different test types:

- `@pytest.mark.manual` - Tests that require manual interaction (login)
- `@pytest.mark.using_state(platform)` - Tests that load saved authentication state

## Configuration

### Periods to Download

Edit the test files to configure which periods to download:

**Arnona:**

```python
PERIODS_TO_DOWNLOAD = [
    InvoicePeriod.PERIOD_4,  # Jul-Aug
    InvoicePeriod.PERIOD_5,  # Sep-Oct
    InvoicePeriod.PERIOD_6,  # Nov-Dec
]
```

## Utils Class Reference

### State Management

```python
# Save state with sessionStorage (for sites like Meitav)
await Utils.record_state(page, platform, logger, include_session_storage=True)

# Save state without sessionStorage (standard)
await Utils.record_state(page, platform, logger)
```

## Troubleshooting

### "Authentication failed - still on login page"

The saved state has expired. Re-run the manual login test:

```bash
uv run pytest src/scanners/water_scanner_test.py::test_meitav_manual_login -v -m manual
```

### "State file not found"

You need to run the manual login test first to create the state file.

### Downloads failing with timeout

Check if the site structure has changed. The selectors may need updating.

### Blob URL downloads hanging

The concurrent racing system should handle this, but if issues persist, check the browser console for errors.

## Architecture Decisions

### Why Async?

1. **Concurrent Downloads** - Download multiple invoices simultaneously
2. **Racing Downloads** - Try blob and direct download methods at the same time
3. **Better Resource Usage** - Non-blocking I/O operations

### Why Custom SessionStorage Handling?

Playwright's `storage_state()` only captures:

- ✅ Cookies
- ✅ localStorage
- ❌ sessionStorage (not supported)

Many modern sites (like Meitav) store auth tokens in sessionStorage, so we built a custom solution:

- `Utils._append_session_storage_to_state()` - Captures and saves sessionStorage
- `page` fixture in conftest.py - Injects sessionStorage on page load

### Inspecting Saved State

Check the saved authentication state:

```bash
cat playwright/.auth/meitav.json
```

Look for:

- `cookies` array - Authentication cookies
- `origins[].localStorage` - localStorage items
- `origins[].sessionStorage` - Custom sessionStorage items

## Contributing

When adding new scanners:

1. **Create manual login test when needed:**

   - Mark with `@pytest.mark.manual`
   - Include `page.pause()` for manual completion
   - Save state with `include_session_storage=True` if needed

2. **Determine if sessionStorage is needed:**

   - If regular test after manual test logs you in, you don't need it

3. **Create regular test:**
   - Mark with `@pytest.mark.using_state(platform)` if needed
   - The fixture will handle state loading automatically

## License

This project is for personal use. Ensure compliance with the terms of service of the sites you're scraping.

---

**Happy Automating!** 🎉
