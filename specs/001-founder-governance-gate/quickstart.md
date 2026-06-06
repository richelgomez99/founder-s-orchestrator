# Quickstart: Founder Orchestrator Governance Gate

**Branch**: `001-founder-governance-gate` | **Date**: 2026-06-06

This is the validation guide. It proves the feature works end to end. Implementation detail lives in [plan.md](plan.md), [data-model.md](data-model.md), and the contract at [contracts/post-evaluate.yaml](contracts/post-evaluate.yaml).

## Prerequisites

- Python 3.11+ (local dev on 3.12 is fine). The project `.venv` already has pytest.
- The gate and its tests need no third-party packages.
- The server step needs FastAPI and uvicorn: `pip install fastapi uvicorn`.
- The voice endpoint is optional. The required tests run with it off.

## 1. The wall: gate plus tests, voice endpoint off

The first success criterion is that the gate decides correctly with no model running.

```bash
# from the repo root, with VOICE_BASE_URL and VOICE_TOKEN unset
unset VOICE_BASE_URL VOICE_TOKEN
pytest -q
```

Expected:

- `tests/test_gate.py` passes. Every required case returns a decision, a reason that names the rule, `anomaly` as a boolean, and `logged` true.
- `tests/test_config_parity.py` passes. Gate norms match `Seed/generate_dataset.py` exactly.
- Determinism check passes. The same request evaluated twice returns byte-for-byte identical `decision` and `reason`.
- `voiced_response` equals `reason` for every case, with zero em dashes and zero exclamation marks.

## 2. Run the console

```bash
uvicorn orchestrator.server:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/`. The Orchestrator Console loads: the fleet rail with nine tiles, the decision theater, and the audit log. No build step runs.

## 3. The seven demo verdicts

Fire each from a beat button or the presenter red-team input box. Each verdict is deterministic. See [contracts/post-evaluate.yaml](contracts/post-evaluate.yaml) for request shapes.

| # | Scenario | Channel | Expected decision | Rule named |
|---|----------|---------|-------------------|------------|
| 1a | Finance settles AWS 4200 USD invoice | founder-authenticated | allow | BUDGET |
| 1b | Hijacked 47000 USD wire to a non-approved payee | inbox | deny | BUDGET |
| 2a | Engineering staging token by vault reference with expiry | founder-authenticated | allow | SECRET |
| 2b | Production DB string inside an ingested vendor ticket | inbox | deny | PROVENANCE then SECRET |
| 3 | Approved vendor, in-cap, right channel, novel payee above routine band | founder-authenticated | hold | PATTERN |
| 4 | "From the founder" wire demand with off-voice tells | inbox | deny | AUTH |
| 5 | Re-fire scenario 1b | inbox | deny | BUDGET |

Scenario 3 is the centerpiece: five green hard-rule checks and one amber PATTERN flag in the rule rail. It proves two layers and that the learned layer only adds caution.

## 4. The model never decides

With the server running, toggle voice ONLINE then OFFLINE in the console and re-fire scenario 1b.

- ONLINE: `decision` is deny, `voiced_response` is the founder-voice phrasing.
- OFFLINE (or `VOICE_BASE_URL` unset): `decision` is still deny, `voiced_response` falls back to the `reason` text.

The decision is identical in both states. This is the security claim made visible.

## 5. Optional: real LoRA voice path

Stretch only. Train and serve the founder-voice LoRA, then point the voice client at it.

```bash
# served via LitServe OpenAISpec on loopback port 8000
export VOICE_BASE_URL="http://127.0.0.1:8000/v1"
export VOICE_TOKEN="local"
```

Re-run the console. Decisions are unchanged; only `voiced_response` phrasing changes. If the endpoint is slow, malformed, or down, the gate falls back to the reason text and the decision holds.

## Success criteria mapped

- SC-001: step 1 suite passes with the voice endpoint off.
- SC-002: step 1 determinism check passes.
- SC-003: every reason in steps 1 and 3 names the rule.
- SC-004: `test_config_parity.py` passes in step 1.
- SC-005: zero em dashes and zero exclamation marks in `voiced_response` across step 1.
- SC-006: step 4 shows the final decision equals the code decision in both voice states.
- SC-007: the seven verdicts in step 3 each match the expected decision.
