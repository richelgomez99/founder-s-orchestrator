# Implementation Plan: Founder Orchestrator Governance Gate

**Branch**: `001-founder-governance-gate` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-founder-governance-gate/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

A deterministic governance gate sits in front of nine scripted sub-agents and decides allow, deny, or hold on every irreversible action. Code decides. The gate is a pure function: `evaluate(request) -> response` over six rules, five hard rules under fixed precedence (BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH) plus a deterministic anomaly layer (PATTERN) that can only escalate an allow to a hold. On top of the deterministic structural check sits a real learned second plane: an out-of-distribution score from the fine-tuned founder model's token-likelihood (perplexity), env-gated, that can also only escalate an allow to a hold and degrades to absent when its endpoint is unset. A fine-tuned founder-voice model phrases the verdict and can only add caution, never remove it. When an endpoint is unset or unreachable, the response falls back to the reason text and the decision is unchanged.

Technical approach is pinned, not re-derived. The gate, config, voice client, and the learned-detector client are pure Python standard library so the critical path never blocks on installs. A FastAPI server exposes `POST /evaluate` and serves a single self-contained static console. The founder voice and the learned out-of-distribution detector share one LoRA on an OpenAI-compatible endpoint on a parallel track that is never on the gate critical path.

### Build order (sacred)

1. Gate plus tests (the wall). `gate.py`, the deterministic anomaly layer, `fleet_config.py` parity test, and the required gate cases. Must pass with the voice endpoint not running.
2. Voice client and server. `voice.py` with hard fallback, `server.py` `POST /evaluate`, and the static console.
3. The real learned second plane. `anomaly.py`, a token-likelihood out-of-distribution scorer consumed by the gate after the hard rules pass, tighten-only, with graceful fallback. Precondition: the two headline gate tests are green. This is the technical-ingenuity layer, distinct from voice.
4. Presenter-driven red-team input box in the console.
5. Real LitServe LoRA endpoint backing both voice and the learned detector. Stretch only, taken only if step 4 is solid and the LoRA trained well.

## Technical Context

**Language/Version**: Python 3.11+ (local dev on 3.12 is fine).

**Primary Dependencies**: Critical path uses the Python standard library only. The gate and config are pure data plus small pure helpers. The voice client and the learned-detector client both use `urllib`. The web server uses FastAPI and uvicorn. Tests use pytest. Parallel LoRA track (not on the critical path): LitGPT `finetune_lora`, LitServe `OpenAISpec`, `bitsandbytes==0.42.0`, base `microsoft/phi-2`. The same served LoRA backs both the founder voice and the learned out-of-distribution detector.

**Storage**: N/A. The audit log is an in-process append-only list for the demo. No database, no migrations.

**Testing**: pytest. The required cases MUST pass with the voice endpoint not running (`VOICE_BASE_URL` and `VOICE_TOKEN` unset).

**Target Platform**: Local loopback dev on macOS or Linux. Optional co-located host is the verified Lightning x OpenClaw Studio template, orchestrator plus LitServe on loopback, gateway the only exposed surface.

**Project Type**: Single project. A web service (FastAPI) plus a self-contained static console served from `/`.

**Performance Goals**: The gate decision is a pure function and returns in well under a millisecond. The voice client uses a short timeout and a hard fallback so the critical path never blocks. No install step on the demo path.

**Constraints**: Determinism is a success criterion: identical input yields byte-for-byte identical `decision` and `reason`. No heavy dependencies on the gate critical path. No frontend build step. `voiced_response` contains zero em dashes and zero exclamation marks.

**Scale/Scope**: 9 lanes, 6 rules (5 hard plus 1 deterministic anomaly), 1 learned out-of-distribution second plane, 1 `POST /evaluate` endpoint, 1 static console, 7 demo verdicts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution file is still a blank template. Per the feature brief, the plan is governed by these five non-negotiables. Each is mapped to the design below.

1. **Security is deterministic code.** The gate computes `decision` and `reason` in code before any model call. The model never decides and can only add caution. PASS: `gate.py` is a pure function with no model dependency; the two allow-to-hold escalation paths are both code-side, the deterministic PATTERN layer and the learned out-of-distribution detector, and neither can produce a deny or loosen one (FR-003, FR-062, FR-065, FR-068, FR-072).
2. **Founder voice on every output.** `voiced_response` is dry, terse, first person, with no em dashes and no exclamation marks. PASS: `voice.py` enforces the style and the fallback reason text is written to the same rule (FR-073, SC-005).
3. **Only the orchestrator is real.** The nine sub-agents are thin scripted clients. PASS: `sub_agent.py` is a copyable client template; no real workforce is built (FR-081).
4. **fleet_config is the single source of truth and mirrors `Seed/generate_dataset.py`.** PASS: `orchestrator/fleet_config.py` holds all norms and `tests/test_config_parity.py` asserts the match (FR-080, SC-004).
5. **Build order is sacred.** Gate plus passing tests before anything else. PASS: the build order above puts `gate.py` and its tests first; the server, console, and LoRA come after.

**Initial gate result: PASS.** No violations. Re-checked after Phase 1 design: still PASS, the data model and the single `POST /evaluate` contract introduce no new dependencies or patterns.

## Project Structure

### Documentation (this feature)

```text
specs/001-founder-governance-gate/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
orchestrator/
├── fleet_config.py        # single source of truth (exists); mirrors Seed/generate_dataset.py
├── gate.py                # evaluate(request) -> response; six rules + deterministic anomaly
├── anomaly.py             # learned OOD scorer (token-likelihood) consumed by the gate; env-gated, graceful fallback
├── voice.py               # OpenAI-compatible client (urllib) + hard fallback to reason text
├── server.py              # FastAPI POST /evaluate; serves the console at /
├── sub_agent.py           # thin reusable client template (copied per agent)
└── static/
    └── index.html         # Orchestrator Console: fleet rail, decision theater, audit log,
                           #   beat buttons, presenter red-team input, voice online/offline toggle

tests/
├── test_gate.py           # the required pytest cases plus per-rule tests
├── test_anomaly.py        # learned second plane: stub high/low/absent, tighten-only
└── test_config_parity.py  # asserts gate config matches Seed/generate_dataset.py norms

README.md                  # run and demo guide
HARDENING.md               # OpenClaw deployment posture (documentation only)
SUBAGENTS.md               # parameter table for the nine-lane fan-out
```

**Structure Decision**: Single project, flat `orchestrator` package. `fleet_config.py` already exists and is the single source of truth. `gate.py` imports only `fleet_config.py` and the standard library, so the tests run without FastAPI and without the voice endpoint. `server.py` and `static/index.html` are thin layers over the gate. `sub_agent.py` is a template the human copies per lane; no real nine-agent workforce is built.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. The design uses one project, the standard library on the critical path, and no added patterns. This section is intentionally empty.
