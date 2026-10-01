# AI Working Log

I used Claude (Claude Code) for this exercise. My way of working: I write the
spec, the AI writes the code and opens a pull request, and I review it, check
it against the data, and merge it myself. One step at a time.

---

## Phase 0 — First try (before this repo)

At the start I just pasted the assessment and the files and asked for help.
The AI gave me a full solution in one shot.

I didn't use it. It worked, but I couldn't explain every line, and the case
says I have to own every row of the register. So I opened a clean repo and
started again, step by step, writing my own prompts with the real rules.

---

## Prompt 1 — Reconciliation script

**Prompt (verbatim):**
```
I'm doing a take-home reconciliation exercise. Files in this folder:
fernhill_claims.csv (retailer's claims) and northgate_ledger.csv (vendor's
independent ledger = ground truth). Claims are hypotheses, never evidence.

Write reconcile.py (stdlib csv only, no pandas). Read ALL fields as strings;
never parse invoice numbers as ints.

Output register.csv with one row per claim: claim_id, matched_invoice
(original ledger value or blank), status_flag, note.

Rules, apply exactly:
1. ID canonicalization: strip optional "INV-" prefix (case-insensitive) and
   leading zeros before comparing. "0088217" == "88217" == "INV-88217". Do NOT
   do fuzzy/OCR correction (e.g. O->0); a garbled ref simply fails to resolve.
2. Matching order: invoice_ref first. If blank or unresolved, fall back to
   po_ref ONLY if exactly one ledger invoice has that PO. If >1 ledger invoices
   share the PO -> AMBIGUOUS_NO_MATCH, matched_invoice blank. Never use amount
   to break the tie.
3. No resolution via invoice or PO -> PHANTOM.
4. Once matched: if ledger invoice_date is outside 2025-01-01..2025-12-31 ->
   OUT_OF_PERIOD (based on invoice date, not claim date).
5. Else if claimed_amount - invoice_amount > 1.00 -> AMOUNT_OVERSTATED.
   Compare to invoice_amount, not paid_amount. Use Decimal, not float.
6. Else CLEAN_MATCH.

Notes must be specific: say whether matched by invoice or by PO fallback, the
amount difference, and for ambiguous cases list the candidate invoices.

Print the register to stdout too. Don't write tests or a memo yet.
```

**Why I wrote it like this:** I didn't want to just say "reconcile these two
files". I put the exact rules from the case in the prompt, and I added the
traps I saw when I read the data:
- `0088217` vs `88217` → read everything as text, or the zeros disappear.
- `INV-1O6OO` has letters, not zeros → I said no "smart" correction.
- PO-5521 has two invoices → I said never pick one by amount.
- One invoice is from 2024 → the date that counts is the invoice date.

**Result:** PR #1.

| Claim | Matched | Flag |
|---|---|---|
| CLM-4401 | INV-10432 | CLEAN_MATCH |
| CLM-4402 | 0088217 | CLEAN_MATCH |
| CLM-4403 | INV-10501 | AMOUNT_OVERSTATED (+32.00) |
| CLM-4404 | — | AMBIGUOUS_NO_MATCH |
| CLM-4405 | INV-10611 | CLEAN_MATCH (+0.01) |
| CLM-4406 | INV-09988 | OUT_OF_PERIOD |
| CLM-4407 | — | PHANTOM |
| CLM-4408 | INV-10600 | CLEAN_MATCH (by PO) |

**Something the AI added that I didn't ask for:** if two invoices in the ledger
end up with the same ID after cleaning, the script stops with an error. I kept
it. Quietly keeping one of them would be guessing, and guessing is exactly
what the rules say not to do.

**A decision I had to make:** the AI pointed out that my rule 5 only checks
one direction. If a claim is more than $1 *below* the invoice, it still comes
out as CLEAN_MATCH. The case says "within $1.00", so you could read it both
ways. I kept it one-sided: the flag is called *overstated*, and a claim that
asks for less money doesn't hurt Northgate. In this data it doesn't change
anything, but I wanted to decide it on purpose.

---

## Checking PR #1 before merging

**Prompt (translated from Spanish):**
> Check: that it uses Decimal, that precedence is period → amount, and that
> 4404 is NOT matched to INV-10517. If anything doesn't match your table, it
> goes in the log as an "override".

The AI showed me where each thing is in the code:
1. Money uses `Decimal`, not float. With float, `0.1 + 0.2 > 0.3` is True,
   and that kind of error matters when the limit is exactly $1.00.
2. The date check runs before the amount check. It tried a fake 2024 invoice
   with a wrong amount, and it came out OUT_OF_PERIOD.
3. CLM-4404 stays blank even though INV-10517 is exactly 915.75.

Then I checked the 8 claims myself. For each one I opened both CSVs and used
`grep` to find the invoice or PO in the ledger, and I did the math by hand:
- **CLM-4402:** the ledger has `0088217`. Without the zeros it's the same
  invoice, same amount.
- **CLM-4404:** `grep PO-5521` gave me two lines. This is the one that made
  me stop. INV-10517 is 915.75, exactly the claim amount, so it *looks* like
  an obvious match. But there are two invoices on that PO, and choosing by
  amount is just guessing.
- **CLM-4405:** I compared against `invoice_amount` (299.99), not
  `paid_amount` (299.97). The difference is 0.01, so it's fine.
- **CLM-4406:** the invoice is from 2024-11-02. The claim is from 2025, but
  that doesn't matter.
- **CLM-4407:** neither the invoice nor the PO exists in the ledger.
- **CLM-4408:** `1O6OO` finds nothing, but PO-5530 has only one invoice
  (INV-10600), so the fallback is allowed.

All 8 matched what the script gave. **No override needed.**

**Something I noticed outside the rules:** every invoice in the ledger is
already paid, and some were paid *before* the claim arrived. For example,
INV-10432 was paid on 03-01 and CLM-4401 came on 03-05, for 100% of the
invoice. The rules don't cover this, so no flag changes, but I'll mention it
in the memo.

---

## Prompt 2 — Tests

**Prompt (verbatim):**
```
Add test_reconcile.py using pytest. Refactor reconcile.py if needed so the
matching logic is importable as a function (no file I/O inside it).

Required test: claim with blank invoice_ref, po_ref PO-5521, amount 915.75
against the real ledger -> status AMBIGUOUS_NO_MATCH and matched_invoice
blank, even though 915.75 exactly equals INV-10517's amount. Assert both
conditions.

Also add small tests for: leading-zero normalization (88217 vs 0088217),
OUT_OF_PERIOD using invoice date not claim date, $1.00 tolerance boundary
(1.00 over = clean, 1.01 over = overstated), and garbled ref INV-1O6OO
falling back to unique PO-5530.

Run pytest and show me the output.
```

**Result:** PR #2. 6 tests, all pass. No refactor was needed, because the
matching functions already worked without reading files.

**How I know the main test is real:** a test that can never fail doesn't
prove anything. So the AI broke the code on purpose and made it pick the PO
by amount. The PO-5521 test failed, like it should. Then it put the code back
and all 6 passed again.

I also like that the test first checks that INV-10517 really is 915.75. If
someone changes the data, the test tells you the trap is gone instead of
passing for the wrong reason.

After merging, I ran `python reconcile.py` and `pytest -v` in my Codespace:
same register, 6 passed.

---

## Prompt 3 — Skeptical review before the memo

**Prompt (verbatim):**
```
Before the memo, act as a skeptical reviewer. For each of the 8 claims, show
the raw claim row, the ledger row(s) considered, and which rule fired. Then
tell me any case where a reasonable reviewer could argue for a different flag,
and why your choice follows the written rules. Don't change code unless you
find an actual bug.
```

**Why I asked this:** the register looked right, but "looks right" isn't
enough. Before writing a memo that tells Finance to concede or dispute real
money, I wanted the AI to argue *against* its own results, so I could see if
any flag was weak.

**What came back:** a trace of all 8 claims with the raw rows, plus six
possible objections. The ones I think matter most:
- **CLM-4404:** "it's obviously INV-10517". This is the trap of the exercise.
  The rule says no, and I agree: the amount comes from Fernhill, so using it
  to choose the invoice is using the claim to prove itself.
- **CLM-4408:** the opposite argument, "the invoice number doesn't exist, so
  it's PHANTOM". But PHANTOM means *neither* the invoice *nor* the PO
  resolves, and here the PO points to exactly one invoice. The match comes
  from Northgate's ledger, not from Fernhill.
- **CLM-4406:** "the claim is from 2025". The rule says the invoice date is
  what counts. The amount matches exactly, so the flag depends only on the
  date.
- **CLM-4403:** "concede $380 and dispute only the $32". That's not a flag
  question, it's a recommendation, so I took it to the memo.

It also checked a few things I hadn't asked for: the claim PO matches the
ledger PO for every matched claim, and no invoice is claimed twice.

**Bug check:** no bug affects the 8 results, so no code changed. It found one
edge case: an invoice made only of zeros (`INV-000`) would be treated as
blank. That can't happen with this data and isn't realistic, so I left it
alone.

**The detail that changed my memo:** my earlier note said every invoice was
already paid. The trace made it more precise:
- 4401, 4406 and 4408 were paid *before* the claim arrived.
- For 4402, 4403 and 4405, Fernhill filed the claim first and then paid the
  invoice in full anyway.

Either way, Fernhill is not deducting from an unpaid invoice.

---

## Prompt 4 — Findings memo

**Prompt (verbatim):**
```
Write memo.md, max one page, for a non-technical finance reader who won't open
the code.
Include: counts and $ by flag (table), total claimed; recommendation per
claim: concede CLEAN_MATCH; dispute PHANTOM and OUT_OF_PERIOD in full; for
AMOUNT_OVERSTATED concede the ledger amount and dispute only the excess; for
AMBIGUOUS request Fernhill provide the specific invoice number before any
concession.
Also note as observations: every ledger invoice shows as paid, which conflicts
with Fernhill deducting against "unpaid" invoices; and INV-10611 was
short-paid $0.02.
Plain language, no code references.
```

**Decisions that were mine, not the AI's:**
- **CLM-4403:** concede the $380 invoice value and dispute only the $32
  excess. The ledger confirms the invoice exists and that $380 was billed, so
  the real problem is only the part above it. A SHORTAGE can't be bigger
  than the whole invoice, which is exactly why that part is disputed.
- **CLM-4404:** "on hold", not disputed and not conceded. The claim could be
  valid, but nobody can say which invoice it's about. The fair next step is
  to ask Fernhill for the invoice number.
- **The two observations** (all invoices paid, the $0.02 short payment) came
  from my own check of the ledger and from the Prompt 3 trace.

**Result:** PR #3, `memo.md`, about 575 words.

| | Amount |
|---|---:|
| Concede | $4,004.90 |
| Dispute | $1,437.00 |
| On hold (CLM-4404) | $915.75 |
| **Total claimed** | **$6,357.65** |

**How I checked it:** the totals were recalculated from the CSVs, not typed
from memory, and concede + dispute + hold adds up to the total claimed. The
AI also confirmed from the data that *no* ledger invoice is unpaid and that
INV-10611 is the *only* short payment.

**Something the AI added that I didn't ask for:** a third observation. The
conceded claims are each close to 100% of their invoice, so Northgate should
ask for proof (proof of delivery, price agreement) before issuing credit. I
kept it. It follows from the governing rule: the ledger confirms that the
invoice exists, but not that the shortage happened.

---

## Prompt 5 — README

**Prompt (verbatim):**
```
Write README.md for the repo. Audience: the reviewer at The Hawkers Club who
will clone it and wants to run it in 2 minutes and understand my approach.

Include:
1. What this is, in 2-3 lines: reconciling Fernhill's deduction claims against
   Northgate's independent ledger>
    ledger = ground truth
    claims = hypotheses.
2. Deliverables map: which file is each of the 4 deliverables (script +
   register.csv, memo.md, test_reconcile.py, AI_LOG.md).
3. How to run: exact commands for the script and for pytest. Add a
   requirements.txt with only what is actually needed (pytest; the script
   itself is stdlib only).
4. Rules applied, in plain words and in the order the code checks them:
   match by invoice
   > PO fallback only if unique
   > PHANTOM ->
   > OUT_OF_PERIOD
   > AMOUNT_OVERSTATED
   > CLEAN_MATCH.
5. Assumptions and decisions, each with a one-line reason:
   - $1.00 tolerance is one-sided (claimed above invoice only)
   - compared against invoice_amount, not paid_amount
   - no OCR/fuzzy correction of invoice refs
   - Decimal for money
   - all fields read as text
   - stdlib csv instead of pandas (case allows either; 8 rows, fewer moving
     parts)
   - duplicate canonical invoice keys in the ledger raise an error
6. Results summary: one line with counts by flag and a link to memo.md.

Constraints and guardrails:
- Only describe what the code actually does.
- If something in this prompt doesn't match the code, tell me instead of writing it.
- Run every command you put in the README and show me the output.
- Keep it short: a reviewer should read it in under 2 minutes.
- Don't change reconcile.py or the tests.
```

**Why I wrote it like this:** a README that says something the code doesn't
do is worse than no README. So I told the AI to check my own prompt against
the code, and to run every command before writing it down.

**The guardrail caught my mistake:** in my list of rules I forgot
AMBIGUOUS_NO_MATCH. The AI told me, and it put it back in the right place,
right after the PO fallback. That's the rule the whole exercise is built
around, so I'm glad it didn't just copy my list.

**Something the AI added that I didn't ask for:** one more assumption, "dates
are compared as text in YYYY-MM-DD format". I kept it. It's true in the code,
and if another date format ever showed up, the period check would break.

**About pandas:** the general assessment brief says "Python and pandas", but
the case itself says "plain stdlib or pandas, your choice". With 8 rows I
went with the standard library so there's less to install and less to go
wrong. I wrote the reason in the README so the reviewer doesn't have to ask.

**Result:** PR #4, `README.md` (about 400 words) and `requirements.txt` (just
pytest). The AI ran every command in a fresh copy of the repo: the script
printed the 8-row register and pytest gave 6 passed. `reconcile.py` and the
tests were not touched.

---

## Looking back

How I tried to steer the AI, mapped to what the case says it looks for:

- **Specification:** every prompt carried the real rules: the audit window,
  the $1.00 tolerance, the ambiguous-PO guard, and the traps I had seen in the
  data. I never just said "reconcile these files".
- **Verification:** I checked all 8 claims by hand against the raw CSVs with
  `grep`, asked for a test that is proven to fail when the logic guesses,
  and ran everything myself in my Codespace.
- **Judgment:** the one-sided tolerance, CLM-4403 (concede $380, dispute
  $32), CLM-4404 on hold instead of matched by amount, and stdlib over
  pandas were all my decisions, and each one has its reason above.
- **Ownership:** I threw away the first one-shot solution because I couldn't
  defend it. Every result in this repo is one I can explain, and every PR was
  reviewed and merged by me.
