"""Focused data-quality checks. No real network requests are used here."""

from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

from app import ROOT, START_URL, clean_books, collect_live, main, parse_books, save_outputs


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "samples" / "books.html").read_text(encoding="utf-8")
        self.records, _ = parse_books(self.html, START_URL)

    def test_full_titles_relative_links_and_ratings(self):
        self.assertEqual(self.records[0]["title"], "Python Practice Notes")
        self.assertEqual(self.records[0]["rating"], 4)
        self.assertEqual(self.records[0]["product_url"], "https://books.toscrape.com/catalogue/python-notes/index.html")
        _, next_url = parse_books(self.html + '<li class="next"><a href="page-2.html">next</a></li>', START_URL)
        self.assertEqual(next_url, "https://books.toscrape.com/catalogue/page-2.html")

    def test_cleaning_deduplicates_converts_prices_and_preserves_stock(self):
        frame = clean_books(self.records)
        self.assertEqual(len(frame), 5)
        self.assertAlmostEqual(frame["price_gbp"].mean(), 15.8)
        self.assertEqual(int(frame["in_stock"].sum()), 4)

    def test_malformed_html_and_empty_data_fail_clearly(self):
        for html in ("<html></html>", self.html.replace('class="price_color"', 'class="missing"', 1)):
            with self.assertRaises(ValueError):
                parse_books(html, START_URL)
        with self.assertRaises(ValueError):
            clean_books([])

    def test_invalid_values_do_not_become_plausible_reports(self):
        for field, value in (("price_text", "USD 18.50"), ("price_text", "£0.00"), ("rating", None), ("availability_text", "Unknown")):
            records = [dict(self.records[0], **{field: value})]
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                clean_books(records)

    def test_csv_database_and_report_agree(self):
        frame = clean_books(self.records)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            save_outputs(frame, output, "DEMO", len(self.records))
            self.assertEqual(len(pd.read_csv(output / "books.csv")), 5)
            with closing(sqlite3.connect(output / "books.sqlite")) as connection:
                count, average = connection.execute("SELECT COUNT(*), AVG(price_gbp) FROM books").fetchone()
            self.assertEqual(count, 5)
            self.assertAlmostEqual(average, 15.8)
            self.assertIn("Mode: DEMO", (output / "report.md").read_text(encoding="utf-8"))
            self.assertEqual(pd.read_csv(output / "by_rating.csv")["book_count"].sum(), 5)

    def test_export_closes_database_on_success_and_failure(self):
        frame = clean_books(self.records)
        for fail_query in (False, True):
            with self.subTest(fail_query=fail_query), tempfile.TemporaryDirectory() as folder:
                output = Path(folder)
                connection = sqlite3.connect(output / "books.sqlite")
                try:
                    with patch("app.sqlite3.connect", return_value=connection):
                        if fail_query:
                            with patch("app.pd.read_sql_query", side_effect=sqlite3.OperationalError("test query failure")):
                                with self.assertRaises(sqlite3.OperationalError):
                                    save_outputs(frame, output, "DEMO", len(self.records))
                        else:
                            save_outputs(frame, output, "DEMO", len(self.records))
                    with self.assertRaises(sqlite3.ProgrammingError):
                        connection.execute("SELECT 1")
                finally:
                    connection.close()

    @patch("app.requests.Session")
    def test_network_failure_propagates_instead_of_using_demo_data(self, session):
        session.return_value.__enter__.return_value.get.side_effect = requests.Timeout("test timeout")
        with self.assertRaises(requests.Timeout):
            collect_live(1)

    def test_demo_cli_runs_from_another_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "results"
            result = subprocess.run(
                [sys.executable, str(ROOT / "app.py"), "--demo", "--output", str(output)],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output / "books.csv").is_file())


if __name__ == "__main__":
    unittest.main()
