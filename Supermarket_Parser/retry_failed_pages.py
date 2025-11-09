# retry_failed_pages.py

import argparse
import re
import pyodbc
import os
from parsers.ah_parser import parse_pdf as ah_parse
from parsers.aldi_parser import parse_pdf as aldi_parse
from parsers.jumbo_parser import parse_pdf as jumbo_parse
from parsers.lidl_parser import parse_pdf as lidl_parse
from parsers.plus_parser import parse_pdf as plus_parse
from log_writer import write_log, init_log

# Init log correctly
init_log("retry_failed_pages")

# Parse arguments
parser = argparse.ArgumentParser(description="Retry failed pages")
parser.add_argument("--logfile", required=True, help="Path to log file")
parser.add_argument("--week", required=True, type=int, help="Week number")
args = parser.parse_args()

# DB connection
conn = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=AI_Supermarket;Trusted_Connection=yes;")
cursor = conn.cursor()

# Read failed pages from log
def extract_failed_pages(logfile):
    failed_pages = {}
    with open(logfile, 'r', encoding='utf-8') as f:
        for line in f:
            match_skip = re.search(r'\[SKIP_PAGE\] (\d+) (.+\.pdf)', line)
            if match_skip:
                page_num = int(match_skip.group(1))
                pdf_name = match_skip.group(2)
                if pdf_name not in failed_pages:
                    failed_pages[pdf_name] = []
                failed_pages[pdf_name].append(page_num)
    return failed_pages

failed_pages = extract_failed_pages(args.logfile)

if failed_pages:
    write_log(f"\n✅ Found failed pages to retry:")
    for pdf_name, pages in failed_pages.items():
        write_log(f"→ {pdf_name}: pages {pages}")

    # Map PDF name → parser function → supermarket name
    parser_map = {
        "AH": (ah_parse, "AH"),
        "ALDI": (aldi_parse, "ALDI"),
        "JUMBO": (jumbo_parse, "JUMBO"),
        "LIDL": (lidl_parse, "LIDL"),
        "PLUS": (plus_parse, "PLUS")
    }

    # Retry pages
    input_folder = "C:/Data/Supermarket_Flyers/Week_26"
    for pdf_name, pages in failed_pages.items():
        filepath = f"{input_folder}/{pdf_name}"
        supermarket = next((key for key in parser_map if key in pdf_name.upper()), None)

        if supermarket:
            parse_func, supermarket_name = parser_map[supermarket]
            write_log(f"\n--- RETRY: {filepath} --- Pages: {pages}")
            offers = parse_func(filepath, args.week, pages_to_parse=pages)

            total_inserted = 0
            total_skipped = 0  # ✅ new counter

            for offer in offers:
                # ✅ Fix SourcePDF: keep only filename (without full path)
                offer_sourcepdf = os.path.basename(offer["SourcePDF"])

                try:
                    cursor.execute("""
                        INSERT INTO dbo.Supermarket_Offers
                        (SupermarketName, WeekNumber, ProductName, OfferType, OriginalPrice, OfferPrice, SourcePDF, InsertedAt, PageNumber)
                        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
                        WHERE NOT EXISTS (
                            SELECT 1 FROM dbo.Supermarket_Offers
                            WHERE WeekNumber = ?
                            AND ProductName = ?
                            AND OfferType = ?
                            AND OriginalPrice = ?
                            AND OfferPrice = ?
                            AND SourcePDF = ?
                            AND PageNumber = ?
                        )
                    """, (
                        supermarket_name,
                        args.week,
                        offer["ProductName"],
                        offer["OfferType"],
                        offer["OriginalPrice"],
                        offer["OfferPrice"],
                        offer_sourcepdf,
                        offer["InsertedAt"],
                        offer["PageNumber"],
                        # params for WHERE NOT EXISTS
                        args.week,
                        offer["ProductName"],
                        offer["OfferType"],
                        offer["OriginalPrice"],
                        offer["OfferPrice"],
                        offer_sourcepdf,
                        offer["PageNumber"]
                    ))

                    if cursor.rowcount > 0:
                        total_inserted += 1
                    else:
                        total_skipped += 1  # duplicate

                except Exception as e:
                    write_log(f"[ERROR] Failed to insert offer: {offer} — {e}")

            conn.commit()
            write_log(f"[RESULT] Inserted {total_inserted} offers, Skipped {total_skipped} duplicates for: {supermarket_name}")

else:
    write_log("\n✅ No failed pages found — nothing to retry.")

conn.close()
