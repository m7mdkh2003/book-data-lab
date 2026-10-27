# Verification — 28 October 2026

Corrected source checked in the assistant's Linux environment. The Windows
fix still needs to be rerun on Mohammad's laptop.

- Python 3.12.14; Requests 2.34.2; BeautifulSoup 4.15.0; Pandas 2.2.3.
- `python -m unittest -v`: 8 tests passed. Tests use synthetic data and mocked
  network failures. They check data validation, extraction, URL resolution,
  deduplication, CSV/SQL agreement, and running from another working directory.
- The new regression test verifies that exports close their SQLite connection
  both on success and when the grouped-report query fails. Both cases failed
  with the old export implementation and pass after the correction.
- `python app.py --demo`: 6 raw rows -> 5 unique books; 4 in stock;
  average GBP 15.80.
- `python app.py --pages 2`: a separate real HTTP smoke check collected 40
  unique books from the practice site; average GBP 34.96 for that run.
- CSV row counts, SQLite counts, grouped counts, numeric prices, ratings and
  unique URLs were checked for both runs.

## Windows feedback and correction

Mohammad ran the demo and live modes on Windows with Python 3.12.10: 5 demo
books and 40 live books were saved. Pandas and SQL each returned the same
8 live books priced below GBP 20.

The original test suite passed 6 tests but failed temporary-directory cleanup
with `WinError 32` because `books.sqlite` was still open. The export and the
CSV/database consistency test now use `contextlib.closing` to close their
connections explicitly. The export retains its commit/rollback context.
No cleanup errors are suppressed. Rerun `python -m unittest -v` on Windows
after replacing the source files to confirm the corrected 8-test suite there.

The ZIP contains source, a synthetic input fixture, instructions and exercises.
Generated output and installed dependencies are excluded. Run the commands in
README to generate fresh results. The website can change; these checks do not
claim general-purpose, JavaScript-rendered or finance-specific scraping support.
