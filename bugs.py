import csv
import os
import datetime
import uuid

def log_bug(user, desc, severity):
    file_exists = os.path.isfile("bugs.csv")
    with open("bugs.csv", mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(["ID", "Time", "User", "Severity", "Description"])
        writer.writerow([str(uuid.uuid4())[:8], datetime.datetime.now(), user, severity, desc])

