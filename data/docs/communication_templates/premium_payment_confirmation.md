---
domain: concierge
document_type: communication_template
topic: premium_payment
version: "1.0"
effective_date: "2025-01-01"
---

# Template: Premium Payment Confirmation

**Channel:** CHAT / EMAIL / SMS

**Variables:** `{customer_name}`, `{policy_id_masked}`, `{amount}`, `{due_date}`

---

Hi {customer_name}, this confirms your premium payment of {amount} for
policy {policy_id_masked} has been received. Thank you for banking with
Meridian.

---

**Usage notes:** `{policy_id_masked}` must already be masked to the last
four digits before this template is filled in — masking happens in the
MCP/guardrails layer, never in this template.
