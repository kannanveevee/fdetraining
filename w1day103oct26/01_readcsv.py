"""Find high-value invoices in a CSV file.

Reads data/homework_invoices.csv, keeps every invoice whose amount is above
HIGH_VALUE_LIMIT, and writes those rows to data/high_value_invoice.csv.

Run from inside this folder:  python 01_readcsv.py
"""

import csv
import os

# Invoices with an amount strictly greater than this are "high value".
HIGH_VALUE_LIMIT = 100000

# The amount is the 3rd column: invoice_id, vendor, amount, status
AMOUNT_COLUMN = 2

INPUT_FILE = os.path.join("data", "homework_invoices.csv")
OUTPUT_FILE = os.path.join("data", "high_value_invoice.csv")

total_rows = 0      # how many invoice rows we read
high_value_rows = []  # the rows that pass the limit

# ---- Step 1: read the input file ----
with open(INPUT_FILE, newline="") as input_file:
    reader = csv.reader(input_file)
    header = next(reader)  # first line holds the column names, keep it for the output

    for row in reader:
        total_rows += 1
        try:
            print(f"Processing row: {row}")
            # float() fails for blank or non-numeric amounts (e.g. "TBD").
            # Such rows are reported below and skipped instead of stopping the script.
            if float(row[AMOUNT_COLUMN]) > HIGH_VALUE_LIMIT:
                high_value_rows.append(row)
        except Exception as error:
            print(f"Error processing row {row}: {error}")

# ---- Step 2: write the high-value rows to a new file ----
with open(OUTPUT_FILE, "w", newline="") as output_file:
    writer = csv.writer(output_file)
    writer.writerow(header)
    writer.writerows(high_value_rows)

# ---- Step 3: print a short summary ----
print(f"Total invoices read: {total_rows}")
print(f"Invoices greater than {HIGH_VALUE_LIMIT}: {len(high_value_rows)}")
