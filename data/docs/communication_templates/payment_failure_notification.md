---
domain: concierge
document_type: communication_template
topic: premium_payment
version: "1.0"
effective_date: "2025-01-01"
---

# Template: Payment Failure Notification

**Channel:** CHAT / EMAIL / SMS

**Variables:** `{customer_name}`, `{policy_id_masked}`, `{grace_period_days}`

---

Hi {customer_name}, we were unable to collect your premium for policy
{policy_id_masked}. You have {grace_period_days} days to make a manual
payment before the policy lapses. If this is due to financial
difficulty, please let us know — we have support options available.

---

**Usage notes:** the final sentence is intentional: it gives the
customer an easy, low-friction way to disclose financial hardship, which
downstream intake classification must route to the
`financial_hardship` hard-escalation category if they respond
affirmatively.
