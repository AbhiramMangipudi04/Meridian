---
domain: insurance
document_type: policy
topic: premium_payment
version: "1.0"
effective_date: "2023-04-01"
retrieval_conflict_fixture: true
---

# Auto-Debit for Premium Payments (Program Overview)

> **Note on this document's age:** this is the original 2023 program
> announcement. It is intentionally broad and does not reflect
> account-level restrictions introduced later. It is kept in the
> knowledge base so the retrieval layer has a realistic case where
> general wording must be reconciled against current structured data
> rather than taken at face value.

## Summary

Auto-debit is available for all active General Insurance, Health, and
Motor policies with a monthly or quarterly premium frequency. Once
enabled, Meridian will automatically collect the premium from the
customer's linked bank account on the due date, with no action required
from the customer.

## How it works

1. The customer links a savings or current account to the policy.
2. Meridian schedules a debit for each due date.
3. If the debit fails, the customer is notified and has a 15-day grace
   period to pay manually before the policy lapses.

## Eligibility (as originally published)

Any active policy with a linked bank account is eligible for auto-debit.

---

**Important — retrieval-conflict fixture:** this document does not
mention that a *linked account's own status* (e.g. DORMANT) can block an
auto-debit collection even when the policy itself supports auto-debit.
That restriction exists only in the structured banking data
(`accounts.status`), which must be treated as authoritative over this
document whenever the two disagree. The response-drafting and validation
agents are expected to surface that conflict rather than resolve it
silently in either direction.
