# Nexus — Data Module + MCP Server Layer

This repository implements the **Data module** and the **MCP Server
Layer** of the Nexus capstone (Meridian Financial Group's unified AI
concierge). It does **not** implement the structured-intake/classification
module, the hybrid-retrieval/RAG pipeline, or the multi-agent
orchestration layer — those are future layers that will *consume* the
four MCP servers built here. See the Data module brief and the MCP
Server Layer specification for the full system context this repository
exists inside of.

Sections 1–12 below describe the Data module (tables, repositories,
seeding, isolation at the database layer). Sections 13 onward describe
the MCP Server Layer built on top of it (the four FastMCP servers,
caller scopes, guardrails, logging, and how to run/test everything).

## 1. Project Structure

```
project/
├── database.py                 # CLI: create schema / seed
├── requirements.txt
├── pytest.ini
├── common/                       # MCP server layer infrastructure (§13+)
│   ├── validate.py                # input validation -- always runs first
│   ├── guardrails.py               # scope enforcement, minimization, masking,
│   │                                # sanitization, PII redaction, output grounding
│   ├── logging_config.py           # @trace(logger) structured JSON-lines tracing
│   ├── errors.py                   # client-safe typed error hierarchy
│   └── knowledge_base.py           # knowledgebase:// resource's document access
├── servers/                      # the four FastMCP servers (§13+)
│   ├── banking_server.py
│   ├── insurance_server.py
│   ├── wealth_server.py
│   └── concierge_ops_server.py
├── data/
│   ├── validation.py            # business-ID format regexes (shared everywhere)
│   ├── database/
│   │   ├── connection.py         # engine, WAL mode, schema creation
│   │   ├── session.py            # domain-restricted session factory + enforcement
│   │   └── access_control.py     # SERVER_TABLE_ACCESS matrix + exception type
│   ├── models/
│   │   ├── base.py
│   │   ├── banking/      (account.py, transaction.py)
│   │   ├── insurance/    (policy.py, claim.py)
│   │   ├── wealth/       (portfolio.py, investment_product.py)
│   │   └── concierge/    (customer.py, interaction_log.py, escalation_flag.py, audit_log.py)
│   ├── repositories/
│   │   ├── base_repository.py    # generic create/read_all/read_by_id/update
│   │   ├── errors.py
│   │   └── banking/ insurance/ wealth/ concierge/   (one repository per model)
│   ├── seed/
│   │   ├── ids.py        # deterministic ID/name generators + showcase constants
│   │   ├── seed.py        # orchestrator: concierge -> banking -> insurance -> wealth
│   │   └── banking_seed.py / insurance_seed.py / wealth_seed.py / concierge_seed.py
│   └── docs/
│       ├── communication_templates/
│       ├── policy_docs/
│       ├── product_docs/
│       └── faqs/
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_repositories.py
    ├── test_seed.py
    ├── test_server_data_isolation.py
    ├── test_caller_scope.py
    ├── test_mcp_tools.py
    ├── test_mcp_resources.py
    ├── test_mcp_prompts.py
    ├── test_guardrails.py
    ├── test_logging.py
    └── test_fastmcp_registration.py
```

## 2. Database Architecture

A single SQLite file, `meridian.db`, holds all four domains' tables
(WAL mode + `PRAGMA foreign_keys=ON`, set on every new connection in
`data/database/connection.py`). Physically sharing one file is allowed by
the brief **as long as logical access is still restricted per server** —
see §10 below for how that is actually enforced, not just documented.

## 3. Domain Ownership

| Domain     | Tables                                                        |
|------------|----------------------------------------------------------------|
| BANKING    | `accounts`, `transactions`                                     |
| INSURANCE  | `policies`, `claims`                                            |
| WEALTH     | `portfolios`, `investment_products`                              |
| CONCIERGE  | `customers`, `interaction_log`, `escalation_flags`, `audit_log` |

This mapping lives in exactly one place: `data/database/access_control.py`
(`SERVER_TABLE_ACCESS`). Nothing else re-declares it.

## 4. Server Data-Access Matrix

| Server                  | Allowed tables                                                | Tools it implements (servers/*.py)                                              |
|--------------------------|----------------------------------------------------------------|----------------------------------------------------------------------------------|
| `banking_server`         | `accounts`, `transactions`                                     | `get_account_summary`, `get_transaction_history`, `get_linked_accounts`         |
| `insurance_server`       | `policies`, `claims`                                            | `get_policy_details`, `check_coverage_clause`, `get_claim_status`               |
| `wealth_server`          | `portfolios`, `investment_products`                              | `get_portfolio_summary`, `get_investment_product_details`, `check_product_suitability` |
| `concierge_ops_server`   | `customers`, `interaction_log`, `escalation_flags`, `audit_log` | `get_customer_kyc_status`, `run_escalation_check`, `send_customer_notification`, `write_audit_log` |

## 5. Foreign-Key Rules

Foreign keys exist **only within a domain**:

- `transactions.account_id_fk -> accounts.id` (banking -> banking) ✅
- `claims.policy_id_fk -> policies.id` (insurance -> insurance) ✅
- No table has a foreign key into `customers`, and no table in one
  domain has a foreign key into another domain's table. `tests/test_models.py`
  asserts this at the mapper level (inspecting `Column.foreign_keys`), not
  just by code review.
- No cross-domain SQLAlchemy `relationship()` exists anywhere — every
  `relationship()` in the codebase points at a mapper in the *same*
  domain, which is also asserted directly in `test_models.py`.

## 6. Cross-Domain Business ID Strategy

Instead of foreign keys, cross-domain links use plain string columns
validated against fixed formats in `data/validation.py`:

| Field                        | Format          | Example         |
|-------------------------------|------------------|------------------|
| `customer_business_id`        | `CUS-XXXXX`      | `CUS-20077`      |
| `account_business_id`         | `ACC-XXXXX`      | `ACC-20077`      |
| `policy_business_id`          | `POL-XX-XXXXX`   | `POL-IN-30091`   |
| `portfolio_business_id`       | `PORT-XXXXX`     | `PORT-10001`     |
| `product_business_id`         | `PROD-XX-XX`     | `PROD-EQ-01`     |
| `claim_business_id`           | `CLM-XXXXX`      | `CLM-50001`      |

These formats come directly from the capstone assignment's Security &
Guardrails requirements (§4) so that this module's data already matches
what the future MCP tool/resource argument validation will expect.
Every model validates its own business-ID fields in `__init__`.

## 7. Seeding Process

```
python database.py --seed
```

`data/seed/seed.py` runs each domain's seed module in a fixed order —
**Concierge → Banking → Insurance → Wealth** — using an *unrestricted*
session (seeding is infrastructure, not server traffic). Each
`seed_*` module:

- is **deterministic**: all randomness flows through one
  `random.Random(SEED)` instance in `data/seed/ids.py`;
- is **idempotent**: every insert first checks `read_by_id(business_id)`
  and skips if the row already exists, so re-running
  `python database.py --seed` never raises `DuplicateBusinessIdError`
  and never duplicates rows (`tests/test_seed.py::test_seed_is_idempotent`).

Seed volumes follow the brief's guidelines: ~40–50 customers, ~50–70
accounts, ~220 transactions, ~40 policies, ~20 claims, ~20 portfolios,
~12 investment products, ~45 interaction-log rows, 8 escalation flags.

## 8. Showcase Data

Explicit, hardcoded fixtures (never generated) in `data/seed/ids.py`:

```
SHOWCASE_CUSTOMER_ID = "CUS-20077"   # Arjun Mehta
SHOWCASE_ACCOUNT_ID  = "ACC-20077"   # savings account
SHOWCASE_POLICY_ID   = "POL-IN-30091" # general insurance policy, auto_debit_supported=True
```

`banking_server` can retrieve `ACC-20077` and its transactions;
`insurance_server` can retrieve `POL-IN-30091` and its payment terms;
`concierge_ops_server` can retrieve `CUS-20077`'s KYC/escalation data —
each strictly through its own repository/session, never by reaching
across domains.

## 9. Unstructured Knowledge Base

`data/docs/` contains Markdown documents with YAML front matter
(`domain`, `document_type`, `topic`, `version`, `effective_date`, and
`retrieval_conflict_fixture` where relevant) so a future RAG pipeline can
filter/rank by metadata without any code changes here:

- `communication_templates/` — 4 customer-facing message templates
- `policy_docs/` — general insurance payment policy, the **auto-debit
  retrieval-conflict fixture** (`premium_auto_debit_policy.md`, deliberately
  broad 2023 wording that omits the account-status restriction tracked in
  `banking_payment_policy.md`), claim policy, banking payment policy
- `product_docs/` — equity/debt/hybrid-and-gold fund overviews
- `faqs/` — general FAQs and an auto-debit-specific FAQ

The retrieval-conflict fixture is intentional: a future hybrid-retrieval
layer must treat the **structured** `policies.auto_debit_supported` /
`accounts.status` fields as authoritative over this older document's
general wording, and surface the conflict rather than silently resolving
it — this module only prepares the data, it does not implement that
reconciliation logic.

## 10. Data Isolation Mechanism (the important part)

Isolation is enforced with real code, not a comment. Two SQLAlchemy event
hooks are registered once on the `Session` class in `data/database/session.py`:

1. **`do_orm_execute`** — fires for every `session.execute(select/update/
   delete/insert(...))` and every legacy `session.query(...)` call (Query
   compiles through the same execution path in SQLAlchemy 1.4/2.0). The
   hook inspects the compiled statement's `FROM`/target table(s) and
   compares them against the session's allowed table set.
2. **`before_flush`** — fires when `session.add()` / `session.delete()`
   changes are about to be flushed via `commit()`. This path does **not**
   go through `do_orm_execute`, so without this second hook a restricted
   session could bypass the allowlist simply by calling
   `session.add(SomeOtherDomainRow())`. `before_flush` inspects
   `session.new`, `session.dirty`, and `session.deleted` directly.

Both hooks look for a plain attribute (`_nexus_domain_server`) set by:

```python
banking_db = create_domain_database_access(server="banking_server")
insurance_db = create_domain_database_access(server="insurance_server")
```

Any statement or flush touching a table outside that server's allowlist
raises `UnauthorizedTableAccessError` — even though `accounts`, `policies`,
`portfolios`, and `customers` all live in the same `meridian.db` file.
Repositories never see or control this; they are simply handed a session
and have no way to escape it.

```
                    meridian.db
                        │
        ┌───────────────┼────────────────┐
        │               │                │
   Banking          Insurance          Wealth
   ───────           ─────────          ─────
   accounts          policies           portfolios
   transactions      claims             investment_products

                        │
                  Concierge Ops
                  ──────────────
                  customers
                  interaction_log
                  escalation_flags
                  audit_log
```

## 11. How to Run Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest   # already in requirements.txt, listed for clarity

python database.py --seed
pytest tests/ -v
```

`tests/test_server_data_isolation.py` is the key file: it proves, for
every server, both that its *own* tables are reachable (positive tests)
and that every *other* domain's tables are rejected — via the repository
layer, via raw `session.execute(select(...))`, and via the
`session.add()` + `commit()` write path — rather than only inspecting the
`SERVER_TABLE_ACCESS` configuration constant.

## 12. Examples of Allowed vs. Forbidden Access

```python
from data.database.session import create_domain_database_access
from data.repositories.insurance.policy_repository import PolicyRepository
from data.repositories.banking.account_repository import AccountRepository

insurance_db = create_domain_database_access(server="insurance_server")

# Allowed: insurance_server reading its own table.
policy = PolicyRepository(insurance_db).read_by_id("POL-IN-30091")

# Forbidden: insurance_server reaching into banking's table.
AccountRepository(insurance_db).read_all()
# -> raises UnauthorizedTableAccessError
```

---

# MCP Server Layer

## 13. Architecture

```
            Nexus Orchestrator (not yet implemented)
                    │          │          │          │
                    ▼          ▼          ▼          ▼
            banking_server  insurance_server  wealth_server  concierge_ops_server
                    │          │          │          │
                    └──────────┴────┬─────┴──────────┘
                                     ▼
                      create_domain_database_access(server=...)
                                     │
                                     ▼
                                meridian.db
```

Each server is one standalone `fastmcp.FastMCP` instance, run as its own
HTTP process. Every server:

- imports **only** its own domain's repositories (`servers/banking_server.py`
  imports nothing from `data/repositories/insurance|wealth|concierge/`, etc.)
- constructs **exactly one** domain-restricted session at import time via
  `create_domain_database_access(server=...)` — the same enforcement
  mechanism described in §10, now backing live MCP tool calls
- validates every identifier argument (`common/validate.py`) **before**
  any repository call
- applies caller-scope checks, field minimization, and business-ID
  masking (`common/guardrails.py`) **after** the repository call, before
  returning
- traces every Tool/Resource/Prompt invocation as structured JSON
  (`common/logging_config.py`)

## 14. The Four Servers

| Server | File | Port (default) | Owns |
|---|---|---|---|
| Banking | `servers/banking_server.py` | 8001 | `accounts`, `transactions` |
| Insurance | `servers/insurance_server.py` | 8002 | `policies`, `claims` |
| Wealth | `servers/wealth_server.py` | 8003 | `portfolios`, `investment_products` |
| Concierge Ops | `servers/concierge_ops_server.py` | 8004 | `customers`, `interaction_log`, `escalation_flags`, `audit_log` |

### Startup commands

```bash
python -m servers.banking_server
python -m servers.insurance_server
python -m servers.wealth_server
python -m servers.concierge_ops_server
```

Each is an independent HTTP process (FastMCP's `mcp.run(transport="http", ...)`
— never stdio). Host/port are configurable per server via environment
variables, with localhost defaults:

| Server | Host var | Port var |
|---|---|---|
| Banking | `BANKING_SERVER_HOST` | `BANKING_SERVER_PORT` |
| Insurance | `INSURANCE_SERVER_HOST` | `INSURANCE_SERVER_PORT` |
| Wealth | `WEALTH_SERVER_HOST` | `WEALTH_SERVER_PORT` |
| Concierge Ops | `CONCIERGE_SERVER_HOST` | `CONCIERGE_SERVER_PORT` |

The database itself is also path-configurable: `MERIDIAN_DB_PATH`
(read once, at `data/database/connection.py` import time).

## 15. Caller Scopes

Five explicit, closed-set roles (`common/validate.ALLOWED_CALLER_SCOPES`)
— arbitrary scope strings are rejected with a typed `ValidationError`:

| Scope | Sees | Cannot see |
|---|---|---|
| `user` | their own account / portfolio / policy data only | any other customer's data |
| `bank_manager` | all of Banking | Insurance, Wealth |
| `policy_manager` | all of Insurance | Banking, Wealth |
| `wealth_manager` | all of Wealth | Banking, Insurance |
| `operations` | all of Concierge | Banking, Insurance, Wealth |

`get_account_summary`, `get_linked_accounts`, and `get_portfolio_summary`
carry `caller_scope` (and an additional `caller_customer_id` used only to
enforce the `user`-scope ownership rule) in their literal required
signature, per the spec. The remaining tools' spec signatures do not
include `caller_scope` at all (`get_policy_details(policy_id)`,
`get_claim_status(claim_id)`, `get_investment_product_details(product_id)`,
`check_product_suitability(product_id, risk_profile)`,
`get_customer_kyc_status(customer_id)`); for these, `caller_scope` is an
**optional** parameter (default `None`, skipping the check) so the exact
spec call pattern still works unmodified, while still giving
`tests/test_caller_scope.py` a real mechanism to exercise Policy
Manager/Wealth Manager/Operations role restrictions when a caller does
supply it.

Field minimization (`common/guardrails.minimize_account_fields` /
`minimize_portfolio_fields`) differs by scope: a `user` sees their own
business-relevant fields only; `bank_manager`/`wealth_manager` additionally
see `customer_business_id` and record timestamps. Account/policy/portfolio
numbers are masked to the last four characters (`mask_business_id`) in
**every** case, regardless of scope.

## 16. Tool Inventory (13 total)

| # | Server | Tool | Op |
|---|---|---|---|
| 1 | Banking | `get_account_summary(account_id, caller_scope, caller_customer_id=None)` | Read |
| 2 | Banking | `get_transaction_history(account_id, limit=20)` | Read |
| 3 | Banking | `get_linked_accounts(customer_id, caller_scope="user", caller_customer_id=None)` | Read |
| 4 | Insurance | `get_policy_details(policy_id, caller_scope=None)` | Read |
| 5 | Insurance | `check_coverage_clause(policy_id, scenario_tag, caller_scope=None)` | Read |
| 6 | Insurance | `get_claim_status(claim_id, caller_scope=None)` | Read |
| 7 | Wealth | `get_portfolio_summary(portfolio_id, caller_scope, caller_customer_id=None)` | Read |
| 8 | Wealth | `get_investment_product_details(product_id, caller_scope=None)` | Read |
| 9 | Wealth | `check_product_suitability(product_id, risk_profile, caller_scope=None)` | Read |
| 10 | Concierge | `get_customer_kyc_status(customer_id, caller_scope=None)` | Read |
| 11 | Concierge | `run_escalation_check(customer_id, request_category, draft_confidence)` | Read (+ writes an audit entry, and an escalation flag if escalated) |
| 12 | Concierge | `send_customer_notification(customer_id, channel, message)` | Write |
| 13 | Concierge | `write_audit_log(action_type, performed_by, customer_id, outcome, details="")` | Write |

`check_coverage_clause` and `check_product_suitability` are fully
deterministic (`servers/insurance_server._COVERAGE_CLAUSE_EVALUATORS`,
`servers/wealth_server._is_suitable`) — no LLM is involved in either
decision. `run_escalation_check` checks the three hard categories
(`financial_hardship`, `safeguarding_concern`, `compliance_override_request`)
**before** any confidence-based logic (`servers/concierge_ops_server._decide_escalation`);
a hard category escalates unconditionally regardless of confidence, and
every decision — escalated or not — is written to `audit_log`.
`write_audit_log` writes exactly one row; it is never called by its own
helper internals, so auditing never recursively audits itself.

## 17. Resource Inventory (4 total)

| Resource URI | Server | Backed by |
|---|---|---|
| `customer://{customer_id}/profile` | Concierge | `CustomerRepository` |
| `account://{account_id}/summary` | Banking | `AccountRepository` |
| `policy://{policy_id}/summary` | Insurance | `PolicyRepository` |
| `knowledgebase://{document_id}/excerpt` | Concierge | `common/knowledge_base.py` over `data/docs/*` |

Every Resource masks business IDs, returns one record/excerpt (never bulk
data), and is traced the same way Tools are. The knowledge-base Resource
reuses the existing `data/docs/` Markdown files as-is — no new database
table was introduced for it (`common/knowledge_base.py` parses the YAML
front matter with a small dependency-free parser and returns only the
requested document's excerpt).

## 18. Prompt Inventory (2 total)

Both registered on `concierge_ops_server` as real `@mcp.prompt()` FastMCP
Prompts (not plain helper functions):

- **`request_classification_prompt`**(`customer_message`, `customer_tier`,
  `prior_interaction_summary`, `known_product_lines`)
- **`response_drafting_prompt`**(`classified_intent`,
  `retrieved_context_summary`, `customer_name`, `escalation_flag`)

Both sanitize every free-text argument (`common.guardrails.sanitize_free_text(...,
raise_on_injection=False)`, neutralizing rather than rejecting, since a
prompt must still render) before embedding it, and explicitly instruct
the model to treat the embedded customer/context text as data, never as
new instructions.

## 19. Guardrails (`common/guardrails.py`)

| Function | Purpose |
|---|---|
| `enforce_domain_scope` | rejects a caller_scope not permitted to reach this server's domain at all |
| `enforce_caller_scope_ownership` | for `user` scope only: rejects access to another customer's record |
| `mask_business_id` / `mask_fields_in_dict` | last-four-character masking, outbound-response-only |
| `minimize_account_fields` / `minimize_portfolio_fields` | scope-based field subsetting |
| `sanitize_free_text` | HTML stripping, length limiting, regex-based prompt-injection signature detection |
| `redact_for_logging` | recursive PII-shaped-key redaction for structured logs |
| `check_output_grounding` / `find_unmasked_business_ids` / `find_unsupported_numeric_claims` | deterministic grounded-output checking for the future Drafting Agent |

Deliberately **not** in this file: `run_escalation_check`,
`write_audit_log`, `send_customer_notification` — those are Concierge
MCP business operations (they decide things and write data), not reusable
guardrail utilities.

Optional, defense-in-depth integration with `guardrails-ai` (see
`requirements.txt` for the exact Hub validators and install commands) is
wired in behind `common.guardrails.GUARDRAILS_AI_AVAILABLE` — every check
in this module is also implemented deterministically in pure Python, so
the guardrail layer is fully correct and fully testable with or without
guardrails-ai/the Guardrails Hub installed.

## 20. Logging (`common/logging_config.py`)

`@trace(logger)` / `@trace(logger, redact=redact_for_logging)` wraps every
Tool, Resource, and Prompt (innermost decorator, so FastMCP registers the
traced function). Produces one JSON object per line:

- `ENTER` (DEBUG): fully-qualified function name, `call_id`, bound arguments
- `EXIT` (DEBUG): same `call_id`, `duration_ms`, truncated return preview
- `FAILED` (ERROR): same `call_id`, `duration_ms`, exception type, full
  traceback — then the original exception is re-raised

`LOG_LEVEL` env var, default `DEBUG`. See `tests/test_logging.py`.

## 21. Error Handling (`common/errors.py`)

Repository errors (`RecordNotFoundError`, `DatabaseOperationError`, ...)
are translated at the server boundary into client-safe types —
`ResourceNotFoundError`, `PermissionDeniedError` (and its
`CallerScopeViolationError` / `PromptInjectionDetectedError` subclasses in
`common/guardrails.py`), `InternalServiceError` — always via
`raise CleanError(...) from original_exc`, so the full original traceback
still reaches the structured `FAILED` trace log server-side without ever
being returned to an MCP client.

## 22. How to Run Everything

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# optional, defense-in-depth only:
guardrails hub install hub://guardrails/regex_match
guardrails hub install hub://guardrails/detect_pii

python database.py --seed

# in four separate terminals:
python -m servers.banking_server
python -m servers.insurance_server
python -m servers.wealth_server
python -m servers.concierge_ops_server

# test suite (does not require the servers to be running separately --
# tests call the decorated tool/resource/prompt functions directly, and
# test_fastmcp_registration.py uses fastmcp's in-memory Client):
pytest tests/ -v
```

## 23. Test Inventory

| File | Covers |
|---|---|
| `test_models.py` / `test_repositories.py` / `test_seed.py` | Data module (unchanged from before the MCP layer) |
| `test_server_data_isolation.py` | table isolation at the repository/session layer, **and** against the real running server modules' own sessions |
| `test_caller_scope.py` | all five roles, both allowed and rejected access, across all four servers; field minimization |
| `test_mcp_tools.py` | business logic of all 13 tools, including the escalation decision matrix (§24) and masking |
| `test_mcp_resources.py` | all 4 resources: masking, no-bulk-data, not-found handling, structured tracing |
| `test_mcp_prompts.py` | both prompts: dynamic arguments present, prompt-injection neutralization |
| `test_guardrails.py` | every function in `common/guardrails.py` in isolation |
| `test_logging.py` | `@trace` ENTER/EXIT/FAILED shape, PII redaction, JSON-lines format |
| `test_fastmcp_registration.py` | the **real** `fastmcp.FastMCP` registrations (tools/resources/prompts), via `fastmcp.Client` — not a mocked server |

## 24. Escalation Decision Matrix

| request_category | draft_confidence | escalated |
|---|---|---|
| `financial_hardship` | 0.95 | **True** (hard category) |
| `safeguarding_concern` | 0.99 | **True** (hard category) |
| `compliance_override_request` | 0.99 | **True** (hard category) |
| `normal_request` | 0.74 | **True** (below 0.75 threshold) |
| `normal_request` | 0.75 | **False** |
| `normal_request` | 0.95 | **False** |

Hard categories are checked **first**, unconditionally — rephrasing a
hard-category request as a differently-worded "normal" request does not
bypass this, because the hard-category check is driven by the
`request_category` field itself (set at intake time by the future
structured-intake module), not by a model's read of the free text.
