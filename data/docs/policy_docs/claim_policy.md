---
domain: insurance
document_type: policy
topic: claims
version: "1.1"
effective_date: "2025-01-01"
retrieval_conflict_fixture: false
---

# Claims Handling Policy

## Filing a Claim

Claims may be filed through the Meridian app, a branch, or by phone.
Each claim is assigned a claim ID in the format `CLM-XXXXX`.

## Claim Statuses

- **SUBMITTED** — received, not yet reviewed.
- **UNDER_REVIEW** — an adjuster is assessing the claim.
- **APPROVED** — the claim has been accepted for settlement.
- **REJECTED** — the claim did not meet policy terms.

## Settlement Authority

Nexus's `insurance_server.get_claim_status` tool is read-only and carries
no settlement authority. Settlement decisions are made by Meridian's
claims team through internal systems outside the scope of this project.

## Escalation

Any claim-related request that discloses a safeguarding concern or
financial hardship must be routed to a human through Meridian's hard
escalation process, regardless of the claim's own status.
