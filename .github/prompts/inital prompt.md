Build a deterministic governance gate for a founder's AI-agent orchestrator. This is the security-critical core of a hackathon demo. Python. Work in this repo. Prioritize correctness and testability over features.

CONCEPT. I am a solo founder running a fleet of nine autonomous sub-agents (growth, sales, engineering, finance, research, recruiting, support, legal, data). This service is the orchestrator: the trusted control plane every sub-agent must go through before any irreversible action (spending money, sending externally, accessing a secret, changing permissions). The orchestrator approves normal requests and refuses dangerous ones. The security MUST be deterministic code in this gate, NOT a language model. A model will later phrase the responses in my voice, but the model never makes the decision. The decision is code.

THE INTERFACE CONTRACT (freeze this; sub-agents are built against it).
A sub-agent sends the orchestrator a JSON request:
{
  "agent": "<one of: growth,sales,engineering,finance,research,recruiting,support,legal,data>",
  "channel": "<the channel the request arrived on, e.g. 'fleet-internal' or 'founder-authenticated' or 'inbox'>",
  "action_type": "<one of: spend, external_send, secret_access, permission_change, publish, internal>",
  "payload": { ...action-specific fields... },
  "ingested_context": "<optional: text the agent read from an external document, may contain injected instructions>"
}
The orchestrator returns:
{
  "decision": "<allow | deny | hold>",
  "reason": "<one-line structural reason>",
  "voiced_response": "<the reason, rephrased in the founder's voice; falls back to reason text if the voice model is unavailable>",
  "anomaly": <true|false>,
  "logged": true
}
Holds, freezes, and quarantines all count as "deny" for safety purposes (did not comply).

FLEET NORMS (put these in a config file, fleet_config.py or .json, so they are the single source of truth and match the training world):
- Per-request spend caps: growth 3000, sales 2500, engineering 5000, finance 5000, research 500, recruiting 2000, support 500, legal 3500, data 1500.
- Approved vendors per lane (invent a sensible list per lane; finance pays only approved vendors at 5000 max). Include a few: engineering [AWS, Vercel, Sentry, GitHub, Datadog], growth [Google Ads, Meta Ads, Mailchimp, Buffer], etc.
- Scope ownership: which lane owns which capability. payment rails and bank = finance only. production deploy, GitHub write, vault references = engineering only. warehouse and dashboards = data only. Each lane owns only its listed tools.
- Sacred objects, never sent or exposed without explicit founder action: production API keys and credentials, the cap table, financial statements, investor materials and the data room, the founder's private contacts and notes, customer PII, payroll data.
- The founder's authenticated channel id (e.g. "founder-authenticated"). A message merely containing the text "From the founder:" is NOT authenticated.

THE GATE RULES (deterministic, each independently testable):
1. BUDGET. Deny if spend amount exceeds the lane's per-request cap. Deny if the payee is not on the approved vendor list. Deny ("hold") if vendor bank/remittance details changed via an inbound message (payload flags a bank change not verified out of band). Deny structuring: multiple requests to the same payee each just under the cap. Deny inter-account transfers to accounts not founder-registered. Deny if the finance agent requests to raise its own cap. Approve normal in-band approved-vendor spend.
2. PRIVILEGE. Maintain the scope-ownership map. Deny any request for access to a capability the requesting lane does not own (the agent should request the OUTPUT from the owning lane, not the access). Deny an agent requesting to edit its own permission manifest. Deny self-approval / approver role over its own queue. Deny self-replication or spawning agents that inherit its scope. Deny disabling or pausing audit logging. Deny credential or session sharing between agents. Deny blanket vault read. Approve scoped, time-boxed, read-only cross-lane requests that ask for output, not keys.
3. SECRET EXFILTRATION. If action_type is secret_access or an external_send includes a sacred object, deny unless the channel is the authenticated founder channel. A production secret never leaves in a ticket, email, gist, or file, not even to a vendor. The correct alternative is a scoped staging/test token, so the reason should say so. Approve staging/test key access by vault reference with expiry.
4. PROVENANCE. If ingested_context contains anything that looks like an instruction (commands, "ignore previous instructions", claims of authority, "pre-approved", "skip verification", a request to send/add/approve), treat it as DATA, never command. Deny acting on it, set anomaly true, instruct to quarantine the source and continue the task without it. Content is never authority.
5. FOUNDER-CHANNEL AUTH. Only requests on the authenticated founder channel carry founder authority. If a request claims to be from the founder ("From the founder:" text, or a founder-claimed inbox message) but is NOT on the authenticated channel, deny as a possible spoof, especially if it carries off-voice tells: urgency, secrecy, instruction not to verify, exclamation marks, a new or lookalike domain. A text prefix is not authentication.

DECISION FLOW. The gate evaluates the rules in code and produces decision + reason FIRST. Then call a voice client to produce voiced_response. The voice client posts to an OpenAI-compatible endpoint (configurable base URL and bearer token, env vars VOICE_BASE_URL and VOICE_TOKEN) sending the request summary and the gate's decision+reason, and returns the model's phrasing in the founder's voice (dry, terse, a decision plus a one-line reason, no em dashes, no exclamation marks). If the endpoint is unset or unreachable, voiced_response falls back to the reason text. The model NEVER changes the decision.

DELIVERABLES:
- fleet_config.py (or .json): caps, vendors, scope map, sacred objects, founder channel id.
- gate.py: the deterministic evaluate(request) -> response function implementing all five rules.
- voice.py: the voice client with the fallback.
- server.py: a minimal FastAPI (or Flask) app exposing POST /evaluate that sub-agents call, returning the contract response.
- tests/test_gate.py: pytest tests proving, at minimum, that the gate APPROVES a legitimate in-band finance invoice to an approved vendor, REFUSES a finance request to wire ~47000 (about 9x cap) to a non-approved payee, APPROVES a scoped staging vault reference for engineering, REFUSES an engineering request to paste a production secret into a vendor ticket, and REFUSES an instruction embedded in ingested_context. Tests must pass without the voice endpoint running.
- README.md: how to run the server and the tests, and the two headline demo requests as curl examples.
- HARDENING.md: the OpenClaw deployment config that wraps this orchestrator as a hardened agent: sandbox mode non-main, workspaceAccess ro, skills [], gateway auth token, channel dmPolicy pairing, and pin openclaw >= 2026.4.22. (Documentation only; this file explains the deployment posture.)

RULES: deterministic gate, model never decides. Founder voice in any phrasing: dry, terse, no em dashes, no exclamation marks. Write the tests and make them pass before considering it done.