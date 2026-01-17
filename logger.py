import csv
import os
import datetime
import uuid
import pandas as pd

LOG_FILE = "submission_log.csv"

def log_submission(client_name, form_type, status):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(["ID", "Time", "Client", "Type", "Status"])
        writer.writerow([str(uuid.uuid4())[:8], datetime.datetime.now(), client_name, form_type, status])

def load_logs():
    if os.path.exists(LOG_FILE): return pd.read_csv(LOG_FILE)
    return pd.DataFrame(columns=["ID", "Time", "Client", "Type", "Status"])

