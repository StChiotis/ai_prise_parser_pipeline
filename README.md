# AI Supermarket Flyer Parser


This project automates the parsing of Dutch supermarket promotional flyers using GPT-4 Vision and OpenAI API. 
It extracts product offers from PDF flyers, logs results, stores structured data into SQL Server, and includes retry logic for failed pages.

Designed for educational purposes and open-source experimentation, _**intended for users to replicate in their own repositories**_.

## Features

- Parse weekly supermarket flyers (AH, ALDI, JUMBO, LIDL, PLUS)
- Extract product names, offer types, prices, and quantities
- Normalize offers to prevent duplicates in SQL
- Retry logic for failed pages
- Modular parsers tailored per supermarket layout
- Easy to replicate or extend for your own use

## Folder Structure

```
Supermarket_Parser/
│
├── main.py                  # Main parser runner
├── retry_failed_pages.py    # Script to retry failed PDF pages
├── log_writer.py            # Logging utility
│
├── logs/                    # Log files for each run
├── retry_logs/              # Log files for retry scripts
│
├── parsers/                 # Individual production parsers per supermarket
│   ├── ah_parser.py
│   ├── aldi_parser.py
│   ├── jumbo_parser.py
│   ├── lidl_parser.py
│   └── plus_parser.py
│
└── Supermarket_Flyers/
    └── Week_26/             # Place flyers per week here
    └── Week_27/
    └── ...

```
## Workflow

1. Place weekly supermarket flyers into `Supermarket_Flyers/Week_<NUMBER>/`
2. Run:
```bash
python main.py --input_folder Supermarket_Flyers/Week_26 --week 26
```
3. Output:
   - Products inserted to `Supermarket_Offers` SQL table.
   - Log saved in `logs/` as `log_run_week_26_20250624_145311.txt`

4. To retry failed pages:
```bash
python retry_failed_pages.py --logfile logs/log_run_week_26_YYYYMMDD_HHMMSS.txt --week 26
```


## Database Table Structure

`dbo.Supermarket_Offers`

| Field           | Type        | Notes                   |
|-----------------|-------------|-------------------------|
| ID              | int         | Identity PK             |
| SupermarketName | varchar     | 'AH', 'ALDI', etc       |
| WeekNumber      | int         | Week number (ISO week)  |
| ProductName     | varchar     |                         |
| OfferType       | varchar     | Normalized (e.g. '25%') |
| OriginalPrice   | varchar     |                         |
| OfferPrice      | varchar     |                         |
| SourcePDF       | varchar     | Filename of flyer       |
| InsertedAt      | date        |                         |
| PageNumber      | int         | Page number             |


## Duplicate Prevention

Both `main.py` and `retry_failed_pages.py` use a `WHERE NOT EXISTS` SQL clause with these fields:
- WeekNumber
- ProductName
- OfferType
- OriginalPrice
- OfferPrice
- SourcePDF
- PageNumber


## Parser Prompt Overview (per parser)

Each parser uses a tailored GPT prompt to handle supermarket-specific flyer formats:

- **AH Parser:** Standard promotions like `1+1 gratis`, `% korting`, and price ranges.
- **ALDI Parser:** Includes `OP=OP`, mandatory fields and formatting expectations.
- **JUMBO Parser:** Handles complex rules like `KIES & MIX`, `Elke dag laag`, and group-level offers.
- **LIDL Parser:** Basic structure with exceptions for range prices and visual promotions.
- **PLUS Parser:** Similar to LIDL but adapted for PLUS layout and multibuy patterns.

You can find exact prompt text in `/parser_versioning/`.


## Normalization Strategy

All parsers normalize `OfferType` before inserting to DB:
```python
offer_type_raw = safe_strip(item.get("OfferType"))
offer_type_normalized = offer_type_raw.replace(" korting", "").replace("%korting", "%").strip()
```
This prevents minor wording differences from creating duplicates.


## Dev Notes

- To test a parser:
```python
selected_pages = [(i+1, p) for i, p in enumerate(pages[:2])]
```

- To change parsed pages (e.g. all):
```python
selected_pages = [(i+1, p) for i, p in enumerate(pages)]
```

- Folder and week must always match:
  - Example: Week 26 PDFs → `Supermarket_Flyers/Week_26/` → `--week 26`


## OpenAI API Notes

- GPT-4 Vision model (`gpt-4o`) is used.
- PDF pages are converted to PNG and sent to GPT.
- API key is currently hardcoded per parser.

## Disclaimer

This project is educational and open-source.
- It does not host or distribute any supermarket data, PDFs, or images.
- References to brands (AH, ALDI, JUMBO, LIDL, PLUS) are illustrative only.
- Users are encouraged to replicate the project in their own repositories.
- Users are solely responsible for compliance with any laws or terms of use for the data sources they process.

## License

This project is licensed under the MIT License — see the LICENSE file for details.
