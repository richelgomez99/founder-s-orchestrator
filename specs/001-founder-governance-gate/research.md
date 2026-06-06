# Phase 0 Research: Founder Orchestrator Governance Gate

**Branch**: `001-founder-governance-gate` | **Date**: 2026-06-06

The stack and structure are pinned, verified live on 2026-06-06. This file records the decisions, not a re-derivation. There are no open NEEDS CLARIFICATION items: the spec was transcribed from a finished brief and the requirements checklist passed with zero markers.

## D1. Gate and config: pure standard library

- **Decision**: `gate.py` and `fleet_config.py` use the Python standard library only. Plain data plus small pure helpers, no third-party imports.
- **Rationale**: The gate is the critical path and a success criterion is determinism. Zero heavy dependencies means the critical path never blocks on installs and the required tests run anywhere Python runs. `fleet_config.py` already exists in this shape.
- **Alternatives considered**: A rules engine or schema-validation library. Rejected: added dependency and indirection for six rules that are clearer as direct code, and it would put a package install on the demo path.

## D2. Web server: FastAPI and uvicorn, single static console

- **Decision**: FastAPI plus uvicorn expose `POST /evaluate` and serve one self-contained `static/index.html` at `/`. No frontend build step. Vanilla JS posts to `/evaluate`.
- **Rationale**: The demo is 50% of the score and must not break live. A single static file served by the same process has no build, no bundler, and nothing to surprise on stage. FastAPI gives a typed endpoint and an automatic OpenAPI document that matches the frozen contract.
- **Alternatives considered**: React or Vite. Rejected: a build step is live-demo fragility for no benefit here. A second static file server. Rejected: one process is simpler to run and rehearse.

## D3. Voice client: standard-library urllib, OpenAI-compatible, hard fallback

- **Decision**: `voice.py` uses `urllib` to POST to an OpenAI-compatible `/v1/chat/completions` endpoint configured by `VOICE_BASE_URL` and `VOICE_TOKEN`, with a short timeout. On any error, timeout, or unset env, it returns the gate `reason` text unchanged.
- **Rationale**: No SDK means no dependency on the critical path and no version drift. The hard fallback makes "the model never decides" testable: with the endpoint off, the decision and reason are identical and `voiced_response` equals `reason`.
- **Alternatives considered**: The official OpenAI SDK. Rejected: a dependency and an init cost for one POST. A streaming client. Rejected: the console needs one phrasing string, not a stream.

## D4. Tests: pytest, required cases pass with the voice endpoint off

- **Decision**: pytest. `tests/test_gate.py` holds the required cases and per-rule tests. `tests/test_config_parity.py` asserts the gate norms match `Seed/generate_dataset.py`. The required suite passes with `VOICE_BASE_URL` and `VOICE_TOKEN` unset.
- **Rationale**: The security claim rests on code deciding. Running the suite with the voice endpoint off proves refusals fire without the model and proves determinism by repeating identical inputs.
- **Alternatives considered**: unittest. Rejected: pytest is already in the project `.venv` and gives terser assertions.

## D5. Two-layer architecture: deterministic gate plus deterministic anomaly

- **Decision**: Layer one is five hard rules (BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH) under fixed precedence. Layer two is a deterministic anomaly scorer (PATTERN) computed in code from structural signals. The PATTERN layer can only escalate an allow to a hold and never loosens a deny. The LoRA is voice and optional narration, never the decider.
- **Rationale**: Code gives guaranteed enforcement on known threats with full auditability. The deterministic anomaly layer adds caution on off-pattern requests without surrendering determinism. Keeping the escalation path in code, not the model, is what makes the asymmetry testable.
- **Alternatives considered**: Letting the model raise holds. Rejected: it would make the decision non-deterministic and break the core claim. A learned anomaly score at decision time. Rejected: the model is the voice and the offline baseline, not a live gate input.

## D6. Determinism strategy

- **Decision**: `evaluate(request)` is a pure function over the request and `fleet_config.py`. No clocks, no randomness, no network in the decision path. The reason names the first rule that fired under fixed precedence (BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH, then PATTERN).
- **Rationale**: Identical inputs must yield byte-for-byte identical `decision` and `reason` (SC-002). Fixed precedence makes multi-rule requests resolve to one stable reason.
- **Alternatives considered**: Timestamped reasons or random tie-breaks. Rejected: both break byte-for-byte determinism. Timestamps belong in the audit log entry, not the decision.

## D7. LoRA voice model (parallel track, not on the critical path)

- **Decision**: Lightning AI Studio, base `microsoft/phi-2`, LitGPT `finetune_lora` with `--precision bf16-true --quantize bnb.nf4`, `bitsandbytes==0.42.0`, `lora_r 8`, `lora_alpha 16`, about 400 steps. Served via LitServe `OpenAISpec` on port 8000 as the OpenAI-compatible endpoint the voice client targets. Dataset exists: `Seed/founder_orchestrator_lora.json` (520 rows, Alpaca format).
- **Rationale**: The LoRA serves the VOICE role only. It is trained on the same norms `fleet_config.py` enforces, which is the "personalization is the security" baseline. Because the voice client falls back hard, the gate ships and demos whether or not the LoRA is up.
- **Alternatives considered**: GraphN `model.graphn.ai/v1` or Lightning model APIs as the host. Held as drop-in alternates: all three are OpenAI-compatible, so `VOICE_BASE_URL` swaps with no code change. LitServe is primary for the co-located loopback story.

## D8. Deployment posture: OpenClaw hardening (documentation only)

- **Decision**: `HARDENING.md` documents the posture: OpenClaw `>= 2026.4.22`, sandbox mode non-main, `workspaceAccess ro`, `skills []`, gateway auth token, channel `dmPolicy pairing`. The verified Lightning x OpenClaw Studio template can host the orchestrator and LitServe co-located on loopback with only the gateway exposed.
- **Rationale**: The tiebreaker is hardest to break. Documenting a locked-down posture on a deliberately CVE-heavy framework is the security narrative. It is documentation, not a runtime dependency, so it cannot break the demo.
- **Alternatives considered**: Wiring OpenClaw into the critical path. Rejected: out of scope and live-integration risk. The gate stands alone and the OpenClaw posture is the deployment story around it.

## D9. Configuration parity

- **Decision**: `orchestrator/fleet_config.py` is the single source of truth. `tests/test_config_parity.py` asserts caps, vendors, scope, sacred objects, production secrets, routine bands, known payees, and the founder channel match `Seed/generate_dataset.py` exactly.
- **Rationale**: If the gate config drifts from the training norms, the LoRA's learned baseline no longer matches what code enforces and the personalization claim breaks. An automated parity test makes the match a tested invariant (SC-004).
- **Alternatives considered**: Importing the generator's `AGENTS` table directly into the gate. Rejected: the generator lives under a folder named `Seed ` (trailing space) and carries dataset-only logic. Mirroring the norms and testing parity keeps the gate clean and the coupling explicit.
