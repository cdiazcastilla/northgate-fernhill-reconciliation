# Findings Memo: Fernhill Mart Deduction Claims

**To:** Northgate Finance · **Re:** 8 deduction claims from Fernhill Mart, $6,357.65 in total

## How we tested the claims

We treated each Fernhill claim as an assertion, not as proof. We confirmed it only when Northgate's own invoice records supported it. A claim had to point to a real Northgate invoice dated in 2025, and its amount could not exceed that invoice by more than $1.00.

## Results by outcome

| Outcome | What it means | Claims | Amount claimed |
|---|---|---:|---:|
| Clean match | Real 2025 invoice, amount agrees | 4 | $3,624.90 |
| Overstated amount | Real invoice, but the claim is higher than the invoice | 1 | $412.00 |
| Ambiguous | Cannot tell which invoice the claim refers to | 1 | $915.75 |
| Out of period | Invoice dated before 2025 | 1 | $875.00 |
| Phantom | No matching invoice or purchase order in our records | 1 | $530.00 |
| **Total** | | **8** | **$6,357.65** |

## Recommendation

| | Amount |
|---|---:|
| **Concede** | **$4,004.90** |
| **Dispute** | **$1,437.00** |
| **On hold** until Fernhill names the invoice | **$915.75** |

| Claim | Outcome | Claimed | Action |
|---|---|---:|---|
| CLM-4401 | Clean match | $1,180.00 | Concede. |
| CLM-4402 | Clean match | $642.50 | Concede. Fernhill wrote the invoice number without its leading zeros; it is the same invoice. |
| CLM-4403 | Overstated | $412.00 | Concede $380.00, the invoice value. Dispute the $32.00 excess. |
| CLM-4404 | Ambiguous | $915.75 | Hold. No invoice number was given, and the purchase order covers two invoices ($915.75 and $210.00). Ask Fernhill to name the specific invoice before conceding anything. A matching amount alone is not proof. |
| CLM-4405 | Clean match | $300.00 | Concede. It is $0.01 above the invoice, within tolerance. |
| CLM-4406 | Out of period | $875.00 | Dispute in full. The invoice is dated November 2024, outside the 2025 audit. The claim was filed in 2025, but the invoice date is what counts. |
| CLM-4407 | Phantom | $530.00 | Dispute in full. Neither the invoice nor the purchase order exists in our records. |
| CLM-4408 | Clean match | $1,502.40 | Concede. The invoice number was mistyped (letters instead of zeros), but the purchase order points to exactly one invoice, and the amount agrees. |

## Observations

- **Every invoice in our records is shown as paid**, yet Fernhill presents these as deductions against *unpaid* invoices. Three invoices were paid in full *before* the claim arrived (CLM-4401, 4406, 4408). For the other three matched claims, Fernhill filed the claim and then paid the invoice in full anyway (CLM-4402, 4403, 4405). Before issuing any credit, confirm whether Fernhill expects a refund or plans to deduct from a future payment, so the same amount is not recovered twice.
- **INV-10611 was short-paid by $0.02** ($299.97 received against $299.99 invoiced). The amount is immaterial, but it is worth noting alongside CLM-4405, which relates to the same invoice.
- **The conceded claims are each close to 100% of their invoice value.** The records confirm that these invoices exist and what was billed. They cannot confirm that the shortage or pricing problem actually happened. We recommend asking for standard backup (proof of delivery, price agreement) before credit is issued.
