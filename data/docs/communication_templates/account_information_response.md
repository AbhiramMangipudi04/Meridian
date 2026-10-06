---
domain: concierge
document_type: communication_template
topic: account_information
version: "1.0"
effective_date: "2025-01-01"
---

# Template: Account Information Response

**Channel:** CHAT / EMAIL

**Variables:** `{customer_name}`, `{account_id_masked}`, `{balance}`, `{account_status}`

---

Hi {customer_name}, your account {account_id_masked} is currently
{account_status}. Your available balance is {balance}. Let us know if
you'd like a full statement or recent transaction history.

---

**Usage notes:** `{balance}` and `{account_id_masked}` must come from a
live `banking_server` tool call, never from this knowledge base — this
template only supplies wording.
