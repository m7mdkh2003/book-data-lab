# Book Data Lab

A guided beginner project for learning Python, Requests, BeautifulSoup, Pandas,
and basic SQL. It extracts book titles, GBP prices, ratings and availability;
validates and cleans the data; removes duplicate product URLs; and exports a
CSV, SQLite table and summary report. The code is provided as a learning aid:
run it, inspect the results, explain the functions, and complete the exercises
before presenting it as a skill you can use independently.

## Data sources

- `--demo`: locally authored, fictional HTML in `samples/books.html`. Six raw
  rows intentionally contain one duplicate. No website is contacted.
- Live mode: https://books.toscrape.com/ — a website designed for scraping
  practice. Its prices and ratings are randomly assigned, not market data.
  This project collects listing pages only, at most five per run, one second apart.
- Neither mode collects customer information or represents investment analysis.

## Windows / PowerShell setup

Requires Python 3.10 or newer. Extract the ZIP. Open the extracted folder,
click File Explorer's address bar, type `powershell`, and press Enter.

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --demo
```

Using the environment's Python directly avoids changing PowerShell's execution
policy. If `py` is unavailable, check `python --version` and use `python` for the
first two commands instead. If neither command exists, install Python from its
official website, https://www.python.org/downloads/, then reopen PowerShell.

Expected demo result: **5 unique books**, **1 duplicate removed**, **4 in stock**,
and average price **GBP 15.80**. Open `output/demo/report.md` in an editor and
`output/demo/books.csv` in Excel. These outputs are generated when you run the program.

## Live run and checks

```powershell
.\.venv\Scripts\python.exe app.py --pages 2
.\.venv\Scripts\python.exe -m unittest -v
```

On macOS/Linux, use `python3 -m venv .venv`, then `.venv/bin/python` for the
remaining commands. `--pages` accepts 1–5; its default is 1. `--output PATH`
selects an output directory. The default directories keep demo and live results
separate. Re-running replaces generated files in the selected output directory
and the `books` table; it does not maintain a historical dataset.

Live network failures stop with a nonzero exit status; they do not silently
switch to fictional data. HTML changes or invalid prices, ratings or stock
labels also stop processing. Check the error, connection and current page.
Do not disable TLS verification. A network failure happens before exports,
so old output files may still exist; check the report's generation time.

## Read the code in this order

1. `parse_books`: CSS selectors, attributes, text, relative URLs and pagination.
2. `clean_books`: numeric conversion, validation, booleans and deduplication.
3. `collect_live`: HTTP requests, timeouts, status checks and bounded pagination.
4. `save_outputs`: CSV export, SQL `GROUP BY` and report generation.

`queries.sql` contains three exercises for the generated SQLite database.
SQLite is included with Python; a MySQL server is not required for this lesson.

## Practice before publishing

- Explain why the full title is read from the link's `title` attribute.
- Add a new valid book to the local HTML; predict the new count and average.
- Change a price to `N/A` and explain the validation error.
- Find books below GBP 15 using Pandas, then reproduce the result in SQL.
- Run two live pages and explain why product URLs are the deduplication key.
- Describe limitations: static HTML, one practice source, no JavaScript rendering,
  no incremental loading, and no finance-specific analysis.

See `START_HERE_AR.md` for the Arabic learning steps.
