# main.py

import os
import argparse
import pyodbc
from parsers.ah_parser import parse_pdf as ah_parse
from parsers.aldi_parser import parse_pdf as aldi_parse
from parsers.jumbo_parser import parse_pdf as jumbo_parse
from parsers.lidl_parser import parse_pdf as lidl_parse
from parsers.plus_parser import parse_pdf as plus_parse
from log_writer import write_log, init_log  

# Parse arguments
parser = argparse.ArgumentParser(description="Supermarket Parser — Main Run")
parser.add_argument("--input_folder", required=True, help="Input folder with flyers")
parser.add_argument("--week", required=True, type=int, help="Week number")
args = parser.parse_args()

input_folder = args.input_folder
week_number = args.week

# INIT LOG — first!
init_log(week_number)

# DB connection
conn = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=AI_Supermarket;Trusted_Connection=yes;") # Adjust as needed
cursor = conn.cursor()

write_log(f"\n=== Supermarket Parser Run — Week {week_number} ===")
write_log(f"Processing folder: {input_folder}\n")

# Map PDF file → parser function → supermarket name
parser_map = {
    "AH": (ah_parse, "AH"),
    "ALDI": (aldi_parse, "ALDI"),
    "JUMBO": (jumbo_parse, "JUMBO"),
    "LIDL": (lidl_parse, "LIDL"),
    "PLUS": (plus_parse, "PLUS")
}

# Process PDFs
for filename in os.listdir(input_folder):
    if filename.lower().endswith(".pdf"):
        filepath = os.path.join(input_folder, filename)
        supermarket = next((key for key in parser_map if key in filename.upper()), None)

        if supermarket:
            parse_func, supermarket_name = parser_map[supermarket]
            write_log(f"\n--- Processing: {filepath} ---")
            offers = parse_func(filepath, week_number, pages_to_parse=list(range(1, 3)))   # Pages 1 and 2

            total_inserted = 0
            for offer in offers:
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
                        week_number,
                        offer["ProductName"],
                        offer["OfferType"],
                        offer["OriginalPrice"],
                        offer["OfferPrice"],
                        offer["SourcePDF"],
                        offer["InsertedAt"],
                        offer["PageNumber"],
                        # params for WHERE NOT EXISTS
                        week_number,
                        offer["ProductName"],
                        offer["OfferType"],
                        offer["OriginalPrice"],
                        offer["OfferPrice"],
                        offer["SourcePDF"],
                        offer["PageNumber"]
                    ))
                    if cursor.rowcount > 0:
                        total_inserted += 1
                except Exception as e:
                    write_log(f"[ERROR] Failed to insert offer: {offer} — {e}")

            conn.commit()
            write_log(f"[RESULT] Inserted {total_inserted} offers into DB for: {supermarket_name}")

write_log("\n✅ All done.")
conn.close()
