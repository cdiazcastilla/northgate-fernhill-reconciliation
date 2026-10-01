from pathlib import Path

import pytest

from reconcile import canon_invoice, read_rows, reconcile

HERE = Path(__file__).parent


@pytest.fixture
def ledger():
    """The real Northgate ledger."""
    return read_rows(HERE / "northgate_ledger.csv")


def claim(invoice_ref, po_ref, amount, claim_date="2025-06-01", claim_id="TEST-1"):
    return {"claim_id": claim_id, "invoice_ref": invoice_ref, "po_ref": po_ref,
            "claim_date": claim_date, "claimed_amount": amount,
            "reason_code": "TEST"}


def run_one(c, ledger):
    return reconcile([c], ledger)[0]


def test_ambiguous_po_5521_is_not_resolved_by_amount(ledger):
    # Precondition: the trap is real. 915.75 is exactly INV-10517's amount.
    inv_10517 = next(r for r in ledger if r["invoice_number"] == "INV-10517")
    assert inv_10517["invoice_amount"] == "915.75"

    row = run_one(claim("", "PO-5521", "915.75"), ledger)

    assert row["status_flag"] == "AMBIGUOUS_NO_MATCH"
    assert row["matched_invoice"] == ""


def test_leading_zero_normalization(ledger):
    assert canon_invoice("88217") == canon_invoice("0088217")

    row = run_one(claim("88217", "PO-5512", "642.50"), ledger)

    assert row["matched_invoice"] == "0088217"
    assert row["status_flag"] == "CLEAN_MATCH"


def test_out_of_period_uses_invoice_date_not_claim_date(ledger):
    # Claim filed inside 2025, but INV-09988 is dated 2024-11-02.
    row = run_one(claim("INV-09988", "PO-5490", "875.00", claim_date="2025-01-10"), ledger)

    assert row["matched_invoice"] == "INV-09988"
    assert row["status_flag"] == "OUT_OF_PERIOD"


@pytest.mark.parametrize("amount, expected", [
    ("1181.00", "CLEAN_MATCH"),        # exactly 1.00 over INV-10432 (1180.00)
    ("1181.01", "AMOUNT_OVERSTATED"),  # 1.01 over
])
def test_tolerance_boundary(ledger, amount, expected):
    row = run_one(claim("INV-10432", "PO-5501", amount), ledger)

    assert row["status_flag"] == expected


def test_garbled_ref_falls_back_to_unique_po(ledger):
    # Letter O instead of zeros: must not resolve as an invoice number...
    assert canon_invoice("INV-1O6OO") != canon_invoice("INV-10600")

    row = run_one(claim("INV-1O6OO", "PO-5530", "1502.40"), ledger)

    # ...but PO-5530 has exactly one ledger invoice, so the fallback applies.
    assert row["matched_invoice"] == "INV-10600"
    assert row["status_flag"] == "CLEAN_MATCH"
    assert "PO fallback" in row["note"]
