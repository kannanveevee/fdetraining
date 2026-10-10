import repository
import services


def main():
    try:
        data = repository.load_data()
    except (OSError, ValueError) as e:
        print(f"Cannot load data: {e}")
        return

    rows = data.get("invoices", [])
    payments = data.get("payments", [])

    print("Task 1 - normalize")
    missing = services.normalize(rows)
    if missing:
        for i in missing:
            print(f"  index {i}: {rows[i]['invoice_id']} has amount None (excluded from totals)")
    else:
        print("  no rows with a missing amount")

    print("Task 2 - exact duplicates")
    exact_dupes, kept = services.remove_exact_duplicates(rows)
    for key, idxs in exact_dupes.items():
        print(f"  {key} -> indexes {idxs}")
    if not exact_dupes:
        print("  none")
    print(f"  rows left: {len(rows)} (original indexes kept: {kept})")

    print("Task 3 - suspected duplicates")
    pairs = services.find_suspected_duplicates(rows)
    for later, earlier in pairs:
        print(f"  ({rows[later]['invoice_id']} ~ {rows[earlier]['invoice_id']})")
    if not pairs:
        print("  none")

    print("Task 4 - credit notes")
    matched, unmatched = services.match_credit_notes(rows)
    for credit, positive in matched:
        print(f"  {credit} <-> {positive}  "
              f"({rows[credit]['invoice_id']} cancels {rows[positive]['invoice_id']}; "
              f"original rows {kept[credit]} <-> {kept[positive]})")
    for i in unmatched:
        print(f"  index {i}: credit note {rows[i]['invoice_id']} has no matching positive invoice")
    if not matched and not unmatched:
        print("  none")

    print("Task 5 - payments per invoice")
    report, orphans = services.reconcile(rows, payments)
    for r in report:
        note = f"  (invoice_id appears on {r['rows']} rows)" if r["rows"] > 1 else ""
        print(f"  {r['invoice_id']}: billed {r['billed']:.2f}, paid {r['paid']:.2f}, "
              f"balance {r['balance']:.2f}{note}")
    for p in orphans:
        print(f"  payment of {p['paid']:.2f} for {p['invoice_id']} has no invoice")


if __name__ == "__main__":
    main()
