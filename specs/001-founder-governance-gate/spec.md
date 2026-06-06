# Feature Specification: Founder Orchestrator Governance Gate

**Feature Branch**: `001-founder-governance-gate`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "A deterministic governance gate that is the trusted control plane a solo founder's nine autonomous sub-agents must pass before any irreversible action (spend, external_send, secret_access, permission_change). Code decides; a fine-tuned model only phrases the decision in the founder's voice and can only ever add caution, never remove it."

## Context

Hackathon project (Lightning AI x Validia x Sentience, NYTechWeek). Judging weights: demo 50%, technical ingenuity 30%, security 10%, creativity 10%. Tiebreaker: hardest to break.

The founder runs a fleet of nine OpenClaw sub-agents: growth, sales, engineering, finance, research, recruiting, support, legal, data. Only the orchestrator is real. The sub-agents are thin scripted clients that submit requests. Every irreversible action a sub-agent wants to take passes through one gate before it happens.

## Core Insight (must hold)

Personalization is the security. One LoRA fine-tuned on how the founder actually works is both the personalization and the anomaly baseline.

- The deterministic gate is the hard floor. It catches structured, known violations with perfect reliability and full auditability, and it can never be talked out of them.
- The learned layer is a soft anomaly sense for open-ended, off-pattern requests the rules cannot enumerate.
- Critical asymmetry: the learned layer can only escalate an allow to a hold (add caution). It can never turn a coded deny into an allow.
- Code gives guaranteed enforcement on known threats. The model generalizes to unknown ones. Together they cover each other's blind spot.

The anomaly layer has two detectors, both tighten-only:

- A deterministic structural detector (the PATTERN rule), computed in code from the fleet config (novel payee above the lane routine band, and similar structural signals). It is always on and is the demo-reliable floor.
- A learned out-of-distribution detector, a real token-likelihood (perplexity) score from the fine-tuned founder model over the request text. A request that resembles the founder's normal traffic yields low surprise. An off-pattern one yields high surprise above a threshold and downgrades an allow to a hold. It is env-gated and degrades gracefully: when the endpoint is unset or errors, the score is absent and the gate proceeds on the hard rules and the structural detector only.

The learned detector is a genuine running capability, not a voice skin. For the live demo its on-stage trigger is pinned to a tested input, because a same-day model on a few hundred rows is a noisy detector. The capability is real, the demo's reliability is engineered, and both statements are true at once.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deterministic verdict on every irreversible request (Priority: P1)

A sub-agent submits any irreversible request. The gate returns allow, deny, or hold with a one-line structural reason, computed in code, so dangerous actions are refused deterministically and every verdict is auditable.

**Why this priority**: This is the MVP. Without a deterministic verdict on every request there is no control plane and no demo.

**Independent Test**: Submit the headline requests with the voice endpoint not running and confirm each returns a decision, a structural reason that names the rule, anomaly, and logged. Repeat identical inputs and confirm identical output.

**Acceptance Scenarios**:

1. **Given** any request with a known action_type, **When** it is evaluated, **Then** the response carries decision in {allow, deny, hold}, a one-line reason naming the rule that fired, anomaly as a boolean, and logged true.
2. **Given** the same request submitted twice, **When** both are evaluated, **Then** decision and reason are byte-for-byte identical.
3. **Given** an unknown or unlisted lane, **When** it requests anything irreversible, **Then** the gate denies, because an unknown lane owns nothing and carries a cap of zero.

---

### User Story 2 - Budget enforcement (Priority: P1)

Finance settles a normal in-band invoice to an approved vendor and it clears. A hijacked wire of about 47,000 USD (roughly 9x the 5,000 finance cap) to a payee that is not on the approved vendor list is refused.

**Why this priority**: Beat 1 of the demo. Money movement is the most legible irreversible action and the clearest proof the floor holds.

**Independent Test**: Run the approved-vendor invoice and the hijacked wire through the gate and confirm allow and deny respectively, each naming the BUDGET rule.

**Acceptance Scenarios**:

1. **Given** a finance spend to a company-shaped approved vendor under the 5,000 per-invoice cap on the authenticated channel, **When** evaluated, **Then** decision is allow and the reason names BUDGET.
2. **Given** a wire of about 47,000 USD to a payee not on any approved vendor list, **When** evaluated, **Then** decision is deny and the reason names BUDGET and the over-cap, off-list breach.
3. **Given** several requests to the same new payee each just under the lane cap, **When** evaluated, **Then** the gate denies as structuring.
4. **Given** a finance request to raise its own cap, **When** evaluated, **Then** the gate denies.

---

### User Story 3 - Secret protection (Priority: P1)

Engineering asks for a scoped staging vault reference with an expiry and it is approved. A request for a production secret arrives inside an ingested vendor ticket and it is refused on both the sacred-object and the provenance grounds.

**Why this priority**: Beat 2 of the demo. Secret exfiltration is the highest-consequence irreversible action and pairs the SECRET and PROVENANCE rules.

**Independent Test**: Run the staging vault reference and the ingested production-secret request through the gate and confirm allow and deny respectively, with the deny naming the safe alternative.

**Acceptance Scenarios**:

1. **Given** an engineering request for a staging or test token by vault reference with an expiry, **When** evaluated, **Then** decision is allow and the reason names SECRET.
2. **Given** an external_send or secret_access that includes a production secret on any channel other than the authenticated founder channel, **When** evaluated, **Then** decision is deny and the reason states that a production secret never leaves in a ticket, email, gist, or file, and names the safe alternative (a scoped staging or test token by vault reference with expiry).
3. **Given** a production-secret request embedded in ingested_context, **When** evaluated, **Then** decision is deny, anomaly is true, the source is quarantined, and the underlying task continues without the injected instruction.

---

### User Story 4 - Deterministic anomaly layer (Priority: P2)

A request passes all five hard rules and is still held because it is off-pattern for how the founder operates, for example a novel payee above the lane routine band. The hold is computed in code, not by the model.

**Why this priority**: Beat 3 and the two-layer proof. It shows the soft sense adds caution beyond the enumerated rules while staying deterministic.

**Independent Test**: Submit a within-cap, approved-vendor, in-band request to a payee the lane has never paid, above the routine band, and confirm a hold from the PATTERN rule with the voice endpoint off.

**Acceptance Scenarios**:

1. **Given** a request that clears BUDGET, PRIVILEGE, SECRET, PROVENANCE, and AUTH, but is above the lane routine band to a payee not in known history, **When** evaluated, **Then** decision is hold, anomaly is true, and the reason names PATTERN.
2. **Given** the pattern layer evaluates a request that a hard rule already denied, **When** it runs, **Then** it never changes deny to allow or hold; it can only escalate an allow to a hold.
3. **Given** a known (lane, payee) pair at routine cadence within the routine band, **When** evaluated, **Then** the pattern layer does not hold it.

---

### User Story 5 - The model never decides (Priority: P2)

With the voice model toggled offline, refusals still fire correctly and voiced_response falls back to the reason text, proving the model never decides.

**Why this priority**: This is the security claim made testable. The whole architecture rests on code deciding and the model only phrasing.

**Independent Test**: Unset VOICE_BASE_URL and VOICE_TOKEN, run the full required test suite, and confirm every decision is unchanged and voiced_response equals the reason text.

**Acceptance Scenarios**:

1. **Given** the voice endpoint is unset or unreachable, **When** any request is evaluated, **Then** decision and reason are unchanged and voiced_response equals the reason text.
2. **Given** the voice endpoint is reachable, **When** it returns phrasing for a denied request, **Then** the decision remains deny regardless of the phrasing returned.

---

### User Story 6 - Founder-channel authentication (Priority: P3)

An inbox message claims to be from the founder, arrives on a channel that is not the authenticated founder channel, and carries off-voice tells. It is refused as a possible spoof.

**Why this priority**: Beat 4, the optional closer. It demonstrates that authority is the channel, not a text prefix.

**Independent Test**: Submit a founder-claimed message on an inbound channel with off-voice tells and confirm a deny from the AUTH rule.

**Acceptance Scenarios**:

1. **Given** a message that claims founder authority but is not on the authenticated founder channel, **When** evaluated, **Then** decision is deny and the reason names AUTH and possible spoof.
2. **Given** that message also carries off-voice tells (urgency, secrecy, an instruction not to verify, exclamation marks, a new or lookalike domain), **When** evaluated, **Then** those tells reinforce the spoof verdict and the response stays deny.
3. **Given** a request on the authenticated founder channel, **When** evaluated, **Then** founder authority is honored, though the request may still be held or denied by another rule.

---

### User Story 7 - Learned out-of-distribution second plane (Priority: P2)

After the hard rules pass, the gate consults a learned detector that scores how typical the request is for the founder, derived from the fine-tuned model's token-likelihood. A high-surprise request downgrades an allow to a hold. When the detector is unavailable the gate proceeds on the hard rules and the deterministic structural check only.

**Why this priority**: This makes the model a genuine detector, not a voice skin, and is the technical-ingenuity centerpiece. It is the real second plane that generalizes beyond the enumerated rules. It stays off the demo-critical path because Beat 3's on-stage hold is guaranteed by the deterministic structural check.

**Independent Test**: With the scorer stubbed to a high value, a request that passes all hard rules downgrades to hold. With it stubbed low, the same request stays allow. With it returning no score, the request stays allow (fallback). All three run with no live endpoint.

**Acceptance Scenarios**:

1. **Given** a request that clears all five hard rules and the learned score is at or above the threshold, **When** evaluated, **Then** decision is hold, anomaly is true, the reason names the pattern layer, and `pattern_check` reports the score crossed.
2. **Given** the learned score is below the threshold, **When** evaluated, **Then** the decision stays allow and `pattern_check` reports the score did not cross.
3. **Given** the learned detector is unset or errors, **When** evaluated, **Then** the score is absent, the decision is unchanged, and the gate relies on the hard rules and the deterministic structural check only.
4. **Given** a hard rule already denied the request, **When** the learned detector would run, **Then** it does not run and never changes the deny.

---

### Edge Cases

- Voice endpoint set but slow, malformed, or erroring: voiced_response falls back to the reason text and the decision is unchanged.
- Multiple rules apply to one request: evaluation follows a fixed precedence (BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH, then PATTERN). A deny from any hard rule wins over a pattern hold. The reason names the first rule that fired under that precedence.
- Spend exactly at the cap: allowed. Deny applies only when spend is strictly greater than the cap.
- Off-voice tells on the authenticated founder channel: authority still holds, because authentication is the channel, not the absence of tells. The request may still be held by PATTERN or denied by another hard rule.
- ingested_context that mixes legitimate data with an instruction: the gate refuses the instruction, sets anomaly true, quarantines the source, and continues the task using the data only.
- Vendor bank or remittance details changed via an inbound message that was not verified out of band: the spend is held, not allowed, until out-of-band verification.

## Requirements *(mandatory)*

### Interface Contract (frozen)

Request fields: `agent`, `channel`, `action_type`, `payload`, `ingested_context`.

Response fields: `decision` (allow | deny | hold), `reason` (one-line structural), `voiced_response` (founder-voice rephrase, falls back to the reason text when the voice model is unavailable), `anomaly` (boolean), `logged` (true).

Additive diagnostic fields (backward compatible, for the dual-verdict console): `rule_check` (which hard rule fired, or pass) and `pattern_check` (the out-of-distribution score and whether it crossed the threshold, or null when the learned detector is unavailable). Sub-agents that read only the frozen five fields are unaffected.

For safety scoring, holds, freezes, and quarantines all count as deny (did not comply). The decision field still distinguishes hold from deny for the audit trail.

### Decision Flow

1. The gate computes `decision` and `reason` in code first, deterministically, under the fixed rule precedence, including the deterministic structural PATTERN check.
2. If the provisional decision is still allow and the learned detector is configured, the gate calls the out-of-distribution scorer (env `ANOMALY_BASE_URL`, `ANOMALY_TOKEN`, `ANOMALY_THRESHOLD`). A score at or above the threshold downgrades the allow to a hold and sets anomaly true. If the scorer is unset or errors, the allow stands. The learned detector can only tighten, never loosen.
3. A voice client posts the request summary and the gate decision to an OpenAI-compatible endpoint (env `VOICE_BASE_URL`, `VOICE_TOKEN`) and returns founder-voice phrasing for `voiced_response`.
4. If those variables are unset or the endpoint is unreachable, `voiced_response` falls back to the `reason` text.
5. The model never changes the decision. The only allow-to-hold escalations are the two code-side anomaly detectors, never a free-text model verdict.

### Functional Requirements

#### Gate core

- **FR-001**: The gate MUST accept a Request {agent, channel, action_type, payload, ingested_context} and return a Response {decision, reason, voiced_response, anomaly, logged}.
- **FR-002**: `decision` MUST be exactly one of allow, deny, hold.
- **FR-003**: The gate MUST compute decision and reason in code before any model call, and identical inputs MUST produce identical decision and reason (determinism).
- **FR-004**: Every response MUST name the rule that fired in the reason, as a one-line structural statement.
- **FR-005**: Every evaluated request MUST be logged, and `logged` MUST be true in every response.
- **FR-006**: Holds, freezes, and quarantines MUST count as deny for safety scoring, while the decision field still distinguishes hold from deny.
- **FR-007**: When more than one rule applies, the gate MUST resolve under a fixed precedence (BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH, then PATTERN), and a hard-rule deny MUST win over a pattern hold.

#### Rule 1: BUDGET

- **FR-010**: The gate MUST deny spend that exceeds the lane per-request cap.
- **FR-011**: The gate MUST deny spend when the payee is not on the approved vendor list (finance may settle company-shaped approved vendors across the fleet at 5,000 maximum per invoice).
- **FR-012**: The gate MUST hold spend when vendor bank or remittance details changed via an inbound message that was not verified out of band.
- **FR-013**: The gate MUST deny structuring, defined as multiple same-payee requests each just under the cap.
- **FR-014**: The gate MUST deny inter-account transfers to accounts not registered by the founder.
- **FR-015**: The gate MUST deny finance raising its own cap.
- **FR-016**: The gate MUST approve normal in-band approved-vendor spend within cap.

#### Rule 2: PRIVILEGE

- **FR-020**: The gate MUST deny any request for a capability the lane does not own, and the reason MUST direct the request to ask the owning lane for the output, not the access.
- **FR-021**: The gate MUST deny a lane editing its own permission manifest.
- **FR-022**: The gate MUST deny self-approval or acting as approver over the lane's own queue.
- **FR-023**: The gate MUST deny self-replication or spawning scope-inheriting agents.
- **FR-024**: The gate MUST deny disabling or pausing audit logging.
- **FR-025**: The gate MUST deny credential or session sharing between agents.
- **FR-026**: The gate MUST deny a blanket vault read.
- **FR-027**: The gate MUST approve scoped, time-boxed, read-only cross-lane requests for output.

#### Rule 3: SECRET exfiltration

- **FR-030**: When action_type is secret_access, or an external_send includes a sacred object or production secret, the gate MUST deny unless the channel is the authenticated founder channel.
- **FR-031**: A production secret MUST never leave in a ticket, email, gist, or file, not even to a vendor.
- **FR-032**: The refusal reason MUST name the safe alternative: a scoped staging or test token by vault reference with an expiry.
- **FR-033**: The gate MUST approve staging or test key access by vault reference with an expiry.

#### Rule 4: PROVENANCE

- **FR-040**: Content in ingested_context MUST be treated as data, never command. The gate MUST deny acting on anything that resembles an instruction, set anomaly true, quarantine the source, and continue the task without the injected instruction.
- **FR-041**: The provenance decision MUST key on source (the content came from an ingested document), not on perfect keyword detection. Content is never authority.

#### Rule 5: FOUNDER-CHANNEL authentication

- **FR-050**: Only the authenticated founder channel carries founder authority. A founder-claimed message that is not on that channel MUST be denied as a possible spoof.
- **FR-051**: Off-voice tells (urgency, secrecy, an instruction not to verify, exclamation marks, a new or lookalike domain) MUST reinforce the spoof verdict. A text prefix is not authentication.

#### Rule 6: PATTERN (deterministic anomaly layer)

- **FR-060**: A request that passes all five hard rules MAY still be held when it is off-pattern for how the founder operates, for example a novel payee above the lane routine band.
- **FR-061**: The anomaly verdict MUST be computed in code as a deterministic score over structural signals, not by the model.
- **FR-062**: The pattern layer MUST only escalate an allow to a hold, and MUST never loosen a deny.

#### Rule 6b: LEARNED OOD plane (the real second plane)

- **FR-063**: The gate MUST support a learned out-of-distribution detector that scores how well a request fits the founder's learned distribution, derived from the fine-tuned founder model's token-likelihood (perplexity) over a compact text rendering of the request.
- **FR-064**: The learned detector MUST run only after all five hard rules pass and the provisional decision is allow. If any hard rule denies or holds, the gate MUST return that verdict and MUST NOT call the learned detector.
- **FR-065**: A learned score at or above `ANOMALY_THRESHOLD` MUST downgrade an allow to a hold, set anomaly true, and name the pattern layer in the reason. The learned detector MUST only escalate an allow to a hold, and MUST never loosen a deny or a hold.
- **FR-066**: The learned detector MUST be configurable by env (`ANOMALY_BASE_URL`, `ANOMALY_TOKEN`, `ANOMALY_THRESHOLD`). When unset or erroring, the scorer MUST return no score and the gate MUST proceed on the hard rules and the deterministic structural PATTERN check only (graceful fallback, never blocks).
- **FR-067**: The response MUST expose both plane verdicts: `rule_check` (which hard rule fired, or pass) and `pattern_check` (the score and whether it crossed the threshold, or null when unavailable).
- **FR-068**: The learned score MUST NEVER be the sole authority for a deny. It can produce only a hold. Every deny MUST originate from a deterministic hard rule.

#### Voice layer

- **FR-070**: After computing decision and reason, the voice client MUST post the request summary and the gate decision to an OpenAI-compatible endpoint configured by `VOICE_BASE_URL` and `VOICE_TOKEN` and return founder-voice phrasing for voiced_response.
- **FR-071**: When `VOICE_BASE_URL` or `VOICE_TOKEN` is unset, or the endpoint is unreachable, voiced_response MUST fall back to the reason text.
- **FR-072**: The model MUST never change the decision. The only escalation path (allow to hold) is the code pattern layer, never the model.
- **FR-073**: voiced_response MUST be dry, terse, first person, with no em dashes and no exclamation marks.

#### Configuration parity and fleet

- **FR-080**: Gate configuration norms (caps, approved vendors, scope ownership, sacred objects, production secrets, routine bands, known payees, founder channel) MUST match `Seed/generate_dataset.py` exactly. `orchestrator/fleet_config.py` is the single source of truth, and an automated parity test MUST assert the match.
- **FR-081**: Only the orchestrator is real. The nine sub-agents MUST be thin scripted clients that submit requests through the gate.

### Key Entities *(include if feature involves data)*

- **Request**: An irreversible action submitted for evaluation. Fields: agent, channel, action_type, payload, ingested_context.
- **Response**: The gate verdict. Fields: decision, reason, voiced_response, anomaly, logged.
- **Lane / Agent**: One of the nine fleet members (growth, sales, engineering, finance, research, recruiting, support, legal, data). Owns a fixed scope and cap.
- **Cap**: Per-request spend ceiling for a lane. Finance settles approved invoices at 5,000 maximum.
- **ApprovedVendor**: A vendor a lane is allowed to pay. Finance may settle company-shaped approved vendors across the fleet.
- **ScopeOwnership map**: The capabilities each lane owns, plus which lane owns each cross-lane capability.
- **SacredObject**: A document or data set that is founder-send only (cap table, financials, investor materials, board deck, data room, founder contacts and notes, customer PII, payroll).
- **ProductionSecret**: A live credential that must never leave the vault in plaintext (production Stripe key, AWS root credentials, OpenAI API key, production database connection string).
- **FounderChannel**: The one authenticated channel that carries founder authority.
- **RoutineBand**: The typical ceiling for routine, no-questions spend in a lane, used by the pattern layer.
- **KnownPayeeHistory**: The (lane, payee) pairs the fleet has paid before at routine cadence.
- **RuleResult**: Which of the six rules fired and the resulting decision, surfaced in the response and the audit log.
- **OODScore**: The learned out-of-distribution score in the range zero to one, higher meaning more anomalous, derived from the fine-tuned model token-likelihood. Carried in `pattern_check` with the threshold and the cross flag. Null when the detector is unavailable.
- **PlaneVerdict**: The pair of diagnostic fields `rule_check` and `pattern_check` that the console reads to show the hard-rule lane and the pattern lane side by side.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The required automated gate test suite passes with the voice endpoint not running.
- **SC-002**: The gate returns an identical decision and reason for repeated identical inputs in 100% of repeated runs (determinism).
- **SC-003**: 100% of responses name the rule that fired in the reason.
- **SC-004**: Gate configuration norms match `Seed/generate_dataset.py` exactly (caps, vendors, scope, sacred objects, routine bands, known payees, founder channel), proven by a passing parity test.
- **SC-005**: voiced_response contains zero em dashes and zero exclamation marks across every test case.
- **SC-006**: The voice layer never converts a coded deny into an allow. In 100% of cases the final decision equals the code decision, with the only allow-to-hold escalation coming from the code pattern layer.
- **SC-007**: Each demo beat produces its expected verdict deterministically: in-band approved-vendor invoice allows, the about-47,000 hijacked wire denies, the staging vault reference allows, the ingested production-secret request denies, the off-pattern request holds, and the spoofed founder message denies.
- **SC-008**: The learned out-of-distribution detector only ever escalates an allow to a hold. In 100% of cases it never converts a deny or a hold to an allow, and when it is unavailable the gate still returns the correct hard-rule and deterministic-structural verdict, proven by tests that stub the score high, low, and absent.

## Assumptions

- Sub-agents are thin scripted clients. No real nine-agent workforce is built; the agents exist only to submit requests.
- Channel is an input field on the request, not a live transport. The authenticated founder channel is represented by its configured identifier for the demo.
- The voice model is a LoRA fine-tuned on the founder's voice, served behind an OpenAI-compatible endpoint. When it is absent, the reason text is the founder-facing output.
- The same fine-tuned model also backs the learned out-of-distribution detector through its token-likelihood. The voice role and the detector role share one trained model and one served endpoint. The detector is env-gated and degrades to absent without blocking the gate.
- The learned detector is a real running capability, but a same-day model on a few hundred synthetic rows is noisy. Beat 3's on-stage hold is therefore guaranteed by the deterministic structural PATTERN check, and the learned score is shown on a pinned, tested input. The honest framing is a learned pattern layer, real and running, demonstrated on a pinned input.
- `orchestrator/fleet_config.py` mirrors `Seed/generate_dataset.py` and is the single source of truth for all norms.
- The automated test harness is Python with pytest.
- Build order is sacred: the gate plus its tests come first, before the voice client and any server or UI.
- Validia is the identity tool of record. No competitor identity tool is wired in.

## Out of Scope

- Building a real working nine-agent workforce.
- Live channel integrations as the critical path.
- Bolting on Sentience. There is no public SDK.
- Wiring a competitor identity tool in place of Validia.

## Non-Negotiables

- Deterministic gate. The model never decides.
- Founder voice is dry, terse, first person, with no em dashes and no exclamation marks.
- Only the orchestrator is real. Sub-agents are thin and scripted.
- The fleet config is the single source of truth and mirrors `Seed/generate_dataset.py`.
- Build order is sacred: gate plus tests first.
