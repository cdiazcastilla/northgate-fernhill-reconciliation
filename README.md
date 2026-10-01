# northgate-fernhill-reconciliation

Reconciles Fernhill Mart's deduction claims against Northgate Outdoor Supply's independent ledger.
The **ledger is ground truth**; each **claim is a hypothesis** that is confirmed only if the ledger supports it.

## Deliverables

| # | Deliverable | File |
|---|---|---|
| 1 | Reconciliation script and register | [`reconcile.py`](reconcile.py) → [`register.csv`](register.csv) |
| 2 | One-page findings memo | [`memo.md`](memo.md) |
| 3 | Automated test (ambiguous PO-5521) | [`test_reconcile.py`](test_reconcile.py) |
| 4 | AI working log | [`AI_LOG.md`](AI_LOG.md) |

## How to run

Requires Python 3. The script uses only the standard library; pytest is needed for the tests. Run from the repo root.

```bash
python reconcile.py          # prints the register and writes register.csv
pip install -r requirements.txt
pytest -v                    # 6 tests
```

Optional arguments: `python reconcile.py [claims.csv] [ledger.csv] [register.csv]`.

## Rules, in the order the code applies them

1. **Match by invoice number**, after removing an optional `INV-` prefix and leading zeros on both sides.
2. **If that fails, fall back to the PO**, but only if exactly one ledger invoice carries it.
3. **More than one invoice on the PO** → `AMBIGUOUS_NO_MATCH`. The claimed amount is never used to pick one.
4. **No invoice and no PO found** → `PHANTOM`.
5. **Matched invoice dated outside 2025-01-01 to 2025-12-31** → `OUT_OF_PERIOD`.
6. **Claimed amount more than $1.00 above the invoice amount** → `AMOUNT_OVERSTATED`.
7. **Otherwise** → `CLEAN_MATCH`.

## Assumptions and decisions

- **$1.00 tolerance is one-sided** (claim above the invoice only). The flag is *overstated*, and a lower claim doesn't expose Northgate.
- **Compared against `invoice_amount`, not `paid_amount`.** The rule is about what was billed, not what was paid.
- **No OCR or fuzzy correction of invoice refs.** Rewriting the retailer's reference until it matches would be guessing.
- **`Decimal` for money.** Float rounding (e.g. `1.0000000000000002`) can flip a result at the exact $1.00 edge.
- **All fields read as text.** This keeps leading zeros (`0088217`), so the register reports the ledger's original value.
- **Standard-library `csv` instead of pandas.** The case allows either, and with 8 rows there are fewer moving parts.
- **Duplicate canonical invoice keys in the ledger raise an error.** Silently keeping one row would be a guess.
- **Dates are compared as ISO `YYYY-MM-DD` text**, which is the format of both files.

## Results

4 `CLEAN_MATCH` · 1 `AMOUNT_OVERSTATED` · 1 `AMBIGUOUS_NO_MATCH` · 1 `OUT_OF_PERIOD` · 1 `PHANTOM` (8 claims, $6,357.65). See [`memo.md`](memo.md) for the recommendation.
