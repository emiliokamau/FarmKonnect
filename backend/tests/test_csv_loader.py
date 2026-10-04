import os
import csv
import tempfile
from datetime import datetime
from django.conf import settings
from django.test import SimpleTestCase
import backend.csv_loader
from backend.csv_loader import load_prices_from_csv


class CsvLoaderTestCase(SimpleTestCase):
    def test_load_prices_from_csv_all(self):
        # Create temporary CSV in the market data dir
        data_dir = settings.MARKET_DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        temp_file = os.path.join(data_dir, 'prices_test.csv')
        rows = [
            {'commodity': 'MAIZE', 'county': 'Nairobi', 'date': '2023-01-01', 'wholesale_price': '1500', 'retail_price': '1700'},
            {'commodity': 'BEANS', 'county': 'Mombasa', 'date': '2023-01-02', 'wholesale_price': '2000', 'retail_price': '2300'},
        ]
        with open(temp_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['commodity', 'county', 'date', 'wholesale_price', 'retail_price'])
            writer.writeheader()
            writer.writerows(rows)

        # Ensure the loader picks up this file as "latest"
        # Patch the internal helper to return our test file path
        from backend.csv_loader import _latest_csv_path
        original = _latest_csv_path
        try:
            # monkeypatch by assigning
            backend.csv_loader._latest_csv_path = lambda: temp_file
            all_data = load_prices_from_csv()
            self.assertEqual(len(all_data), 2)
            self.assertEqual(all_data[0]['commodity'], 'MAIZE')
        finally:
            # Restore original function
            backend.csv_loader._latest_csv_path = original
            if os.path.exists(temp_file):
                os.remove(temp_file)

