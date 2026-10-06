---
domain: insurance
document_type: policy
topic: premium_payment
version: "1.2"
effective_date: "2025-01-01"
retrieval_conflict_fixture: false
---

# Meridian General Insurance — Premium Payment Policy

## Scope

This document describes how premiums are collected across Meridian's
General Insurance, Health, Motor, and Home policy lines.

## Payment Methods

Meridian supports the following premium payment methods, subject to the
terms recorded on the individual policy record:

- **Manual payment** — the policyholder initiates payment each cycle via
  net banking, UPI, or a Meridian branch.
- **Auto-debit** — premiums are collected automatically from a linked
  bank account on the due date, if the policy's payment terms enable it.

## Frequency

Premiums may be billed MONTHLY, QUARTERLY, or ANNUALLY, as recorded on
the policy.

## Authoritative Source

The payment method and auto-debit eligibility for any individual policy
are authoritative in the structured policy record (`policies.payment_method`,
`policies.auto_debit_supported`), not in this general document. This
document explains the *program*, not any one customer's current terms.

## Grace Period

A payment grace period of 15 days applies after a missed premium
collection before a policy is marked LAPSED.
