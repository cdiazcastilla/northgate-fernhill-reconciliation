"""Reconcile Fernhill's deduction claims against Northgate's independent ledger.

The ledger is ground truth; each claim is a hypothesis to be confirmed or rejected.

Usage:
    python reconcile.py [claims.csv] [ledger.csv] [register.csv]
"""
import csv
import re
import sys
from decimal import Decimal

AUDIT_START = "2025-01-01"
AUDIT_END = "2025-12-31"
TOLERANCE = Decimal("1.00")

REGISTER_FIELDS = ["claim_id", "matched_invoice", "status_flag", "note"]


def read_rows(path):
    # csv.DictReader returns every field as a str, so invoice numbers such as
    # "0088217" are never coerced to integers.
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def canon_invoice(raw):
    """Strip an optional 'INV-' prefix (any case) and leading zeros.

    No fuzzy/OCR correction: 'INV-1O6OO' stays as-is and simply fails to resolve.
    Returns "" for a blank value.
    """
    s = (raw or "").strip()
    s = re.sub(r"^inv-", "", s, flags=re.IGNORECASE)
    s = s.lstrip("0")
    return s


def build_indexes(ledger):
    by_invoice = {}
    by_po = {}
    for row in ledger:
        key = canon_invoice(row["invoice_number"])
        if key in by_invoice:
            raise ValueError(f"Two ledger invoices canonicalize to '{key}'")
        by_invoice[key] = row
        po = row["po_number"].strip()
        if po:
            by_po.setdefault(po, []).append(row)
    return by_invoice, by_po


def classify(claim, by_invoice, by_po):
    """Return (matched_invoice, status_flag, note) for one claim."""
    inv_raw = claim["invoice_ref"].strip()
    po = claim["po_ref"].strip()
    inv_key = canon_invoice(inv_raw)
    inv_desc = f"invoice_ref '{inv_raw}'" if inv_raw else "blank invoice_ref"

    # Rule 2: invoice_ref first.
    if inv_key and inv_key in by_invoice:
        match = by_invoice[inv_key]
        how = f"Matched by invoice_ref '{inv_raw}'."
    else:
        # Rule 2: PO fallback only if exactly one ledger invoice carries the PO.
        candidates = by_po.get(po, []) if po else []
        if len(candidates) > 1:
            ids = ", ".join(c["invoice_number"] for c in candidates)
            return ("", "AMBIGUOUS_NO_MATCH",
                    f"{inv_desc} did not resolve; PO fallback: {po} is shared by "
                    f"{len(candidates)} ledger invoices ({ids}). Amount not used "
                    f"to break the tie.")
        if not candidates:
            # Rule 3.
            return ("", "PHANTOM",
                    f"{inv_desc} did not resolve and PO '{po}' is not in the ledger.")
        match = candidates[0]
        how = (f"{inv_desc} did not resolve; matched by PO fallback "
               f"({po} -> {match['invoice_number']}, the only ledger invoice on that PO).")

    matched_invoice = match["invoice_number"]

    # Rule 4: audit window uses the ledger invoice date (ISO strings compare correctly).
    inv_date = match["invoice_date"].strip()
    if not (AUDIT_START <= inv_date <= AUDIT_END):
        return (matched_invoice, "OUT_OF_PERIOD",
                f"{how} Invoice date {inv_date} is outside {AUDIT_START}..{AUDIT_END} "
                f"(claim filed {claim['claim_date']}).")

    # Rules 5-6: compare to invoice_amount, using Decimal.
    claimed = Decimal(claim["claimed_amount"])
    invoiced = Decimal(match["invoice_amount"])
    diff = claimed - invoiced
    amounts = f"Claimed {claimed} vs invoiced {invoiced} (diff {diff:+})."
    if diff > TOLERANCE:
        return (matched_invoice, "AMOUNT_OVERSTATED",
                f"{how} {amounts} Exceeds the {TOLERANCE} tolerance.")
    return matched_invoice, "CLEAN_MATCH", f"{how} {amounts}"


def reconcile(claims, ledger):
    by_invoice, by_po = build_indexes(ledger)
    register = []
    for claim in claims:
        matched, flag, note = classify(claim, by_invoice, by_po)
        register.append({"claim_id": claim["claim_id"], "matched_invoice": matched,
                         "status_flag": flag, "note": note})
    return register


def main(argv):
    claims_path = argv[1] if len(argv) > 1 else "fernhill_claims.csv"
    ledger_path = argv[2] if len(argv) > 2 else "northgate_ledger.csv"
    out_path = argv[3] if len(argv) > 3 else "register.csv"

    register = reconcile(read_rows(claims_path), read_rows(ledger_path))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTER_FIELDS)
        writer.writeheader()
        writer.writerows(register)

    writer = csv.DictWriter(sys.stdout, fieldnames=REGISTER_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(register)


if __name__ == "__main__":
    main(sys.argv)
