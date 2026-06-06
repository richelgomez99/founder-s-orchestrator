# Founder Orchestrator

## What this is, in plain language

You are a solo founder with nine AI employees: growth, sales, engineering,
finance, research, recruiting, support, legal, data. Each one can do real damage.
They spend money, send email to outsiders, touch secrets, and change settings.
Any one of them can be tricked by a poisoned document, a spoofed message, or a
clever prompt, and turned against you. You are the only person who can authorize
the dangerous stuff, which makes you the single point of failure.

This is **the boss**: one trusted agent that sits above the nine. Every employee
has to ask the boss before doing anything irreversible. The boss approves the
normal asks and refuses the dangerous ones.

What makes it trustworthy: an irreversible request is put to **two judges**, and
the boss obeys the stricter one.

- **The gate (code).** A rule-checker computes allow, deny, or hold from hard
  rules: spend caps, approved vendors, who owns which tool, what counts as a
  secret, whether the message really came from you. Plain deterministic code, no
  model. Unplug everything and the boss still refuses the $47,000 wire correctly.
- **The model (you).** A small LoRA fine-tuned on how you actually work and talk.
  It reads each request and forms its own verdict, in your voice. Because it
  learned your normal patterns, a malicious request reads as off-pattern even
  from a trusted-looking account.

The safety rule is simple: **either judge can refuse, neither can wave something
through alone.** Nothing is approved unless both agree, and the model can only
ever *add* caution, never remove it. A deny from the code is absolute.

That is the one idea that ties it together: **personalization and security are
the same mechanism.** The model that speaks in your voice is the same model that
senses what is off-pattern for you.

> The orchestrator refusing a $47,000 wire is the product. Nine agents booting is
> just motion.

## The two judges

```
request
   │
   ├──▶ the model (LoRA)  ── proposes a verdict, on its own, in your voice
   └──▶ the gate (code)   ── decides by rule, deterministically
                │
          stricter wins   ── deny > hold > allow; neither loosens the other
                │
          the boss acts: issues the token, freezes the payment, routes it,
          or holds it for you, and says so in your voice
```

The gate's six rules run in fixed precedence: BUDGET, PRIVILEGE, SECRET,
PROVENANCE, AUTH, PATTERN. The model judge runs alongside it. If the model is
unavailable or unsure, it abstains and the gate decides alone. The model never
has the last word on an allow.

## Built on

- **OpenClaw** — the agent runtime. The boss runs as a real OpenClaw agent and
  calls the gate as an MCP tool (`orchestrator/mcp_gate.py`). It is structurally
  unable to act without the verdict. Pressure it to approve a fraudulent wire and
  it still refuses, because the decision is computed in code, not by the model.
- **Lightning AI** — the founder LoRA is trained on Lightning Studios and served
  on LitServe behind an OpenAI-compatible endpoint (`orchestrator/serve_voice.py`).
  One model, three jobs: the voice, the second judge, and the anomaly sense.

## What was built today, in order

1. **The gate and its config**, with tests that prove it approves a real finance
   invoice and refuses a hijacked $47,000 wire. The load-bearing wall.
2. **The attack demos** (finance budget-drain, engineering secret-exfiltration,
   off-pattern hold, founder impersonation): each shows the legit request approved,
   then the attack refused.
3. **The console** that makes all of this visible for the judges, including real
   OpenClaw agent turns.
4. **The second judge and the LoRA**: the model promoted from rephraser to
   co-judge, trained on Lightning.

## Layout

```text
orchestrator/
  fleet_config.py          single source of truth, mirrors Seed/generate_dataset.py
  gate.py                  the deterministic gate: evaluate(request) -> verdict
  model_judge.py           the LoRA as a judge: propose(request) -> verdict | None
  orchestrate.py           the two-judge combiner: stricter wins, neither loosens
  voice.py                 founder-voice client, hard fallback to reason text
  anomaly.py               structural + learned OOD score (the anomaly meter)
  mcp_gate.py              the gate as an MCP tool for the OpenClaw agent
  openclaw_orchestrator.py runs a real OpenClaw agent turn, governed by the gate
  server.py                FastAPI: /evaluate, /agent, /profile, serves the console
  serve_voice.py           LitServe script for the Studio (serves the merged LoRA)
  static/                  the Orchestrator Console (index.html, console.js)
tests/                     gate cases, two-judge combiner, anomaly, config parity
```

## Run the tests

The deterministic gate path needs no model and no network.

```bash
python -m venv .venv && source .venv/bin/activate
pip install pytest
python -m pytest -q          # 44 tests
```

## Run the console

```bash
source .venv/bin/activate
pip install fastapi uvicorn
# optional: point at the served founder LoRA (voice + model judge)
export VOICE_BASE_URL="https://<your-litng-subdomain>.cloudspaces.litng.ai/v1"
export VOICE_TOKEN="<your-bearer-or-anything-if-open>"
uvicorn orchestrator.server:app --port 8080
```

Open `http://127.0.0.1:8080/`. Each scenario shows the legitimate request
approved, then the attack refused. Click a lane to fire its request, or type your
own attack into the red-team box. Flip **deterministic gate only** to unplug the
model and watch the refusals still fire.

## Run the OpenClaw agent

```bash
pip install mcp
openclaw mcp add governance-gate \
  --command "$PWD/.venv/bin/python" --arg -m --arg orchestrator.mcp_gate --cwd "$PWD"
python -m orchestrator.openclaw_orchestrator drain   # finance budget drain (deny)
python -m orchestrator.openclaw_orchestrator legit   # normal invoice (allow)
```

## Results

- 44 automated tests green; the gate path is deterministic and offline-safe.
- Founder LoRA (Qwen2.5-3B, Lightning): held-out accuracy 84%, val ppl 6.91.
- A model error fails safe: it can never loosen a gate deny, and the abstain
  guard drops noisy outputs so a weak model defaults to the gate.

## Honest framing

The deterministic gate is demo-reliable by design. The learned model is a real,
running fine-tune, but on a few hundred rows it is noisy, so when it is unsure it
abstains and the gate decides. The capability is real, the demo's reliability is
engineered, and both are true at once.

See [HARDENING.md](HARDENING.md) for the hardened OpenClaw deployment posture.
