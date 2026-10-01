"""Reconcile Fernhill's deduction claims against Northgate's independent ledger.

The ledger is ground truth; each claim is a hypothesis to be confirmed or rejected.

pandas handles loading, data checks and totals. The matching rules are plain
functions over one claim at a time, so each rule stays readable and testable.

Usage:
    python reconcile.py [claims.csv] [ledger.csv] [register.csv]
"""
import re
import sys
from decimal import Decimal

import pandas as pd

AUDIT_START = "2025-01-01"
AUDIT_END = "2025-12-31"
TOLERANCE = Decimal("1.00")

REGISTER_FIELDS = ["claim_id", "matched_invoice", "status_flag", "note"]


def load(path):
    # dtype=str keeps "0088217" as text (no lost zeros); keep_default_na=False
    # keeps a blank cell as "" instead of NaN.
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_rows(path):
    return load(path).to_dict("records")


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


def data_checks(claims, ledger):
    """Facts about the raw data worth knowing before trusting any match."""
    po_counts = ledger["po_number"].value_counts()
    out_of_window = ledger[(ledger["invoice_date"] < AUDIT_START) |
                           (ledger["invoice_date"] > AUDIT_END)]
    short_paid = ledger[ledger["paid_amount"].map(Decimal) !=
                        ledger["invoice_amount"].map(Decimal)]
    return [
        f"{len(claims)} claims, {len(ledger)} ledger invoices",
        f"claims with blank invoice_ref: {', '.join(claims.loc[claims['invoice_ref'] == '', 'claim_id']) or 'none'}",
        f"POs shared by more than one ledger invoice: {', '.join(po_counts[po_counts > 1].index) or 'none'}",
        f"ledger invoices outside the audit window: {', '.join(out_of_window['invoice_number']) or 'none'}",
        f"ledger invoices without a payment: {(ledger['paid_date'] == '').sum()}",
        f"ledger invoices not paid in full: {', '.join(short_paid['invoice_number']) or 'none'}",
    ]


def summarize(register, claims):
    """Claim count and claimed amount per status_flag, summed exactly with Decimal."""
    df = register.merge(claims[["claim_id", "claimed_amount"]], on="claim_id")
    df["claimed_amount"] = df["claimed_amount"].map(Decimal)
    summary = (df.groupby("status_flag", sort=False)
                 .agg(claims=("claim_id", "count"), amount=("claimed_amount", "sum")))
    summary.loc["TOTAL"] = [summary["claims"].sum(), df["claimed_amount"].sum()]
    return summary


def main(argv):
    claims_path = argv[1] if len(argv) > 1 else "fernhill_claims.csv"
    ledger_path = argv[2] if len(argv) > 2 else "northgate_ledger.csv"
    out_path = argv[3] if len(argv) > 3 else "register.csv"

    claims, ledger = load(claims_path), load(ledger_path)

    print("Data checks")
    for line in data_checks(claims, ledger):
        print(f"  - {line}")

    register = pd.DataFrame(
        reconcile(claims.to_dict("records"), ledger.to_dict("records")),
        columns=REGISTER_FIELDS)
    register.to_csv(out_path, index=False)

    print("\nRegister")
    print(register.to_csv(index=False), end="")

    print("\nSummary by flag")
    print(summarize(register, claims).to_string())


if __name__ == "__main__":
    main(sys.argv)
