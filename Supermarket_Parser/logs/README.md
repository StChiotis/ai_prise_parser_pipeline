## Folder Structure

```
  Supermarket_Parser/
    │
    ├── main.py                  # Main parser runner
    ├── retry_failed_pages.py    # Script to retry failed PDF pages
    ├── log_writer.py            # Logging utility
    │
👉🏼  ├── logs/                    # Log files for each run
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
