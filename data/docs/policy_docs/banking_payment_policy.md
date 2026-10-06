---
domain: banking
document_type: policy
topic: account_status_and_payments
version: "1.0"
effective_date: "2025-01-01"
retrieval_conflict_fixture: false
---

# Account Status and Outbound Payments

## Account Statuses

- **ACTIVE** — the account can send and receive funds, including
  scheduled auto-debit collections.
- **DORMANT** — the account has had no customer-initiated activity for
  an extended period. Outbound scheduled debits, including insurance
  auto-debit collections, are blocked until the customer reactivates the
  account through KYC re-verification.

## Why this matters for cross-product requests

A policy's own payment terms (see the insurance payment-policy
documents) describe whether a *policy* supports auto-debit. Whether a
*specific account* can actually fund that auto-debit depends on the
account's own status, which is tracked here in the banking domain and
retrieved live through `banking_server`, never guessed from policy
wording alone.
