# Founder Orchestrator

A personalized autonomous agent that governs a solo founder's fleet of nine
OpenClaw sub-agents. It answers the question every agent demo dodges: **who stops
the agent when it's wrong?**

The orchestrator is a real OpenClaw agent (memory, channels, the founder's
voice), but it cannot take any irreversible action (spend, external send, secret
access, permission change) without clearing **two judges first**. Either judge can
refuse. Neither can loosen the other. Nothing is approved unless both agree.

> **Personalization is the security.** One model, fine-tuned on Lightning on how
> this founder works, is both the voice and the second judge.

## The two judges

Every irreversible request is put to two independent judges, and the final
decision is the **stricter** of the two (`deny > hold > allow`):

1. **The gate — your written rules.** Pure deterministic code. Six rules in fixed
   precedence: BUDGET, PRIVILEGE, SECRET, PROVENANCE, AUTH, PATTERN. Same input,
   same verdict, every time, fully auditable. It can never be talked out of a
   refusal, and it names the exact rule that fired.
2. **The model — your trained instinct.** A founder LoRA (Qwen2.5-3B, fine-tuned
   on Lightning) that reads each request and forms its own verdict, in the
   founder's voice. It catches off-pattern requests the rules cannot enumerate,
   and it can only ever *add* caution, never remove it.

If the model judge is unavailable, the result is the deterministic gate alone:
the floor that proves the model never has the last word on an allow.

```
request
   │
   ├──▶ the model (LoRA)  ── proposes a verdict, independently
   └──▶ the gate (code)   ── decides by rule, deterministically
                │
          stricter wins  ── neither can loosen the other
                │
          founder voice + the next action the orchestrator takes
```

## Built on

- **OpenClaw** — the agent runtime. The orchestrator runs as a real OpenClaw
  agent and calls the deterministic gate as an MCP tool before acting
  (`orchestrator/mcp_gate.py`). It is structurally unable to act without the
  verdict.
- **Lightning AI** — the founder LoRA is trained on Lightning Studios and served
  on LitServe behind an OpenAI-compatible endpoint (`orchestrator/serve_voice.py`).
  The same endpoint backs the voice and the model judge.

## Layout

```text
orchestrator/
  fleet_config.py        single source of truth, mirrors Seed/generate_dataset.py
  gate.py                the deterministic gate: evaluate(request) -> verdict
  model_judge.py         the LoRA as a judge: propose(request) -> verdict | None
  orchestrate.py         the two-judge combiner: stricter wins, neither loosens
  voice.py               founder-voice client, hard fallback to reason text
  anomaly.py             structural + learned OOD score (the anomaly meter)
  mcp_gate.py            the gate exposed as an MCP tool for the OpenClaw agent
  openclaw_orchestrator.py  runs a real OpenClaw agent turn, governed by the gate
  server.py              FastAPI: /evaluate, /agent, /profile, serves the console
  serve_voice.py         LitServe script for the Studio (serves the merged LoRA)
  static/                the Orchestrator Console (index.html, console.js)
tests/
  test_gate.py           the required cases, per-rule, determinism
  test_orchestrate.py    two-judge: stricter wins, neither loosens, fallback
  test_anomaly.py        the learned plane: tighten-only, graceful fallback
  test_config_parity.py  the gate config matches the dataset generator
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

Open `http://127.0.0.1:8080/`. Fire a scenario (it shows the legitimate request
approved, then the attack refused), click a lane, or type your own attack into
the red-team box. Flip **deterministic gate only** to unplug the model and watch
the refusals still fire.

## Run the OpenClaw agent

```bash
pip install mcp
openclaw mcp add governance-gate \
  --command "$PWD/.venv/bin/python" --arg -m --arg orchestrator.mcp_gate --cwd "$PWD"
python -m orchestrator.openclaw_orchestrator drain   # finance budget drain (deny)
python -m orchestrator.openclaw_orchestrator legit   # normal invoice (allow)
```

A real OpenClaw agent receives the request, calls `governance_gate`, obeys the
two-judge verdict, and replies in the founder voice. It cannot be talked out of a
refusal: pressure it to approve a fraudulent wire and it still denies, because the
verdict is computed in code, not by the model.

## Results

- 44 automated tests green; the gate path is deterministic and offline-safe.
- Founder LoRA (Qwen2.5-3B): held-out accuracy 84%, val ppl 6.91.
- In the two-judge design, a model error fails safe: it can never loosen a gate
  deny, and the abstain guard drops noisy outputs so a weak model defaults to the
  gate.

## Honest framing

The deterministic gate is demo-reliable by design. The learned model is a real,
running fine-tune, but on a few hundred rows it is noisy, so when it is unsure it
abstains and the gate decides. The capability is real, the demo's reliability is
engineered, and both are true at once.

## Deployment posture

See [HARDENING.md](HARDENING.md) for the hardened OpenClaw deployment config.
