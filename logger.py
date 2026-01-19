import pandas as pd
import os
from datetime import datetime

# We changed the filename to 'logs_v2.csv' to bypass the error 
# and start a fresh database.
LOG_FILE = "logs_v2.csv"

def log_submission(client_name, form_name, status):
    """
    Saves a new entry to the log file.
    """
    # 1. Create the new entry data
    new_entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Client": client_name,
        "Form": form_name,
        "Status": status
    }
    
    # 2. Check if file exists to determine if we need headers
    file_exists = os.path.isfile(LOG_FILE)
    
    # 3. Save to CSV
    df = pd.DataFrame([new_entry])
    df.to_csv(LOG_FILE, mode='a', header=not file_exists, index=False)

def load_logs():
    """
    Reads the log file for the Dashboard.
    """
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except:
            # If file is corrupt, return empty
            return pd.DataFrame(columns=["Timestamp", "Client", "Form", "Status"])
    else:
        # If no logs yet, return empty structure
        return pd.DataFrame(columns=["Timestamp", "Client", "Form", "Status"])
