# parsers/plus_parser.py

import pdfplumber
from openai import OpenAI
import io
import json
import base64
from datetime import datetime
from dateutil import parser
import time
from log_writer import write_log

# Hardcoded API key — replace with your key:
client = OpenAI(api_key=" ... YOUR_OPENAI_API_KEY ... ") # Adjust as needed

# Helper — sanitize date field
def safe_date(val, default="2025-06-24"):
    try:
        if val is None or str(val).strip() == "":
            return default
        dt = parser.parse(str(val), dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except:
        return default

# Helper — safe strip
def safe_strip(val):
    if val is None:
        return ""
    return str(val).strip()

def parse_pdf(filepath, week_number, pages_to_parse=None):
    offers = []
    write_log(f"\n=== Parsing PLUS PDF with GPT-4 Vision: {filepath} ===")

    with pdfplumber.open(filepath) as pdf:
        
# Determine pages to parse:
        if pages_to_parse:
            pages_to_parse = [p-1 for p in pages_to_parse]  # 0-based
            selected_pages = [(p+1, pdf.pages[p]) for p in pages_to_parse if 0 <= p < len(pdf.pages)]
        else:
            selected_pages = [(i+1, p) for i, p in enumerate(pdf.pages[:2])]  # First 2 pages

        for true_page_num, page in selected_pages:
            write_log(f"[INFO] Page {true_page_num}: Sending to GPT-4 Vision...")

            # Convert PDF page to PNG (resolution 300)
            image = page.to_image(resolution=300).original
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are an expert in reading Dutch supermarket promotional flyers. "
                                    "Extract ALL products, offers, prices, discounts, and promotions shown on this page. "

                                    "RULES: "
                                    "1️. If the flyer shows 'OP=OP' or 'OP = OP', this means the product is sold only while stocks last. "
                                    "Set OfferType = 'OP=OP' for these products. "
                                    "Do not set OfferType = 'Regular Price' for these products. "
                                    "If no promotional price is visible, copy the shelf price into both OriginalPrice and OfferPrice. "
                                    "Leave ValidityEnd = 'unknown' or week end. "

                                    "2️. If the flyer shows a clear promotional message or badge (such as '1+1 gratis', '2+3 gratis', '25% korting', etc), "
                                    "then set this value in the OfferType field and DO NOT output other offer types for the same product. "
                                    "→ Prioritize the first and most important promotional message as seen by the customer. "

                                    "3️. If NO promotional badge or message is present, but price reductions or ranges are shown "
                                    "(e.g. 'actieprijzen variëren van 1.99-2.39'), "
                                    "then use OfferType = 'Discount' or 'Discount Range' as appropriate. "

                                    "4️. The OriginalPrice field must always be provided — it is the full price per product BEFORE applying any promotion. "
                                    "5️. The OfferPrice field must always be provided — it is the price per product AFTER applying the promotion (if any). "

                                    "6️. Do not skip any products — even if font is small or price is complex — extract ALL products shown on the page. "

                                    "7️. Double check extracted prices — ensure the price is read exactly as shown on the flyer — do not change decimal points or digits. "

                                    "8️. Return response ONLY as a JSON array, no other text, no formatting. "
                                    "Each item must have: ProductName, OfferType, OriginalPrice, OfferPrice."
                                    
                                    "9️. If the flyer shows '+1 zegel', 'spaarzegel', 'zegelactie', or similar loyalty/stamp promotions, "
                                    "these are NOT product discounts — they must be ignored. "

                                    "DO NOT output '+1' or similar as OfferType — only real price promotions should be output. "

                                )
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": "data:image/png;base64," + img_base64
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=4000
                    )

                    response_text = response.choices[0].message.content

                    # Clean GPT response — remove code block if present
                    if response_text.startswith("```json"):
                        response_text = response_text.lstrip("```json").strip()
                    if response_text.endswith("```"):
                        response_text = response_text.rstrip("```").strip()

                        # Parse JSON response
                        offers_json = json.loads(response_text)
                        for item in offers_json:
                            offer_type_raw = safe_strip(item.get("OfferType"))
                            offer_type_normalized = offer_type_raw.replace(" korting", "").replace("%korting", "%").strip()

                            offers.append({
                                "ProductName": safe_strip(item.get("ProductName")),
                                "OfferType": offer_type_normalized,
                                "OriginalPrice": safe_strip(item.get("OriginalPrice")),
                                "OfferPrice": safe_strip(item.get("OfferPrice")),
                                "SourcePDF": filepath.split("\\")[-1],
                                "InsertedAt": datetime.now().strftime("%d-%m-%Y"),
                                "PageNumber": true_page_num
                            })

                        write_log(f"[INFO] Parsed {len(offers_json)} items from page {true_page_num}.")
                        break  # success → exit retry loop


                except Exception as e:
                    write_log(f"[ERROR] Page {true_page_num} attempt {attempt+1}: {e}")
                    if attempt == max_retries - 1:
                        pdf_name = filepath.split("\\")[-1]
                        write_log(f"[SKIP_PAGE] {true_page_num} {pdf_name}")
                    else:
                        time.sleep(2)

    write_log(f"\n✅ Total offers parsed from PLUS PDF: {len(offers)}")
    return offers
