# backend/etl/tasks.py
"""Celery task that scrapes KAMIS market data and stores it as CSV.

The task:
1. Retrieves the KAMIS landing page (or a specific endpoint that contains the market table).
2. Parses the HTML with BeautifulSoup to extract rows for the supported commodities
   (MAIZE, BEANS, TILAPIA).  The expected table columns are:
   * Commodity name
   * County
   * Date (assumed to be the current date displayed on the page)
   * Wholesale price (KES/kg)
   * Retail price (KES/kg)
3. Writes the collected rows to a CSV file under ``settings.MARKET_DATA_DIR``.
   The filename includes a timestamp: ``prices_YYYYMMDD_HHMM.csv``.
4. Optionally logs the operation; the CSV can later be loaded by the API view.

If the website layout changes, the parsing logic may need to be updated.
"""

import os
import csv
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Ensure the data directory exists
DATA_DIR = Path(getattr(settings, "MARKET_DATA_DIR", Path(settings.BASE_DIR) / "market_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_COMMODITIES = {"MAIZE", "BEANS", "TILAPIA"}
KAMIS_URL = "https://kamis.kilimo.go.ke/"

@shared_task(name="backend.etl.tasks.fetch_and_save_market_prices")
def fetch_and_save_market_prices():
    """Scrape KAMIS and write a timestamped CSV file.

    The CSV columns are:
        commodity,county,date,wholesale_price,retail_price
    """
    logger.info("Starting KAMIS market data scrape")
    try:
        response = requests.get(KAMIS_URL, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        logger.error("Failed to retrieve KAMIS page: %s", exc)
        return

    soup = BeautifulSoup(response.text, "html.parser")
    # The implementation below assumes the data lives in a table with a specific CSS class.
    # Adjust selectors according to the actual page structure.
    table = soup.find("table", class_="kamis-table")
    if not table:
        logger.error("Could not locate market data table on KAMIS page")
        return

    rows = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    for tr in table.find_all("tr")[1:]:  # skip header row
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) < 5:
            continue
        commodity, county, wholesale, retail = cols[0], cols[1], cols[2], cols[3]
        commodity = commodity.upper()
        if commodity not in SUPPORTED_COMMODITIES:
            continue
        # Clean numeric values – remove commas, currency symbols, etc.
        try:
            wholesale_price = float(wholesale.replace(",", "").replace("KES", "").strip())
            retail_price = float(retail.replace(",", "").replace("KES", "").strip())
        except ValueError:
            logger.warning("Skipping row with non‑numeric price: %s", cols)
            continue
        rows.append([commodity, county, today_str, wholesale_price, retail_price])

    if not rows:
        logger.warning("No market rows extracted for supported commodities")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = DATA_DIR / f"prices_{timestamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["commodity", "county", "date", "wholesale_price", "retail_price"])
        writer.writerows(rows)

    logger.info("Saved %d market rows to %s", len(rows), csv_path)

    # Optional: you could also load the CSV into the DB here by calling a service function.
    return str(csv_path)
