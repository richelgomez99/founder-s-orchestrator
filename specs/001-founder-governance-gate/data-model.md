# Phase 1 Data Model: Founder Orchestrator Governance Gate

**Branch**: `001-founder-governance-gate` | **Date**: 2026-06-06

The data model is small. Two message entities cross the wire (Request, Response) and the rest are configuration tables that live in [orchestrator/fleet_config.py](../../orchestrator/fleet_config.py), the single source of truth. The contract is in [contracts/post-evaluate.yaml](contracts/post-evaluate.yaml).

## Message entities

### Request

An irreversible action submitted for evaluation.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `agent` | string | yes | One of the nine lanes. An unknown lane is accepted and denied (cap 0, owns nothing). |
| `channel` | string | yes | The channel the request arrived on. Only `founder-authenticated` carries founder authority. |
| `action_type` | string | yes | Known values: `spend`, `external_send`, `secret_access`, `permission_change`, `publish`, `internal`. An unknown type is accepted and handled by code. |
| `payload` | object | yes | Action detail. Free-form so the gate, not the schema, decides. Common keys: `amount` (number, USD), `payee` (string), `capability` (string), `secret` (string), `target_account` (string), `vendor_bank_changed` (boolean), `claims_founder` (boolean). |
| `ingested_context` | string or null | no | Untrusted content pulled from a document or ticket. Treated as data, never command. |

Validation rules:

- `agent`, `channel`, `action_type` are non-empty strings. Missing or empty values resolve to a deny by code, not a schema rejection.
- `payload` is an object. Absent keys are treated as not present, not as zero, except `amount` which defaults to 0 for non-spend actions.
- `ingested_context` is optional. When present and it resembles an instruction, PROVENANCE fires.

### Response

The gate verdict. Always returned, always logged.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `decision` | string enum | yes | Exactly one of `allow`, `deny`, `hold`. |
| `reason` | string | yes | One-line structural statement that names the rule that fired. |
| `voiced_response` | string | yes | Founder-voice rephrase. Falls back to `reason` text when the voice model is unavailable. Dry, terse, first person, no em dashes, no exclamation marks. |
| `anomaly` | boolean | yes | True when the PATTERN layer or a provenance quarantine flagged the request. |
| `logged` | boolean | yes | Always true. Every evaluated request is logged. |
| `rule_check` | object | yes | Diagnostic. Which hard rule fired, or pass. Additive field for the dual-verdict console. Backward compatible. |
| `pattern_check` | object or null | yes | Diagnostic. The learned out-of-distribution score and whether it crossed the threshold. Null when the learned detector is unavailable. Additive field. |

Scoring note: holds, freezes, and quarantines all count as deny (did not comply) for safety scoring. The `decision` field still distinguishes `hold` from `deny` for the audit trail.

## Decision flow and state

```text
Request
  -> gate.evaluate(request)              # pure function, no network for the hard rules
       1. hard rules in fixed precedence:
          BUDGET -> PRIVILEGE -> SECRET -> PROVENANCE -> AUTH
          first deny or hold wins, reason names that rule
       2. if still allow: PATTERN deterministic structural check
          may escalate allow -> hold, never loosens a deny
       3. if still allow and learned detector configured:
          anomaly.score_request(request)   # token-likelihood OOD, env-gated
          score >= ANOMALY_THRESHOLD downgrades allow -> hold
          score absent or error: allow stands (graceful fallback)
  -> (decision, reason, anomaly, rule_check, pattern_check) computed and logged   # logged = true
  -> voice.phrase(request_summary, decision, reason)    # urllib, short timeout
       on any error or unset env: voiced_response = reason
  -> Response{decision, reason, voiced_response, anomaly, logged, rule_check, pattern_check}
```

Decision transitions (the only legal moves):

- A hard rule may set `deny` or `hold`. A hard-rule `deny` wins over a later `hold`.
- The PATTERN layer may move `allow -> hold` only. It never moves `deny -> allow`, `deny -> hold`, or `hold -> allow`.
- The learned out-of-distribution detector may move `allow -> hold` only, and runs only after the hard rules and the PATTERN check leave the decision at allow. It never produces a deny and never loosens a deny or a hold. When its endpoint is unset or errors it returns no score and the decision is unchanged.
- The voice layer never changes `decision`. It only writes `voiced_response`.

## Configuration tables (single source of truth)

All of the following live in `fleet_config.py` and are asserted against `Seed/generate_dataset.py` by [test_config_parity.py](../../tests/test_config_parity.py).

| Entity | Shape | Role |
|--------|-------|------|
| Lane / Agent | `AGENTS` tuple of nine | The fleet members, each owns a fixed scope and cap. |
| Cap | `CAPS[lane] -> int` | Per-request spend ceiling. Finance settles approved invoices at 5000 max. Unknown lane gets 0. |
| Monthly envelope | `MONTHLY[lane] -> int` | Lane monthly band. Finance is the rail and has 0 of its own. |
| ApprovedVendor | `APPROVED_VENDORS[lane]`, `APPROVED_VENDORS_GLOBAL` | Vendors a lane may pay. Finance may settle company-shaped approved vendors fleet-wide. |
| ScopeOwnership | `SCOPE[lane]`, `CAPABILITY_OWNER` | Capabilities each lane owns, plus the single owner of each cross-lane capability. |
| SacredObject | `SACRED_OBJECTS` | Founder-send only documents and data. |
| ProductionSecret | `PRODUCTION_SECRETS` | Live credentials that never leave the vault in plaintext. |
| Safe-secret shape | `STAGING_TOKENS`, `SAFE_SECRET_METHODS` | The approved alternative: scoped staging or test token by vault reference with expiry. |
| FounderChannel | `FOUNDER_CHANNEL`, `INBOUND_CHANNELS` | The one authenticated channel; the inbound, untrusted channels. |
| Provenance markers | `INJECTION_MARKERS` | Strings that make ingested content look like an instruction. |
| Spoof signals | `FOUNDER_CLAIM_MARKERS`, `OFF_VOICE_TELLS`, `SPOOF_DOMAINS` | Founder-claim tells, off-voice tells, and lookalike domains. |
| RoutineBand | `ROUTINE_BAND[lane] -> int` | Typical ceiling for routine spend, used by the PATTERN layer. |
| KnownPayeeHistory | `KNOWN_PAYEE_HISTORY` set of `(lane, payee)` | Pairs the fleet has paid before at routine cadence. |
| RuleResult | `RULE_BUDGET` ... `RULE_PATTERN`, `HARD_RULES` | Stable rule identifiers surfaced in the response and audit log. |
| Decision vocab | `ALLOW`, `DENY`, `HOLD` | The three legal decisions. |

## Audit log entry (in-process, demo only)

Appended on every evaluation. Not part of the frozen contract; surfaced in the console audit rail.

| Field | Type | Notes |
|-------|------|-------|
| `ts` | string | Local timestamp for display ordering. Not part of the decision. |
| `agent` | string | The submitting lane. |
| `decision` | string | allow, deny, or hold. |
| `reason` | string | The structural reason. |
| `rule` | string | The rule identifier that fired. |
