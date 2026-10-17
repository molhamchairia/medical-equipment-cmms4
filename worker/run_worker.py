"""Worker entry point placeholder for scheduled CMMS jobs.

The worker is intentionally separate from Streamlit. Scheduled jobs must be idempotent
and use persisted database state so they can safely resume after restarts.
"""
import logging
import time
from core.db import init_db

logging.basicConfig(level=logging.INFO, filename="data/worker.log")

def main():
    init_db()
    logging.info("CMMS worker started; scheduled jobs are not enabled in this starter build.")
    try:
        while True: time.sleep(60)
    except KeyboardInterrupt:
        logging.info("CMMS worker stopped")
if __name__ == "__main__": main()
