# Founder's Orchestrator

> 🏆 1st place, NYTechWeek Agents Hackathon (Lightning AI, Validia & Sentience), June 2026.

A trusted orchestrator that sits between a solo founder and their nine AI
employees, signing off on or refusing anything they try to do that can't be
undone. Built solo in a day as a real OpenClaw agent, with a deterministic rules
engine and a small model fine-tuned on Lightning on how the founder actually works.

*Runs locally in 30 seconds (below). No hosted demo. The full experience needs
the local OpenClaw agent plus the served model.*

## The problem

You're a solo founder with nine AI employees: growth, sales, engineering,
finance, legal, and more. Each one can spend money, email outsiders, and touch
secrets. And each one can be tricked into doing real damage.

Any of them can be turned against you by a poisoned document or a spoofed
message. And it's not only AI attacks: a scam that reaches your phone lets a bad
actor message your agents from your own trusted channels. Counting on a busy,
sleep-deprived founder to catch every bad request by hand is the weak point.

## The boss, and two checks

So I built the boss: one trusted orchestrator above the other nine. Before any
employee does something irreversible, it asks the boss for sign-off, and the boss
runs the request past **two independent checks.**

Guardrails on the model still matter, and I use them. But a model can be
influenced no matter how well you prompt or train it. The right phrasing, the
right pressure, the right poisoned context, and it bends. So the floor can't be
another model. It has to be something that doesn't negotiate.

**First, deterministic code.** Hard rules for spend caps, approved vendors, what
counts as a secret, and whether the request really came from you. No model in the
loop. You can pressure it to approve a fraudulent $47,000 wire all you want. It
still refuses, because that "no" is computed in code, not decided by a model that
can be talked into things.

**Second, a small model** fine-tuned on how the founder actually works and talks,
so it notices when a request feels off, even from an account that looks legitimate.

The two checks work together. Anything ambiguous escalates to you. If the code
would approve something but the model senses it isn't how you'd operate, caution
wins. Every decision you confirm or correct teaches it more.

**The idea that ties it together: personalization and security are the same
mechanism.** The model that speaks in your voice is the same model that senses
what doesn't sound like you.

> The orchestrator refusing a $47,000 wire is the product. Nine agents booting is
> just motion.

## How a request flows

```
request
   │
   ├──▶ the model      proposes a verdict, on its own, in your voice
   └──▶ the rules      decide by code, deterministically
                │
          stricter wins:  deny > hold > allow, neither loosens the other
                │
          the boss acts: issues the token, freezes the payment, routes it,
          or holds it for you, and says so in your voice
```

The six rules run in fixed precedence: BUDGET, PRIVILEGE, SECRET, PROVENANCE,
AUTH, PATTERN. The model runs alongside them. If the model is unavailable or
unsure, it abstains and the rules decide alone. The model never has the last word
on an allow.

## Built on

- **OpenClaw**: the agent runtime. The boss runs as a real OpenClaw agent and
  calls the rules engine as an MCP tool (`orchestrator/mcp_gate.py`). It is
  structurally unable to act without the verdict. Pressure it to approve a
  fraudulent wire and it still refuses, because the decision is computed in code,
  not by the model.
- **Lightning AI**: the founder model is fine-tuned on Lightning Studios and
  served on LitServe behind an OpenAI-compatible endpoint (`orchestrator/serve_voice.py`).
  One model, three jobs: the voice, the second check, and the anomaly sense.

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

## Configure the OpenClaw agent

The boss runs as a real OpenClaw agent that calls the gate as an MCP tool.

**1. Install OpenClaw and the MCP SDK.**

```bash
npm install -g openclaw
source .venv/bin/activate && pip install mcp
```

**2. Give OpenClaw a model provider** (the agent's reasoning brain. Any
OpenClaw-supported provider works; this build used OpenAI).

```bash
export OPENAI_API_KEY="sk-..."
openclaw models            # the provider should show status=usable
```

**3. Register the deterministic gate as an MCP tool.** Pass the served founder
LoRA endpoint as env so the tool can run the model judge and speak in the founder
voice. (OpenClaw spawns this stdio server per turn and only it gets these vars.)

```bash
openclaw mcp add governance-gate \
  --command "$PWD/.venv/bin/python" --arg -m --arg orchestrator.mcp_gate \
  --cwd "$PWD" \
  --env VOICE_BASE_URL="https://<your-litng-subdomain>.cloudspaces.litng.ai/v1" \
  --env VOICE_TOKEN="<bearer-or-anything-if-open>"

openclaw mcp probe governance-gate     # should report: governance-gate: 1 tools
```

**4. Run a governed agent turn.**

```bash
python -m orchestrator.openclaw_orchestrator drain   # finance budget drain -> deny
python -m orchestrator.openclaw_orchestrator legit   # normal invoice -> allow
```

The agent receives the request, calls `governance_gate`, obeys the two-judge
verdict, and replies in the founder voice. It cannot be talked out of a refusal:
the verdict is computed in code, not by the model.

The console's live-agent path calls this same agent via `POST /agent`, so launch
the server with the keys in its environment:

```bash
source .demo.env && uvicorn orchestrator.server:app --port 8080
```

## Secrets (local, gitignored)

Keys live only in a gitignored `.demo.env`, never in the repo:

```bash
# .demo.env
export OPENAI_API_KEY="sk-..."                                   # OpenClaw agent brain
export VOICE_BASE_URL="https://<subdomain>.cloudspaces.litng.ai/v1"  # served LoRA
export VOICE_TOKEN="<bearer-or-anything-if-open>"
```

`source .demo.env` before running the server or the agent.

## What the model was trained on

The LoRA is fine-tuned on the founder's own governance decisions, not generic
data. Each row is `agent message -> founder's decision + one-line reason`
(Alpaca format), so the model learns to *decide and explain like the founder*.

- **520 rows**, generated deterministically by `Seed/generate_dataset.py`
  (`python3 generate_dataset.py --count 520 --seed 20260606`, rerunnable).
- **70% normal governance** (364 rows) and **30% attacks** (156 rows, evenly
  split across budget abuse, privilege escalation, secret exfiltration, and
  injected-document attacks).
- Built by combinatorial templating: 35 scenario families x authored phrasing
  variants x randomized parameters (9 agents, 30+ vendors, name pools, amounts).
  Normal and attack rows **share the same vendors, people, and tools on purpose**,
  so the boundary the model learns is structural (caps, payee history, scope
  ownership, channel, voice tells), not keyword spotting. The same Datadog invoice
  is paid when the account matches history and frozen when the bank details
  changed by email.
- The norms baked into the data (caps, approved vendors, scope ownership, sacred
  objects, routine bands) are the **exact same norms `fleet_config.py` enforces**,
  so the model and the gate describe one world. `tests/test_config_parity.py`
  asserts they never drift.
- A separate **180-row voice-enrichment set** (`Seed/founder_voice_enrich.json`:
  delegation, status, why, pressure, compressed, pushback) sharpens tone.
- Validation gates on every row: zero em dashes, zero exclamation marks in
  outputs, no corporate filler, near-duplicate rejection.
- A **held-out eval** of 150 rows with zero surface overlap
  (`Seed/held_out_eval.labeled.json`) measures the numbers that matter:
  false-approve rate on attacks and false-refuse rate on legitimate requests.

Result on the held-out set (Qwen2.5-3B + LoRA, 4 epochs): 84% accuracy, val ppl
6.91, 12% false-approve on attacks (caught anyway by the deterministic gate),
10% false-refuse on legit. In the two-judge design a model error fails safe.

## Train and serve the founder LoRA (Lightning)

On a Lightning Studio with a GPU:

```bash
pip install 'litgpt[all]' litserve
litgpt download Qwen/Qwen2.5-3B-Instruct
litgpt finetune_lora Qwen/Qwen2.5-3B-Instruct \
  --data JSON --data.json_path "Seed/founder_orchestrator_lora.json" \
  --data.val_split_fraction 0.05 --train.epochs 4 \
  --lora_r 16 --lora_alpha 32 --out_dir out/founder-qwen-lora
litgpt merge_lora out/founder-qwen-lora/final
python "Seed/score_model.py" --model out/founder-qwen-lora/final   # held-out eval

export FOUNDER_LORA_DIR=out/founder-qwen-lora/final
export VOICE_BEARER="<random>"
python orchestrator/serve_voice.py        # OpenAI-compatible /v1 on port 8000
```

Expose port 8000 and use its public URL as `VOICE_BASE_URL` (with `/v1`). The same
endpoint backs the voice and the model judge, so a better model upgrades both.

## Results

- 44 automated tests green; the gate path is deterministic and offline-safe.
- Founder LoRA (Qwen2.5-3B, Lightning): held-out accuracy 84%, val ppl 6.91.
- A model error fails safe: it can never loosen a gate deny, and the abstain
  guard drops noisy outputs so a weak model defaults to the gate.

## Honest framing

The deterministic rules are the part I'd stake the demo on: 44 tests, and they
run offline with the model unplugged, so the refusals are provable, not promised.
The model is real but small, fine-tuned in a day on a few hundred of my own
decisions, so it's the softer signal: when it's unsure it steps back and the
rules decide, and it can only ever add caution, never remove it. The capability
is real, the reliability is engineered, and both are true.

See [HARDENING.md](HARDENING.md) for the hardened OpenClaw deployment posture.
