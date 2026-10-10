import repository
from model import Invoice


class NotFoundError(Exception):
    pass


class StorageError(Exception):
    pass


# ---------- Invoice clean-up (tasks 1-5) ----------

def normalize(rows):
    """Task 1: clean vendor and status in place, return indexes with no amount."""
    missing = []
    for i in range(len(rows)):
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
    seen = {}
    for i, row in enumerate(rows):
        key = (row["invoice_id"], row["vendor"], row["amount"], row["status"], row["date"])
        seen.setdefault(key, []).append(i)

    exact_dupes = {key: idxs for key, idxs in seen.items() if len(idxs) > 1}

    # Collect first, delete afterwards, highest index first, so nothing is skipped.
    to_remove = []
    for idxs in exact_dupes.values():
        to_remove.extend(idxs[1:])
    for i in sorted(to_remove, reverse=True):
        del rows[i]

    kept = [i for i in range(len(rows) + len(to_remove)) if i not in to_remove]
    return exact_dupes, kept


def find_suspected_duplicates(rows):
    """Task 3: same vendor, amount and date but a different invoice_id."""
    groups = {}
    for i, row in enumerate(rows):
        if row["amount"] is None:
            continue
        key = (row["vendor"], row["amount"], row["date"])
        groups.setdefault(key, []).append(i)

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

    Returns (pairs, unmatched) as row indexes: pairs is [(credit, positive)].
    """
    pairs = []
    unmatched = []
    used = set()
    for i, row in enumerate(rows):
        if row["amount"] is None or row["amount"] >= 0:
            continue
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
        used.add(partner)
        rows[i]["status"] = "CANCELLED"
        rows[partner]["status"] = "CANCELLED"
        pairs.append((i, partner))
    return pairs, unmatched


def counts_in_totals(row):
    return row["amount"] is not None and row["status"] != "CANCELLED"


def reconcile(rows, payments):
    """Task 5: join payments to invoices by invoice_id and sum them.

    Returns (report, orphans). report has one entry per invoice_id that still
    counts in the totals; orphans are payments whose invoice_id is not in the data.
    """
    paid_by_id = {}
    for p in payments:
        paid_by_id[p["invoice_id"]] = paid_by_id.get(p["invoice_id"], 0) + p["paid"]

    billed_by_id = {}
    rows_by_id = {}
    for row in rows:
        rows_by_id[row["invoice_id"]] = rows_by_id.get(row["invoice_id"], 0) + 1
        if counts_in_totals(row):
            billed_by_id[row["invoice_id"]] = billed_by_id.get(row["invoice_id"], 0) + row["amount"]

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

    known = set(rows_by_id)
    orphans = [p for p in payments if p["invoice_id"] not in known]
    return report, orphans


# ---------- Payments API ----------

def _save():
    try:
        repository.save_data()
    except OSError as e:
        raise StorageError(f"could not write data file: {e}")


def _check_invoice_exists(invoice_id):
    if repository.get_invoice_by_id(invoice_id) is None:
        raise NotFoundError(f"invoice '{invoice_id}' does not exist")


def list_payments(invoice_id=None):
    result = []
    for i, p in enumerate(repository.get_payments()):
        if invoice_id is None or p["invoice_id"] == invoice_id:
            result.append({"index": i, **p})
    return result


def get_payment(index):
    payment = repository.get_payment_by_index(index)
    if payment is None:
        raise NotFoundError(f"payment {index} does not exist")
    return {"index": index, **payment}


def add_payment(invoice_id, paid):
    _check_invoice_exists(invoice_id)
    payment = repository.create_payment(invoice_id=invoice_id, paid=paid)
    _save()
    return {"index": len(repository.get_payments()) - 1, **payment}


def change_payment(index, changes):
    if repository.get_payment_by_index(index) is None:
        raise NotFoundError(f"payment {index} does not exist")
    if not changes:
        raise ValueError("nothing to update")
    if "invoice_id" in changes:
        _check_invoice_exists(changes["invoice_id"])
    payment = repository.update_payment_by_index(index, **changes)
    _save()
    return {"index": index, **payment}


def remove_payment(index):
    payment = repository.delete_payment_by_index(index)
    if payment is None:
        raise NotFoundError(f"payment {index} does not exist")
    _save()
    return {"index": index, **payment}
