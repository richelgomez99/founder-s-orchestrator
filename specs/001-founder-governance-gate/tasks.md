# Tasks: Founder Orchestrator Governance Gate

**Branch**: `001-founder-governance-gate`
**Input**: Design documents in `specs/001-founder-governance-gate/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/post-evaluate.yaml

**Tests**: Test tasks are included. The spec requires an automated gate suite that passes with the voice endpoint not running.

## Build order is sacred

The phases below are the build order, not a suggestion. A later phase does not start until the phase before it meets its checkpoint. The hard gate and its tests come first. The learned plane comes second and is gated on the gate tests being green. The demo is third. The fleet and docs come last and are cuttable under time pressure.

```text
PHASE 0  Foundation        fleet_config.py (done)
PHASE 1  The Wall          deterministic gate + voice + server + tests   <- MVP, blocks all
   |     CHECKPOINT        two headline tests green (precondition for PHASE 2)
PHASE 2  The Second Plane  learned OOD anomaly detector (ingenuity layer)
PHASE 3  The Demo          Orchestrator Console (approach A then C)
PHASE 4  The Fleet         sub_agent template + SUBAGENTS table (cuttable)
PHASE 5  Docs              README + HARDENING
```

## Format

`- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: can run in parallel (different file, no dependency on an incomplete task).
- **[Story]**: the spec user story the task serves (US1 deterministic verdict, US2 budget, US3 secret, US4 anomaly, US5 model-never-decides, US6 founder-channel auth).
- No story label on pure setup, infrastructure, docs, or milestone tasks.

---

## Phase 0: Foundation (COMPLETE)

**Goal**: Single source of truth for all fleet norms, mirrored from the dataset generator.

- [x] T001 `orchestrator/fleet_config.py` exists and mirrors `Seed/generate_dataset.py` norms (CAPS, MONTHLY, APPROVED_VENDORS, APPROVED_VENDORS_GLOBAL, SCOPE, CAPABILITY_OWNER, PRODUCTION_SECRETS, SACRED_OBJECTS, FOUNDER_CHANNEL, INBOUND_CHANNELS, ROUTINE_BAND, KNOWN_PAYEE_HISTORY, INJECTION_MARKERS, spoof markers, rule identifiers). No further work; this is the source of truth for every later phase.

---

## Phase 1: The Wall (deterministic gate)

**Priority**: P1. This is the MVP and it blocks every later phase. The gate decides in code. The model never decides.

**Goal**: A pure function `evaluate(request) -> response` over six rules under fixed precedence (BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH, then PATTERN), plus the voice client, the server, and the required tests.

**Independent test**: With `VOICE_BASE_URL` and `VOICE_TOKEN` unset, `pytest -q` passes. Identical input yields byte-for-byte identical `decision` and `reason`. `voiced_response` equals `reason` with zero em dashes and zero exclamation marks.

### Setup

- [x] T002 Make the package importable and add the test root: confirm `orchestrator/__init__.py` exists (add it if missing), create `tests/` with `tests/__init__.py`, and verify `pytest -q` runs from the repo root with no third-party package on the gate path. Files: `orchestrator/__init__.py`, `tests/__init__.py`.

### Gate core (single file `orchestrator/gate.py`, edited in sequence)

- [x] T003 [US1] Create `orchestrator/gate.py` skeleton in `orchestrator/gate.py`: pure `evaluate(request) -> response`, fixed precedence loop BUDGET then PRIVILEGE then SECRET then PROVENANCE then AUTH then PATTERN, first deny or hold wins and the reason names that rule, assemble the frozen Response `{decision, reason, voiced_response=reason, anomaly, logged=True}`, append an in-process audit entry on every call. No clock, no randomness, no network in the decision path (FR-001 to FR-007).
- [x] T004 [US2] Implement the BUDGET rule in `orchestrator/gate.py`: deny spend strictly over the lane cap and allow spend exactly at cap, deny when the payee is not on the lane list or the finance global approved set, hold when `vendor_bank_changed` is true and unverified out of band, deny same-payee structuring just under cap, deny transfers to unregistered `target_account`, deny finance raising its own cap, allow in-band approved-vendor spend within cap (FR-010 to FR-016).
- [x] T005 [US1] Implement the PRIVILEGE rule in `orchestrator/gate.py`: deny any capability the lane does not own and name the owning lane from `CAPABILITY_OWNER` (ask for the output, not the access), deny self permission-manifest edits, self-approval, self-replication, disabling audit logging, credential or session sharing, and blanket vault reads, allow scoped time-boxed read-only cross-lane output requests (FR-020 to FR-027).
- [x] T006 [US3] Implement the SECRET rule in `orchestrator/gate.py`: when `action_type` is `secret_access` or an `external_send` carries a `PRODUCTION_SECRETS` or `SACRED_OBJECTS` item, deny unless the channel is `FOUNDER_CHANNEL`, state that a production secret never leaves in a ticket, email, gist, or file, name the safe alternative (a scoped staging or test token by vault reference with expiry), allow staging or test access by vault reference with expiry (FR-030 to FR-033).
- [x] T007 [US3] Implement the PROVENANCE rule in `orchestrator/gate.py`: treat `ingested_context` as data and never command, key on source not keyword detection, when the content resembles an instruction (`INJECTION_MARKERS`) deny, set `anomaly` true, quarantine the source, and continue the underlying task without the injected instruction (FR-040 to FR-041).
- [x] T008 [US6] Implement the AUTH rule in `orchestrator/gate.py`: only `FOUNDER_CHANNEL` carries founder authority, a founder-claimed message on any inbound channel is denied as a possible spoof, off-voice tells (urgency, secrecy, do-not-verify, exclamation marks, a new or lookalike domain) reinforce the spoof verdict, a text prefix is not authentication (FR-050 to FR-051).
- [x] T009 [US4] Implement the deterministic PATTERN layer in `orchestrator/gate.py`: after the five hard rules leave a provisional allow, compute a deterministic anomaly from `ROUTINE_BAND` and `KNOWN_PAYEE_HISTORY` (for example a novel payee above the lane routine band), escalate allow to hold with `anomaly` true and the reason naming PATTERN, never loosen a deny and never touch an existing hold (FR-060 to FR-062). This is the in-code anomaly layer, not the model.

### Voice, server, tests

- [x] T010 [P] [US5] Create `orchestrator/voice.py`: standard-library `urllib` client that posts the request summary and the gate decision to an OpenAI-compatible endpoint (`VOICE_BASE_URL`, `VOICE_TOKEN`) with a short timeout, returns founder-voice phrasing, and falls back hard to the `reason` text on any error, timeout, or unset env. The model never changes the decision. Enforce dry, terse, first-person output with zero em dashes and zero exclamation marks (FR-070 to FR-073). DONE plus two honesty guards: contradiction guard (discard phrasing that implies the opposite verdict) and numeric guard (discard invented dollar figures).
- [x] T011 [P] [US1] Create `tests/test_gate.py`: the five required cases run with the voice endpoint not running. DONE, 20 gate tests pass.
- [x] T012 [P] [US1] Create `tests/test_config_parity.py`: assert the gate config norms match `Seed/generate_dataset.py` exactly (FR-080, SC-004). DONE.
- [x] T013 [US1] Create `orchestrator/server.py`: FastAPI `POST /evaluate` that returns the frozen contract Response and serves the static console at `/`. DONE, plus `/audit` and `/health`.

### Checkpoint (gating milestone, blocks Phase 2)

- [x] T014 CHECKPOINT: unset `VOICE_BASE_URL` and `VOICE_TOKEN`, run `pytest -q`, and confirm the two headline tests in `tests/test_gate.py` are green. DONE. Two headline tests green, 36 tests total pass.

---

## Phase 2: The Second Plane (learned OOD anomaly detector)

**Priority**: P2. The ingenuity layer. **PRECONDITION: T014 is green.** Plane two does not start before the gate tests pass.

**Goal**: A learned, out-of-distribution anomaly sense that adds caution the enumerated rules cannot, computed from the fine-tuned founder model and degrading gracefully to hard-rule-only behavior when absent.

**Independent test**: With the gate tests green and no live endpoint, `tests/test_anomaly.py` proves a hard-rule-passing request downgrades to hold on a high score, stays allow on a low score, and stays allow when the score is `None`.

- [x] T015 [US4] Create `orchestrator/anomaly.py`: `score_request(request) -> float` from token-likelihood (perplexity), env-gated, returns `None` on unset or error. DONE.
- [x] T016 [US4] Integrate the learned layer in `orchestrator/gate.py`: injected `anomaly_scorer`, runs only on a provisional allow, downgrades to hold at or above threshold, never loosens. DONE.
- [x] T017 [US4] Expose both plane verdicts in the Response: `rule_check` and `pattern_check`. DONE.
- [x] T018 [P] [US4] Create `tests/test_anomaly.py`: high downgrades to hold, low stays allow, `None` stays allow. DONE, plus deny-never-loosened and error-swallowed tests.

---

## Phase 3: The Demo (50% of the score, approach A then C)

**Priority**: P1 for the score. The console is the proof on stage.

**Goal**: A single self-contained console that shows the dual-verdict gate live, with scripted beats and a presenter-driven attack box. Vanilla JS, no build step. All copy in the founder voice.

**Independent test**: Open `http://127.0.0.1:8080/`, fire each beat, and watch the verdict stamp, the GATE line, the VOICE line, the rule rail, and the audit log update. Scenario 3 shows five green hard rules and one amber PATTERN flag.

- [x] T019 [US1] Create `orchestrator/static/index.html`: three-zone Orchestrator Console (fleet rail, decision theater with verdict stamp + GATE mono line + VOICE sans line + rule rail of five hard rules plus a PATTERN lane, append-only audit log showing `logged:true`). Vanilla JS, no build step. DONE (baseline; needs polish, see Phase 6).
- [x] T020 [US1] Add the scripted beat buttons and the voice toggle to `orchestrator/static/index.html`: four beats run legit then attack; voice ONLINE/OFFLINE toggle flips the voice path and auto-detects server voice on load. DONE.
- [x] T021 [US1] Add the approach C presenter red-team input box: founder types or pastes an attack and fires it live through the real gate. DONE (baseline parse; needs hardening, see Phase 6).
- [x] T022 [US4] Wire the Beat 3 frame: drive the rule rail from `pattern_check` and the hard-rule verdicts so an off-pattern request renders five green hard rules and one amber PATTERN flag. DONE.

---

## Phase 4: The Fleet (cuttable under time pressure)

**Priority**: P3. Cut from the bottom if time runs short. The gate and the demo stand without this.

**Goal**: One reusable thin sub-agent client and a parameter table for the nine lanes. Only the orchestrator is real.

**Independent test**: Run the finance and engineering agents and confirm a legit request allows and an attack request is refused, each printing `decision` and `voiced_response`.

- [x] T023 [US1] Create `orchestrator/sub_agent.py`: one reusable thin client template, posts to `/evaluate`, prints `decision` and `voiced_response`. DONE, verified live (finance + engineering beats).
- [x] T024 [P] [US1] Create `SUBAGENTS.md`: per-agent parameter table, tested agents plus seven cuttable backdrop agents. DONE.

---

## Phase 5: Docs

**Priority**: P3. Run and deployment narrative.

- [x] T025 [P] Create `README.md`: how to run the server and the tests, plus the two headline demo curl examples. DONE.
- [x] T026 [P] Create `HARDENING.md`: the OpenClaw deployment posture, pin `>= 2026.4.22`, sandbox non-main, workspaceAccess ro, skills [], gateway auth token, dmPolicy pairing. DONE.

---

## Polish and validation

- [ ] T027 Run the quickstart validation in `specs/001-founder-governance-gate/quickstart.md`: confirm the seven demo verdicts (SC-007), determinism (SC-002), config parity (SC-004), zero em dashes and zero exclamation marks in `voiced_response` (SC-005), and that the final decision equals the code decision in both voice states (SC-006). REMAINING (Claude Code): final pre-demo validation pass.

---

## Phase 6: PERSONALIZATION + AGENT (REMAINING, Claude Code handoff)

**Why this phase exists.** Honest critique from the founder: "everything looks
deterministic, where is the agent, how does this show a PERSONALIZED agent?"
That critique is correct about the DEMO, not the architecture. The
personalization is real but currently quiet and off-screen. This phase makes it
visible and gives the orchestrator agentic behavior. This is the highest-value
remaining work for the demo (50%) and creativity (10%) axes. Everything above is
built and tested (36 tests green, live LoRA voice working). Start here.

### The gap, stated plainly

What is built is a deterministic GOVERNANCE GATE. What the brief asks for is a
PERSONALIZED AUTONOMOUS AGENT. The gate is the security spine and it is correct
to be deterministic. But three things are missing for the demo to read as a
personalized agent rather than a firewall:

1. The personalization is invisible. The LoRA voice and the learned anomaly
   plane are the personalized parts, but on screen they look like one more line
   of text. A judge cannot see "this agent knows ME."
2. The orchestrator only JUDGES. It returns allow or deny or hold. An agent
   ACTS: it issues the staging token, it routes the request to the owning lane,
   it drafts the reply, it remembers. Right now it never takes the next step.
3. The "agent" (OpenClaw: memory, channels, autonomous turns) is named but not
   shown. The demo shows a request-response function, not an actor.

### What makes the personalization REAL (use this framing, it is true)

The personalization is not bolted on, it IS the security, and that is the whole
thesis. Make these visible:

- The LoRA is a weight update trained on how THIS founder works and talks
  (val ppl 9.56). It is a digital twin of the founder's judgment, not a prompt.
- The learned anomaly plane flags off-pattern requests because it learned the
  founder's normal distribution. "It holds this because it does not look like
  something I would do" is personalization expressed as security.
- Beat 3 (the off-pattern hold) is THE personalization beat: a request that
  breaks no hard rule and is still held purely because it is unlike the founder.
  Lead the demo narrative with this, not with the deterministic denials.

### Remaining tasks (priority order for Claude Code)

- [ ] T028 [PERSONALIZATION] Add a visible "founder profile" panel to the console
  (`orchestrator/static/index.html`): show the learned norms this agent carries
  (per-lane caps, approved vendors, sacred objects, voice samples from the LoRA).
  Caption it "what this agent learned about how I operate." This is the single
  fastest way to make personalization legible. Pull data from a new
  `GET /profile` route in `server.py` that returns the fleet_config norms plus a
  few sample LoRA voice lines.
- [ ] T029 [AGENT] Make the orchestrator ACT, not just judge. Add a `next_action`
  field to the response: on allow, state the action taken ("staging token issued,
  expires 24h"); on a cross-lane deny, state the routing ("forwarded to data for
  the dashboard output"); on a secret deny, state the safe alternative offered.
  Show `next_action` in the decision theater. This turns a verdict into an agent
  doing something. Keep it deterministic and code-driven.
- [ ] T030 [AGENT] Show the anomaly SCORE as a live dial or meter in the console,
  fed by `pattern_check.score`. When the learned plane is wired
  (`ANOMALY_BASE_URL`), a request animates the meter from low (typical) to high
  (off-pattern). This makes the learned layer a visible instrument, not a footnote.
- [ ] T031 [AGENT, stretch] Wire one real OpenClaw surface: the orchestrator
  receives a request through an OpenClaw channel (or a thin memory file it reads),
  consults the gate, and replies in the founder voice. Even one real channel turn
  makes "agent" concrete. See HARDENING.md for the OpenClaw config; the Studio
  template already runs OpenClaw.
- [ ] T032 [DEMO POLISH] Tighten the console visuals: animation timing on the
  stamp, a cleaner Beat 3 reveal (five green plus one amber should land as one
  image), the voice online-to-offline flip as a deliberate beat. The demo is 50
  percent; this is where the polish budget goes.
- [ ] T033 [PERSONALIZATION, stretch] Train a stronger anomaly signal: the current
  same-day Phi-2 OOD score is noisy. If credits allow later, a cleaner
  perplexity separation makes the live anomaly meter (T030) more convincing.
  Until then, Beat 3 stays pinned to a tested input.

### Demo narrative fix (no code, but say this)

Reorder the pitch so personalization leads:

1. "This agent is a fine-tuned model of how I work. Here is what it learned
   about me." (show the profile panel, T028)
2. "Watch it approve my normal AWS invoice in my voice." (Beat 1 legit, voice on)
3. "Now watch it refuse a request that breaks no rule, purely because it does
   not look like me." (Beat 3, the personalization beat, T030 meter)
4. "And here is the floor under all of it: the deterministic gate, which the
   model can never talk out of a refusal." (Beat 1 attack, then flip voice off)

That order answers "where is the agent" directly: the agent is the thing that
knows you, and the gate is the thing that cannot be fooled.

---


## Dependencies and execution order

### Phase order

- Phase 0 is done. Phase 1 blocks everything. Phase 2 is gated on the T014 checkpoint. Phase 3 needs the gate and server from Phase 1 and reads `pattern_check` from Phase 2. Phase 4 needs the server. Phase 5 is documentation and can be drafted any time after Phase 1.

### Hard preconditions

- T003 before T004 to T009 (all edit `orchestrator/gate.py`).
- T013 server depends on T003 to T010.
- **T014 checkpoint is the Phase 1 to Phase 2 gate. No Phase 2 task (T015 onward) starts until the two headline tests are green.**
- T016 depends on T009 and T015. T017 depends on T016. T018 depends on T015.
- T020, T021, T022 edit the same file as T019 and follow it in sequence. T022 also depends on T017.
- T024 documents the template from T023.

### Parallel opportunities

- T010, T011, T012 run in parallel once the gate core (T003 to T009) is done. They are different files with no shared edits.
- T018 runs in parallel with the rest of Phase 2 once T015 and T016 land.
- T025 and T026 run in parallel with each other and with Phase 4.
- Within T024, the seven backdrop agents are parallel and cuttable.

---

## Implementation strategy

- **MVP**: Phase 0 plus Phase 1 through the T014 checkpoint. A deterministic gate that allows the in-band invoice and denies the about-47000 USD wire, with the voice endpoint off, is a shippable, demoable control plane on its own.
- **Ingenuity increment**: Phase 2 adds the learned second plane on top of the green gate without changing any hard-rule decision.
- **Demo increment**: Phase 3 turns the gate into the on-stage proof. This is half the score, so it gets built as soon as the gate is green.
- **Cuttable tail**: Phase 4 and Phase 5 are dropped first if time runs short. The thesis survives without them.

---

## Story coverage

- **US1 deterministic verdict**: T003, T005, T011, T012, T013, T019, T020, T021, T023, T024.
- **US2 budget**: T004.
- **US3 secret and provenance**: T006, T007.
- **US4 anomaly (deterministic plus learned)**: T009, T015, T016, T017, T018, T022.
- **US5 model never decides**: T010.
- **US6 founder-channel auth**: T008.
