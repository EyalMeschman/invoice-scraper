Below is a structured review of your repo (Repomix bundle: ). I’m focusing on maintainability, Python best practices, libraries, and readability—broken into “chunks” you can hand to Cursor/ClaudeCode as discrete refactor tasks.

---

## Chunk 1 — Fix repo layout + remove confusing duplicates

### What I see

- You have **two different `utils.py` files**:
  - `utils.py` (root) with `get_project_root()`
  - `src/utils.py` with the real logic (`Utils` class, fingerprint shim, state management, etc.)

- You also have “app-ish” modules (`logger.py`, `google_secrets_client.py`) at root, while most logic lives under `src/`.

### Why it matters

Duplicate module names (`utils`) cause import ambiguity and confusion, and root-level modules + `src/` mix makes the repo harder to navigate and package.

### Refactor recommendation

- Move root modules into `src/` and make imports consistent.
- Rename the root `utils.py` (or remove it) to avoid collision.

**Concrete target structure**

```
invoice_scraper/
  src/
    invoice_scraper/
      __init__.py
      config.py
      logging.py
      secrets.py
      playwright_state.py
      scanners/
        __init__.py
        arnona.py
        meitav.py
        partner.py
        ...
      utils/
        __init__.py
        paths.py
        downloads.py
        auth.py
  tests/
    conftest.py
    scanners/
      test_arnona.py
      ...
```

---

## Chunk 2 — Fix a real bug in `conftest.py` sessionStorage injection

### What I see

In `conftest.py`, you build `session_storage_data = {"origin": ..., "localStorage": ..., "sessionStorage": ...}`

But later you do:

```python
for item in session_storage_data["items"]:
```

`items` **does not exist** in that dict. So that block will crash if it runs.

Also, you’re injecting storage **twice**:

1. `context.add_init_script(...)` (good approach)
2. then `page.goto(origin)` and `page.evaluate(sessionStorage.setItem...)` (redundant + currently broken)

### Recommended fix (simple + robust)

- **Keep only `add_init_script` injection** (it runs before page JS, which is exactly what you want).
- Remove the second injection block entirely.

### Extra improvement

Your log line:

```python
len(origin_data['sessionStorage'])
```

will crash if `sessionStorage` missing; you already use `.get()` above, but log references the raw key.

---

## Chunk 3 — Replace “tests as production code” with a scanner runner layer

### What I see

Your “scanners” are implemented as pytest tests (`*_scanner_test.py`), but they behave like **production tasks** (download invoices, write files, manage auth state).

### Why it matters

- Tests become hard to reason about (side effects, external services).
- Running “real downloads” via pytest is awkward for scheduling / automation.
- Shared logic gets duplicated across scanners because pytest test files aren’t structured like reusable modules.

### Refactor recommendation

Split into:

- **Scanner implementations**: pure code (functions/classes) that accept a Playwright `Page` and output downloaded `Path`s.
- **Thin pytest tests**: just call the scanner code.

Bonus: later you can add a CLI runner:

```bash
uv run python -m invoice_scraper run --platform meitav --periods 4..6
```

---

## Chunk 4 — DRY up repeated “InvoicePeriod” enums and download loops

### What I see

Every scanner defines its own `InvoicePeriod(StrEnum)` (monthly vs bi-monthly) + repeats:

- platform constant
- periods selection from `get_periods_to_download`
- loop that downloads and saves

### Recommended approach

Create a shared abstraction:

- A single `Period` concept:
  - monthly: `Jan..Dec`
  - numeric: `01..12`
  - bimonthly: `1-2025`, `2-2025`, etc.

Then scanners just define:

- how to locate the invoice row for a given period
- how to trigger download (direct vs blob)
- naming convention for files

This will cut a lot of code and make adding new scanners fast and consistent.

---

## Chunk 5 — Improve config: stop hardcoding `YEAR = 2025`

### What I see

`src/scanner_config.py` has `YEAR = 2025` with comments “update once per year”.

### Better pattern

Make it dynamic + overridable:

- default: current year
- override via env var or CLI arg

Example:

- `INVOICE_YEAR=2026 uv run pytest ...`
- or CLI: `--year 2026`

This avoids annual code changes and reduces accidental wrong-year downloads.

---

## Chunk 6 — Secrets/env loading: don’t load dotenv at import time

### What I see

`google_secrets_client.py` calls:

```python
load_dotenv(".env.defaults")
load_dotenv(".env", override=True)
```

at import time. `conftest.py` also loads dotenv at module import time.

### Why it matters

- Import-time side effects are brittle and surprising.
- Makes it harder to reuse the package from other entrypoints (CLI, scripts, notebooks).
- In tests, ordering can get weird.

### Recommendation

Centralize configuration loading once:

- a `config.py` that reads env (optionally using `pydantic-settings`)
- call it explicitly from `conftest.py` / CLI entrypoint

If you want a small dependency: **pydantic-settings** is great for typed env config.

---

## Chunk 7 — Logging: make logger naming + configuration consistent

### What I see

`logger.py` creates a logger using `logging.getLogger(__name__)` inside a helper; depending on where it’s called, you may get inconsistent names.

### Recommendation

- Use a stable app logger name like `"invoice_scraper"`.
- Configure once (level/format/handlers).
- In modules, do `log = logging.getLogger(__name__)` and rely on configured root/app logger.

Also: consider `rich` logging (optional) for nicer console output when debugging Playwright.

---

## Chunk 8 — Playwright reliability improvements

### What you’re already doing well

- Async Playwright usage.
- Smart “race” between direct download and blob fetch for Meitav.

### Improvements

- Prefer **locator-based waits** over `wait_for_timeout(500)` where possible.
- Wrap repetitive patterns:
  - `expect_new_page(click)` helper
  - `expect_download(click)` helper

- Add retry/backoff for flaky selectors and transient network issues:
  - small, bounded retries (e.g., 2 attempts) around navigation/download

---

## Chunk 9 — Type hints & small API cleanups in `src/utils.py`

### Observations

- Many helpers return `Locator | None` which is fine, but you can simplify usage by:
  - returning `Locator` and raising a small custom error when not found
  - or providing `must_*` variants (`must_wait_for_selector`)

Also:

- Prefer `ValueError`/`RuntimeError` with consistent messages; avoid broad `OSError` for missing env vars (use `KeyError` or custom `MissingEnvError`).

---

## Chunk 10 — Tooling upgrades (low effort, high payoff)

You already use Ruff and CI runs `ruff format --check` + `ruff check`. Nice.

Suggested additions:

- Add `mypy` (or `pyright`) for type checking (even if partial)
- Add `pre-commit` with:
  - ruff format
  - ruff check
  - trailing whitespace, end-of-file fixes

- Consider splitting ruff rules to avoid noisy ones in tests (or apply per-path config)

---

## Chunk 11 — Naming & organization: rename “\*\_scanner_test.py”

If these are primarily automation scripts, rename to reduce mental overhead:

- `src/scanners/arnona.py` (implementation)
- `tests/scanners/test_arnona.py` (pytest wrapper)

This makes it obvious what’s “product code” vs “test harness”.

---

## Chunk 12 — Suggested PR plan (in the order I’d do it)

1. **Fix `conftest.py` injection bug + remove duplicate injection path**
2. **Eliminate duplicate `utils.py` name collision** (rename root `utils.py` → `src/.../paths.py`)
3. **Move root modules into `src/`** and standardize imports
4. **Introduce a scanner base abstraction** (period handling + common download helpers)
5. **Make `YEAR` dynamic + override-able**
6. **Centralize config/env loading** (stop import-time dotenv loads)
7. Optional: add CLI runner + pre-commit + mypy
