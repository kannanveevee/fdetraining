"""Business logic.

Part 1 - invoice clean-up (tasks 1 to 5 from Rules.txt). These functions work
         on a plain list of invoice dicts called `rows`, and report.py uses them.
Part 2 - payments API. These functions are called by main.py.
"""

import repository
from model import Invoice


class NotFoundError(Exception):
    """Something the caller asked for does not exist (becomes HTTP 404)."""


class StorageError(Exception):
    """The data file could not be saved (becomes HTTP 500)."""


# =====================================================================
# Part 1 - Invoice clean-up (tasks 1-5)
# =====================================================================

def normalize(rows):
    """Task 1: clean vendor and status in place, return indexes with no amount."""
    missing = []
    for i in range(len(rows)):
        # "abc ltd " -> "Abc Ltd", "pending" -> "PENDING"
        rows[i]["vendor"] = rows[i]["vendor"].strip().title()
        rows[i]["status"] = rows[i]["status"].strip().upper()
        if rows[i]["amount"] is None:
            missing.append(i)
    return missing


def remove_exact_duplicates(rows):
    """Task 2: keep the first row of each exact-duplicate group, drop the rest.

    Returns (exact_dupes, kept) where exact_dupes maps the row key to all of
    its indexes and kept is the list of original indexes that survived.
    """
    # Group the row numbers by the full row content (every field).
    seen = {}
    for i, row in enumerate(rows):
        key = (row["invoice_id"], row["vendor"], row["amount"], row["status"], row["date"])
        seen.setdefault(key, []).append(i)

    # Only the groups with more than one row are duplicates.
    exact_dupes = {key: idxs for key, idxs in seen.items() if len(idxs) > 1}

    # Collect first, delete afterwards, highest index first, so nothing is skipped.
    # (Deleting while looping forward would shift the rows and skip items.)
    to_remove = []
    for idxs in exact_dupes.values():
        to_remove.extend(idxs[1:])   # idxs[0] is the first row, which we keep
    for i in sorted(to_remove, reverse=True):
        del rows[i]

    # Work out which of the original row numbers are still in the list.
    original_count = len(rows) + len(to_remove)
    kept = [i for i in range(original_count) if i not in to_remove]
    return exact_dupes, kept


def find_suspected_duplicates(rows):
    """Task 3: same vendor, amount and date but a different invoice_id.

    Returns a list of (later_index, earlier_index) pairs. Nothing is removed.
    """
    # Group row numbers that share vendor + amount + date (skip rows with no amount).
    groups = {}
    for i, row in enumerate(rows):
        if row["amount"] is None:
            continue
        key = (row["vendor"], row["amount"], row["date"])
        groups.setdefault(key, []).append(i)

    # Inside each group, compare every pair; a different invoice_id means "suspected".
    pairs = []
    for idxs in groups.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                first, second = idxs[a], idxs[b]
                if rows[first]["invoice_id"] != rows[second]["invoice_id"]:
                    pairs.append((second, first))
    return pairs


def match_credit_notes(rows):
    """Task 4: pair each negative invoice with a positive one and cancel both.

    Returns (pairs, unmatched) as row indexes: pairs is [(credit, positive)],
    unmatched is the list of credit notes that found no partner.
    """
    pairs = []
    unmatched = []
    used = set()   # positive invoices that already have a credit note

    for i, row in enumerate(rows):
        # Only negative amounts are credit notes.
        if row["amount"] is None or row["amount"] >= 0:
            continue

        # Look for a positive invoice: same vendor, same amount without the minus sign.
        partner = None
        for j, other in enumerate(rows):
            if j in used or other["amount"] is None or other["amount"] <= 0:
                continue
            if other["vendor"] == row["vendor"] and other["amount"] == -row["amount"]:
                partner = j
                break

        if partner is None:
            unmatched.append(i)
            continue

        # Found a partner: mark both rows as cancelled.
        used.add(partner)
        rows[i]["status"] = "CANCELLED"
        rows[partner]["status"] = "CANCELLED"
        pairs.append((i, partner))

    return pairs, unmatched


def counts_in_totals(row):
    """A row is included in totals only if it has an amount and is not cancelled."""
    return row["amount"] is not None and row["status"] != "CANCELLED"


def reconcile(rows, payments):
    """Task 5: join payments to invoices by invoice_id and sum them.

    Returns (report, orphans). report has one entry per invoice_id that still
    counts in the totals; orphans are payments whose invoice_id is not in the data.
    """
    # Total paid for each invoice_id.
    paid_by_id = {}
    for p in payments:
        paid_by_id[p["invoice_id"]] = paid_by_id.get(p["invoice_id"], 0) + p["paid"]

    # Total billed for each invoice_id (only rows that count), and how many rows each id has.
    billed_by_id = {}
    rows_by_id = {}
    for row in rows:
        rows_by_id[row["invoice_id"]] = rows_by_id.get(row["invoice_id"], 0) + 1
        if counts_in_totals(row):
            billed_by_id[row["invoice_id"]] = billed_by_id.get(row["invoice_id"], 0) + row["amount"]

    # One report line per invoice_id: billed - paid = balance.
    report = []
    for invoice_id, billed in billed_by_id.items():
        paid = paid_by_id.get(invoice_id, 0)
        report.append({
            "invoice_id": invoice_id,
            "billed": billed,
            "paid": paid,
            "balance": billed - paid,
            "rows": rows_by_id[invoice_id],
        })

    # Payments that point to an invoice_id that does not exist anywhere.
    known = set(rows_by_id)
    orphans = [p for p in payments if p["invoice_id"] not in known]
    return report, orphans


# =====================================================================
# Part 2 - Payments API
# =====================================================================

def _save():
    """Write the data file; turn a disk error into our own StorageError."""
    try:
        repository.save_data()
    except OSError as e:
        raise StorageError(f"could not write data file: {e}")


def _check_invoice_exists(invoice_id):
    """Stop with NotFoundError if there is no invoice with this id."""
    if repository.get_invoice_by_id(invoice_id) is None:
        raise NotFoundError(f"invoice '{invoice_id}' does not exist")


def list_payments(invoice_id=None):
    """Return all payments (optionally only one invoice's), each with its index."""
    result = []
    for i, p in enumerate(repository.get_payments()):
        if invoice_id is None or p["invoice_id"] == invoice_id:
            result.append({"index": i, **p})
    return result


def get_payment(index):
    """Return one payment by position, or raise NotFoundError."""
    payment = repository.get_payment_by_index(index)
    if payment is None:
        raise NotFoundError(f"payment {index} does not exist")
    return {"index": index, **payment}


def add_payment(invoice_id, paid):
    """Add a payment for an existing invoice and save."""
    _check_invoice_exists(invoice_id)
    payment = repository.create_payment(invoice_id=invoice_id, paid=paid)
    _save()
    # The new payment is always the last one in the list.
    return {"index": len(repository.get_payments()) - 1, **payment}


def change_payment(index, changes):
    """Update a payment. `changes` holds only the fields to change."""
    if repository.get_payment_by_index(index) is None:
        raise NotFoundError(f"payment {index} does not exist")
    if not changes:
        raise ValueError("nothing to update")
    # If the payment is being moved to another invoice, that invoice must exist.
    if "invoice_id" in changes:
        _check_invoice_exists(changes["invoice_id"])
    payment = repository.update_payment_by_index(index, **changes)
    _save()
    return {"index": index, **payment}


def remove_payment(index):
    """Delete a payment by position and save."""
    payment = repository.delete_payment_by_index(index)
    if payment is None:
        raise NotFoundError(f"payment {index} does not exist")
    _save()
    return {"index": index, **payment}
