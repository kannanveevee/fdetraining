"""Shared helpers to read and write the invoices.json file.

The create, get and delete routes all use the same JSON file, so the
load/save code lives here once instead of being copied into every file.
"""

import json
from pathlib import Path

# invoices.json sits in the same folder as this script.
INVOICES_FILE = Path(__file__).with_name("invoices.json")


def load_invoices():
    """Read the JSON file and return the invoices as a list of dicts."""
    with INVOICES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_invoices(invoices):
    """Write the whole list of invoices back to the JSON file."""
    with INVOICES_FILE.open("w", encoding="utf-8") as file:
        json.dump(invoices, file, indent=4)
