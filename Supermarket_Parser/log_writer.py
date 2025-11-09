# log_writer.py

import os
from datetime import datetime

# Set once per run — filled by main.py or retry_failed_pages.py
LOG_FILE_PATH = None

def init_log(log_prefix):
    global LOG_FILE_PATH
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if log_prefix.startswith("retry_"):
        # Logs go to retry_logs folder
        log_dir = "retry_logs"
        os.makedirs(log_dir, exist_ok=True)
        LOG_FILE_PATH = os.path.join(log_dir, f"{log_prefix}_{timestamp}.txt")
    else:
        # Normal run logs go to logs folder
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        LOG_FILE_PATH = os.path.join(log_dir, f"log_run_week_{log_prefix}_{timestamp}.txt")

    with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(f"=== Supermarket Parser Log — {log_prefix} — {timestamp} ===\n")

def write_log(message):
    global LOG_FILE_PATH
    if LOG_FILE_PATH is None:
        raise Exception("LOG_FILE_PATH is not initialized — please call init_log() first")

    print(message)
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")
