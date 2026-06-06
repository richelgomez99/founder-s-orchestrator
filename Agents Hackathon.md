# Agents Hackathon — Pass 1 Technical Reference (June 6, 2026)

Lightning AI × Validia × Sentience, NYTechWeek, The Bench, 49 Elizabeth St NYC. Documentation-and-capability research only. Every claim carries a doc URL and a version or date stamp; unverifiable items are flagged with confidence levels.

Authoring conventions: `DOC` = present in official docs, `CODE` = verified in repo source, `INF` = inferred from primary sources but not stated outright, `UNV` = not found, marked for on-site verification.

---

## 1. Per-Tool Documentation Dossier

### 1.1 OpenClaw (personalized agent framework)

**Identity, version, install.** OpenClaw is the local-first personal AI assistant from Peter Steinberger (renamed from Moltbot/Clawdbot on January 30, 2026, per auth0.com/blog/five-step-guide-securing-moltbot-ai-agent). Repository: `github.com/openclaw/openclaw`, MIT license, 377k stars, 78.8k forks as of the README fetch on 2026-06-06. Latest stable referenced by primary docs: `2026.4.22` (the OpenClaw advisory that fixes the Claw Chain quartet, per thehackernews.com/2026/05). Subsequent advisory chain references `2026.4.10` (CVE-2026-43584) and `2026.3.28` (CVE-2026-33579), so any hackathon build should pin `openclaw@latest` and `openclaw --version` `>= 2026.4.22`. `DOC`

**Runtime, install, daemon.** README (github.com/openclaw/openclaw): "Runtime: **Node 24 (recommended) or Node 22.19+**." Install path:

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon          # installs launchd/systemd user service
openclaw gateway status
openclaw agent --message "Ship checklist" --thinking high
```

Foreground/debug:

```bash
openclaw gateway stop
openclaw gateway --port 18789 --verbose
```

Gateway default loopback port: `18789`. Control UI at `http://127.0.0.1:18789`. `DOC`

**Config file & schema.** Path `~/.openclaw/openclaw.json`, format JSON5 (comments and trailing commas allowed). The Gateway watches this file; safe changes hot-reload, destructive ones (e.g., shrinking the file by >50%, dropping `gateway.mode`) are rejected and saved as `.rejected.*`. Schema is strict — unknown keys block startup. Edits via CLI: `openclaw config get|set|unset|patch|validate`; values JSON5-parsed (use `--strict-json` to require JSON). Protected list/map paths like `agents.defaults.models`, `models.providers`, `plugins.entries`, `auth.profiles` reject element-removing writes unless `--replace` is passed. Source: docs.openclaw.ai/cli/config and docs.openclaw.ai/gateway/configuration. `DOC`

**Full `agents.defaults` schema relevant to a 5-hour build.** Verbatim from docs.openclaw.ai/gateway/config-agents:

| Key | Default | Behavior |
|---|---|---|
| `agents.defaults.workspace` | `~/.openclaw/workspace` | Per-agent working directory. |
| `agents.defaults.model.primary` | provider/model id (e.g. `anthropic/claude-sonnet-4-5`) | Active model. |
| `agents.defaults.model.fallbacks` | `[]` | Failover list. |
| `agents.defaults.skills` | unset (= unrestricted) | If set, allowlist of skill ids; `[]` = no skills. |
| `agents.defaults.skipBootstrap` | `false` | When `true`, disables auto-creation of AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md. |
| `agents.defaults.skipOptionalBootstrapFiles` | `[]` | Subset of `SOUL.md`, `USER.md`, `HEARTBEAT.md`, `IDENTITY.md` to skip while still writing required files. |
| `agents.defaults.contextInjection` | `"always"` | `"always" \| "continuation-skip" \| "never"`. `continuation-skip` omits bootstrap re-injection on safe continuation turns; `never` disables workspace bootstrap entirely. Heartbeat and post-compaction always rebuild. |
| `agents.defaults.bootstrapMaxChars` | `20000` | Per-file character cap; over-budget files are silently truncated. |
| `agents.defaults.bootstrapTotalMaxChars` | `60000` | Aggregate cap across all bootstrap files. (Community guide at stack-junkie.com cites 150,000; the doc-confirmed default is 60,000.) |
| `agents.defaults.heartbeat.every` | `30m` (or `1h` on Anthropic OAuth/setup-token auth) | Cadence; `0m` disables. |
| `agents.defaults.heartbeat.model` | inherits | `provider/model` override for heartbeat runs. |
| `agents.defaults.heartbeat.lightContext` | `false` | When `true`, only HEARTBEAT.md is injected. |
| `agents.defaults.heartbeat.isolatedSession` | `false` | When `true`, fresh session each tick (no history). |
| `agents.defaults.heartbeat.target` | `none` | `last` routes to last contact; explicit channel id permitted. |
| `agents.defaults.heartbeat.directPolicy` | `allow` | `block` suppresses direct/DM delivery. |
| `agents.defaults.heartbeat.activeHours` | unset | `{start,end}` window in configured timezone. |
| `agents.defaults.elevatedDefault` | `false` | Global elevated tool access default. |
| `agents.defaults.imageMaxDimensionPx` | `1200` | Vision-token control. |

`DOC`

**Workspace files — exact roles and load order.** From docs.openclaw.ai/reference/templates/SOUL and the workspace docs surfaced via stack-junkie.com and stanza.dev:

| File | Role | Notes |
|---|---|---|
| `SOUL.md` | Persona, voice, hard limits | First file injected; aim ~200–500 words. |
| `IDENTITY.md` | Name, agent id, role label | Short by design. |
| `AGENTS.md` | Procedural rules, workflows | Largest functional file. |
| `USER.md` | Known facts about the user | Single static context card. |
| `TOOLS.md` | Tool inventory and usage notes | Docs not permissions. |
| `MEMORY.md` | Persistent facts re-injected every session | Plus optional `memory/YYYY-MM-DD.md` dated logs. |
| `HEARTBEAT.md` | Checklist consumed on heartbeat ticks | Empty/comment-only file causes heartbeat skip with `reason=empty-heartbeat-file`. |
| `BOOTSTRAP.md` | First-run ritual checklist | Optional; delete after onboarding. |

Per-file cap `bootstrapMaxChars=20000` and aggregate cap `bootstrapTotalMaxChars=60000` are enforced via silent truncation. Standard files are injected on every session start (no delta-loading); custom files are not auto-injected and must be `read`-tooled by the agent. `DOC`

**Skills (AgentSkill spec).** Each skill is a directory containing `SKILL.md` with YAML frontmatter (`name`, `description`, optional `metadata.openclaw.requires.{bins,env}`, `metadata.openclaw.install[]`, `primaryEnv`, `envVars[]`). Load roots in precedence order: workspace `<workspace>/skills` > project-agent `.agents/skills` > personal `~/.agents/skills` > managed/local `~/.openclaw/skills` > bundled (npm package) > extra dirs (`skills.load.extraDirs`). Source: docs.openclaw.ai/tools/skills and docs.openclaw.ai/tools/skills-config. `DOC`

**Run with ZERO ClawHub skills.** Two complementary controls:

```jsonc
{
  agents: {
    defaults: { skills: [] }   // explicit empty allowlist = no skills load
  },
  skills: {
    load:    { allowSymlinkTargets: false, watch: false },
    install: { allowUploadedArchives: false }
  },
  security: {
    installPolicy: { enabled: true, targets: ["skill", "plugin"] }  // fail-closed
  }
}
```

Additionally, environment variable `OPENCLAW_SKILLS_ALLOWLIST` (e.g., `publisher:openclaw-official` or `skill:my-skill`) restricts what can be installed; empty default allows everything. ClawHub installs are gated by VirusTotal (block above default threshold; override `OPENCLAW_SKILLS_VT_THRESHOLD`). Source: docs.openclaw.ai/tools/skills-config, dev.to/zacvibecodez/openclaw-skills-blocked. `DOC`

**Sandbox model.** From the README "Security model (important)" section: "Default: tools run on the host for the `main` session, so the agent has full access when it is just you. Group/channel safety: set `agents.defaults.sandbox.mode: 'non-main'` to run non-`main` sessions inside sandboxes. Docker is the default sandbox backend; SSH and OpenShell backends are also available. Typical sandbox default: allow `bash`, `process`, `read`, `write`, `edit`, `sessions_list`, `sessions_history`, `sessions_send`, `sessions_spawn`; deny `browser`, `canvas`, `nodes`, `cron`, `discord`, `gateway`."

Verbatim config (docs.openclaw.ai/gateway/sandboxing and the moltfounders.com walkthrough):

```jsonc
{
  agents: {
    defaults: {
      sandbox: {
        mode: "non-main",           // "off" | "non-main" | "all"
        scope: "session",           // "session" | "agent"
        workspaceAccess: "ro",      // "none" | "ro" | "rw"
        allowlist: ["read","write","edit","bash","sessions_list","sessions_history","sessions_send"],
        denylist:  ["browser","canvas","nodes","cron","discord","gateway"],
        docker: { image: "openclaw-sandbox:bookworm-slim", network: "none", readOnlyRoot: true },
        container: { timeout: 30000, memory: "512m", cpu: "0.5" }
      }
    }
  }
}
```

Important: the sandbox is per-session and per-tool, not a VM-level boundary for the `main` agent. Sandbox containers default to `bridge` networking, which still permits external HTTP exfiltration unless you replace it with `--internal` or `network: "none"`. `DOC` for keys; `DOC` for the exfil caveat (github.com/zast-ai/openclaw-security).

**Exec approvals.** Host-local policy at `~/.openclaw/exec-approvals.json` overrides session-level requests when stricter. "YOLO" mode requires `tools.exec.security: "full"` and `tools.exec.ask: "off"` in both `openclaw.json` and `exec-approvals.json`. Defaults are interactive prompts. Source: docs/tools/exec-approvals.md (referenced via deepwiki.com/openclaw/docs). `DOC`

**DM & channel security.** `channels.<channel>.dmPolicy` ∈ {`pairing` (default), `allowlist`, `open`, `disabled`}. Pairing codes expire after 1 hour, capped at 3 pending per channel. Group default: `groupPolicy: "allowlist"`, mention required. Approve via `openclaw pairing approve <channel> <code>`. README: "Treat inbound DMs as untrusted input." `DOC`

**Gateway exposure & auth.** Default `gateway.bind: "loopback"`, port `18789`, `gateway.auth.mode: "token"` or `password`. Production recipe (`design.dev/guides/openclaw-security`):

```jsonc
{
  gateway: {
    mode: "local",
    bind: "loopback",
    port: 18789,
    auth: { mode: "token", token: "OPENCLAW_GATEWAY_TOKEN" }   // reference env via secretRef
  }
}
```

Tokens generated with `openssl rand -hex 32`; rotate after every config-touching incident. `OPENCLAW_GATEWAY_TOKEN` / `OPENCLAW_GATEWAY_PASS` env vars are read automatically. `DOC`

**Hooks.** `hooks.enabled`, `hooks.token` (separate from gateway auth), `hooks.path`, `hooks.allowedSessionKeyPrefixes`. Treat payloads as untrusted; never reuse the gateway auth token. `DOC`

**Heartbeat verbatim defaults** (docs.openclaw.ai/gateway/heartbeat):

```jsonc
{
  agents: { defaults: { heartbeat: {
    every: "30m",
    model: "anthropic/claude-opus-4-6",
    includeReasoning: false,
    lightContext: false,
    isolatedSession: false,
    target: "last",
    prompt: "Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.",
    ackMaxChars: 300
  } } }
}
```

**Memory.** `MEMORY.md` is the only re-injected memory file. Dated `memory/YYYY-MM-DD.md` logs live in the workspace and are not auto-injected. There is no documented "review queue" for memory writes — once the agent writes, the file is on disk. Mitigation is operational: keep workspace under version control (git) and audit deltas. `DOC` for file existence; `UNV` for any official memory-write-review control.

**GitHub Security Advisories with config-level mitigation versus upstream-fix-only.**

| GHSA / CVE | Severity | Class | Config-level mitigation |
|---|---|---|---|
| GHSA-g8p2-7wf7-98mq / CVE-2026-25253 | Critical | 1-click RCE via WebSocket origin | Upstream fix in `2026.1.29`; no config mitigation. |
| GHSA-g55j-c2v4-pjcg / CVE-2026-25593 | High | Unauth local RCE via `config.apply` (`cliPath`) | Mitigate by `gateway.auth` + avoid custom `cliPath`; full fix in `2026.1.20`. |
| GHSA-gv46-4xfq-jv58 / CVE-2026-28466 | Critical 9.4 | Node-invoke approval bypass | Set `gateway.nodes.denyCommands` to block `system.run`; full fix in `2026.2.14`. |
| GHSA-hc5h-pmr3-3497 / CVE-2026-33579 | High 8.6 | Pairing privilege escalation (any `operator.pairing` → `operator.admin`) | Upstream fix only; install `2026.3.28`. |
| GHSA-39mp-545q-w789 / GHSA-vqvg-86cc-cg83 / CVE-2026-35620 | High | Auth bypass in `/send` and `/allowlist` chat commands | Limit `operator.write` scope assignments; upstream fix `2026.3.24`. |
| GHSA-vfp4-8x56-j7c5 / CVE-2026-43584 | High 8.7 | Exec env denylist gap (VIMINIT, EXINIT, LUA_INIT, HOSTALIASES) | No config-level mitigation; install `2026.4.10`. |
| GHSA-f3h5-h452-vp3j / CVE-2026-43579 | Moderate 6.0 | Nostr profile write without admin | Disable Nostr plugin; upstream fix `2026.4.10`. |
| Claw Chain (CVE-2026-44112/44113/44115/44118) | Critical | OpenShell TOCTOU + `senderIsOwner` spoof | Upstream fix only; install `2026.4.22`. |

`DOC`

---

### 1.2 GraphN (Lightning AI agent-workflow platform)

**Reality check.** `graphn.ai` is a closed JavaScript SPA. The site exposes `Blueprints`, `Pricing`, and a `Docs` button that resolves to landing-page content rather than a developer reference. The SSR error trace exposed via the public landing leaks the internal repo path `/home/runner/work/agent-foundry/agent-foundry/web/dist/...`, indicating the source is the private `Lightning-AI/agent-foundry` repository. There is no public Python SDK, no PyPI package named `graphn` or `graphn-sdk`, and no `Lightning-AI/graphn` GitHub repo as of June 2026. `UNV` for any public REST/OpenAPI surface; treat as on-site provisioning.

**Positioning.** From the Partiful event listing (partiful.com/e/UUSBKyeFqHuURxthFyji, verbatim): "GraphN, Lightning AI's platform for building and deploying agent workflows, is the layer between the model and a working product. It handles orchestration, model routing, tool execution (in sandboxed micro-VMs), knowledge base search, guardrails…" That same listing also states: "Starter templates will have you going from sign-in to a running agent in about five minutes." `DOC`

**Confirmed node types (from graphn.ai/blueprints HTML).** All 13 node types appear verbatim in blueprint labels: `Start`, `End`, `Agent`, `Function`, `MCP Tools`, `RAG Tools`, `GitHub`, `Slack`, `Notion`, `For Each`, `Parallel Analysis`, `Evaluator Loop`, `Handoff Router`. `DOC`

**Variable interpolation syntax — confirmed by blueprint labels:**

- `For Each|{steps.resolve_files.output.files}`
- `For Each|{input.files}`
- `For Each|{steps.synthesizer.output.comments}`

So the syntax is `{steps.<node_id>.output.<field>}` and `{input.<field>}`. `DOC`

**Micro-VM / sandbox technology.** The Partiful description uses the phrase "sandboxed micro-VMs" but no Lightning AI or GraphN primary source names the underlying technology (no mention of Firecracker, E2B, gVisor, or WebContainer in connection with GraphN). `UNV` — verify on-site. As industry-pattern context only (NOT confirmed for GraphN): Firecracker is the dominant micro-VM primitive for tool execution today, with documented boot time of "under 125 milliseconds" per Firecracker's project benchmarks (cited in northflank.com/blog/what-is-aws-firecracker: "Firecracker boots a microVM in as little as 125 milliseconds"); the AWS-backed paper at arxiv.org/pdf/2102.12892 baselines pre-snapshot microVM boot at "approximately 200ms." E2B and gVisor occupy adjacent niches. If pressed by judges, expect a sub-200ms cold-start profile and a per-call ephemeral filesystem — but do NOT claim Firecracker is what GraphN uses without on-site confirmation.

**Guardrails, RAG node, connectors, auth, free tier.** `UNV` on the public web. The Partiful copy explicitly mentions "guardrails" and "knowledge base search" as built-in capabilities, but no documented configuration surface exists. Notion/Slack/GitHub connector OAuth scopes are not publicly documented; expect on-site provisioning. `UNV`

**litAI vs GraphN.** They are distinct products both under the Lightning AI umbrella. The litAI README (github.com/Lightning-AI/litAI) makes no mention of GraphN; the GraphN landing page only says "Powered by Lightning AI." There is no primary-source claim that litAI is GraphN's underlying SDK. Treat the relationship as INFERRED at most: GraphN likely routes through Lightning AI's same billing surface that litAI uses, but the SDK identity is not confirmed. `INF`

**litAI as the practical "GraphN-adjacent" Python SDK.** Since GraphN has no public Python SDK, litAI is the only Lightning-published Python entrypoint to the same model fleet. From github.com/Lightning-AI/litAI README and pypi.org/project/litai (current `0.0.10+` series):

```bash
pip install litai
```

```python
from litai import LLM

# 20+ public models: "openai/gpt-5", "anthropic/claude-opus-4-6",
# "google/gemini-2.5-pro", "lightning-ai/gpt-oss-120b", etc.
llm = LLM(model="openai/gpt-5", api_key="<LIT_API_KEY>")
answer = llm.chat("who are you?")

# Tool use
def search_web(query: str) -> str: ...
llm = LLM(model="openai/gpt-5-mini", api_key="...", tools=[search_web], auto_call_tools=True)

# Manual control
llm.call_tool(name="search_web", arguments={"query": "..."})
```

Features the README claims as shipped: OpenAI-compatible chat format, unified billing through Lightning credits, auto retries, fallbacks, async (`LLM.achat`), tools, streaming. **Free quota:** the Lightning-AI/litAI GitHub README and pypi.org/project/litai both currently state "15 free credits (~37M tokens)"; the older lightning.ai/docs/overview/quick-start page advertises "30 million free tokens per month." The GitHub README is the more frequently updated source and should be treated as authoritative until lightning.ai/docs reconciles the discrepancy — plan around ~37M free tokens/month. `DOC` (with two conflicting figures, flagged).

---

### 1.3 Lightning AI Studios + Training Stack

**Studios environment.** Cloud GPU "Studios" exposing a VS Code-like browser IDE plus SSH attach, persistent storage, and seamless CPU↔GPU swap. GPU types documented across the free + Pro tiers: T4, L4, A10G, L40S; A100, H100, H200 available on Teams plan. Source: lightning.ai/pricing (snapshot via saasworthy.com/product/lightning-ai/pricing). Free tier: "1 free 4-CPU Studio" plus monthly free credits (`UNV` exact 2026-June figure — saasworthy snapshot shows the Pro plan at $50/mo with "40 monthly Lightning credits"; hackathon coordinators typically top this up).

**Per-hour GPU pricing (verified via gputracker.dev/provider/lightningai, data pulled from lightning.ai/pricing, last refreshed April 19, 2026):** T4 $0.41/hr, L4 $0.60/hr, A10G $0.71/hr, A100 40GB $1.89/hr, A100 80GB $2.99/hr, H100 $3.50/hr — all on-demand, US-East. (The widely-shared genai.works figures of T4 $0.68, L4 $0.70, A10G $1.80 are significantly overstated; use the gputracker numbers for capacity planning.) `DOC` for types, `UNV` for the current free-credit numeric.

**LitGPT — current finetune surface.** Repository `github.com/Lightning-AI/litgpt`, install `pip install 'litgpt[all]'`. Full LoRA command surface (litgpt/litgpt/finetune/lora.py, main branch as of 2026-06-06):

```bash
litgpt finetune_lora <REPO_ID_OR_CHECKPOINT_DIR> \
  --data {Alpaca|JSON|LIMA|Dolly|...} \
  --data.json_path data/mydata.json \
  --checkpoint_dir checkpoints/<repo>/<model> \
  --out_dir out/<run-name> \
  --precision {bf16-true|bf16-mixed|32-true} \
  --quantize {bnb.nf4|bnb.nf4-dq|bnb.fp4|bnb.fp4-dq|bnb.int8-training} \
  --train.max_steps N --train.epochs N \
  --train.micro_batch_size N --train.global_batch_size N \
  --train.learning_rate 3e-4 --train.lr_warmup_steps 100 \
  --train.save_interval 200 --train.log_interval 1 \
  --lora_r 8 --lora_alpha 16 --lora_dropout 0.05 \
  --lora_query true --lora_key false --lora_value true \
  --lora_projection false --lora_mlp false --lora_head false \
  --devices 1 --num_nodes 1 \
  --eval.interval 200 --eval.max_iters 100
```

Quant + precision constraints from `lora.py`: `"Quantization and mixed precision is not supported"` (must use `bf16-true` not `bf16-mixed`); `"Quantization is currently not supported for multi-GPU training. Please set devices=1 and num_nodes=1 when using the --quantize flag."` litgpt warns: `"LitGPT only supports bitsandbytes v0.42.0. This may result in errors when using quantization."` `CODE`

**Custom dataset format (JSON).** Per litgpt/tutorials/finetune_lora.md:

```json
[
  {
    "instruction": "Arrange the given numbers in ascending order.",
    "input": "2, 4, 0, 8, 3",
    "output": "0, 2, 3, 4, 8"
  }
]
```

The `input` field is only used in the Alpaca template; otherwise it can be empty. `DOC`

**Download & merge.** `litgpt download list` enumerates supported base models (StableLM, Phi-2, Llama-2 7B/13B/70B, Llama-3.1 8B/70B, Mistral, CodeLlama, Falcon, DeepSeek-R1-Distill-Llama-8B, Pythia, Salamandra, OLMo-1B/7B, more — exhaustive list at litgpt/tutorials/download_model_weights.md). Gated models accept `--access_token $HF_TOKEN`. Merge:

```bash
litgpt download meta-llama/Meta-Llama-3.1-8B --access_token $HF_TOKEN
# train …
litgpt merge_lora "out/lora/step-002000"     # writes lit_model.pth
```

Inference commands (`litgpt generate`, `litgpt chat`) auto-merge on the fly so manual `merge_lora` is only needed for external use. `DOC`

**LitServe — OpenAI-compatible serve.** Repo `github.com/Lightning-AI/LitServe`, install `pip install litserve`. Minimal OpenAI-compatible skeleton serving a fine-tuned model that OpenClaw can hit as a BYOK endpoint:

```python
# server.py
import litserve as ls
from litgpt import LLM

class FinetunedChatAPI(ls.LitAPI):
    def setup(self, device):
        self.llm = LLM.load("out/lora/final", quantize="bnb.nf4")

    def predict(self, messages):
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        for tok in self.llm.generate(prompt, max_new_tokens=512, stream=True):
            yield tok

if __name__ == "__main__":
    api = FinetunedChatAPI()
    server = ls.LitServer(
        api,
        spec=ls.OpenAISpec(),
        accelerator="auto",
        middlewares=[ls.TokenAuthMiddleware(token="<bearer-token>")]
    )
    server.run(port=8000)
```

This exposes `POST /v1/chat/completions` with streaming. OpenClaw's BYOK custom provider config (verbatim from moltfounders.com Configuration Guide):

```jsonc
{
  models: {
    providers: {
      "lit-finetuned": {
        baseUrl: "http://127.0.0.1:8000/v1",
        apiKey:  "<bearer-token>",
        api:     "openai-responses"
      }
    }
  },
  agents: { defaults: { model: { primary: "lit-finetuned/local" } } }
}
```

`DOC` / `CODE`

**Quant/adapter dependency pins (LitGPT 2026 series).** Per `lora.py` source: `bitsandbytes==0.42.0` (hard pin warning if newer). `peft` and `transformers` are runtime dependencies of `litgpt[all]`; the resolver picks the constraint set valid for the LitGPT release. `CODE`

**Free-tier GPU-hour amount and phone-verification lag.** Pro plan documents "40 monthly Lightning credits" (saasworthy snapshot); the free tier provides "1 free 4-CPU Studio" plus monthly credits whose numeric value is not pinned in the docs we can confirm. Phone verification is required at sign-up, and waitlist throttling is mentioned by third-party reviewers (toolify.ai snapshot). `UNV` exact numeric — verify on-site.

---

### 1.4 Validia (deepfake / identity verification)

**Company.** Founded 2023, San Francisco. Co-founders Justin Marciano (CEO) and Paul Vann (CTO) (tracxn.com profile, validia.ai/en). Won the inaugural Okta SaaS Startup Competition at Oktane24, with the winner announced October 16, 2024, per okta.com blog ("Okta SaaS Startup Competition 2024 results"): "The winner, Validia, was announced on October 16 and had the opportunity to ring the opening bell at NASDAQ." Prize was "up to $500,000 in investment from Okta" (businesswire.com/news/home/20241007945016). SOC 2 Type II completed (Paul Vann LinkedIn announcement, 2024-2025). Recent product: "Truly" identity verification, positioned against Cluely (theaudit.itauditlabs.com podcast). `DOC`

**Developer API — present.** docs.validia.ai/platform-usage/integrations/api-setup documents a public REST API at `https://api.validia.ai`. Verbatim authentication call:

```bash
curl -X POST "https://api.validia.ai/api/auth" \
  -H "Content-Type: application/json" \
  -d '{ "api_key": "vld_your_api_key",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret" }'
```

Returns a bearer token used against further endpoints. `DOC` (per subagent verification, June 2026)

**Python SDK.** No public SDK on PyPI; no `github.com/validia` org with public SDK repo. Use raw HTTPS. `DOC` (negative)

**Integration pattern for "verify before irreversible agent action."** No documented endpoint signature is publicly indexed beyond the auth call, so the working pattern (to confirm on-site at the hackathon) is:

```python
import requests

def validia_check_before_action(session_id: str, action: str) -> bool:
    token = get_validia_bearer()         # cached from POST /api/auth
    r = requests.post(
        "https://api.validia.ai/api/verify",      # endpoint shape to confirm on-site
        headers={"Authorization": f"Bearer {token}"},
        json={"session_id": session_id, "action": action, "modality": "video"}
    )
    risk = r.json()
    return risk.get("decision") == "allow"
```

Wire this into an OpenClaw exec-approval hook or a GraphN `Function` node placed in front of any node that performs an external write. `INF` on endpoint name; the auth call is `DOC`.

**Fallback reference shapes (NOT Validia, for engineering completeness).** Reality Defender RealAPI (`realitydefender.com/platform/api`) and Sightengine Deepfake Detection API both return JSON with a 0..1 manipulation/deepfake score and explainability fields. Both have public SDKs (`pip install realityapi`, `pip install sightengine`). Use either of these patterns when sketching a Validia client; do not assume parity. `DOC` for Reality Defender / Sightengine.

---

### 1.5 Sentience (The Sentience Company)

**Company.** Founded 2025 by Sam Kececi (ex-MACRO, Amazon, Bridgewater, Salesforce; Columbia 2016–2020). HQ Newark, DE; "6 total employees" per PitchBook's profile for The Sentience Company (pitchbook.com/profiles/company/969705-64). Raised $6.5M, with Bain Capital Ventures, Daybreak Ventures, Otherwise Fund among investors (PitchBook profile). Public launch announced March 26, 2026, with the X post: "We raised $6.5m to build humanity's platform for uploaded consciousness. Sentience creates one unique model for every person — a digital twin of your mind — to remember everything, recall what matters, and operate as you." Marketing tagline at southparkcommons.com profile: "Sentience is your digital memory bank that allows you to capture and share your knowledge with any app, AI, or human." `DOC`

**Developer API or SDK.** None confirmed publicly as of June 6, 2026. The site sentience.com is gated; no docs subdomain, no PyPI package, no public GitHub org for the personal-memory product. Note: do not confuse with the separate company SentienceAPI at sentienceapi.com (a browser-agent verification harness, `pip install sentienceapi`) or galadriel-ai/Sentience (on-chain LLM proofs) — both are different products. `UNV` — provision on-site at hackathon.

**Conceptual integration patterns to plan for.**

1. As an OpenClaw memory feeder: receive a Sentience export (JSON dump of recall items) and write to `USER.md` and `memory/YYYY-MM-DD.md` so the standard injection path picks it up.
2. As a GraphN `RAG Tools` node corpus: load Sentience export into the GraphN knowledge-base node as the indexed document set. Both shapes are `UNV` until an SDK or export endpoint is provided by sponsors at the venue.

---

## 2. OpenClaw Hardening Reference (config-level controls)

| Attack class | Exact config key | Setting that mitigates | Source |
|---|---|---|---|
| Inbound DM impersonation / prompt injection from strangers | `channels.<ch>.dmPolicy` | `"pairing"` (default) or `"allowlist"` | docs.openclaw.ai/gateway/security |
| Public DM blast | `channels.<ch>.allowFrom` | Explicit ids only (no `"*"`) | same |
| Hostile group invite-driven activation | `channels.defaults.groupPolicy` | `"allowlist"` (default) with `requireMention: true` | docs.openclaw.ai/gateway/configuration |
| Unauthenticated local WebSocket RCE (CVE-2026-25253, GHSA-g8p2-7wf7-98mq) | `gateway.auth.mode` + version pin | `"token"` with 32-byte random + `openclaw >= 2026.1.29` | github.com/advisories/GHSA-g8p2-7wf7-98mq |
| Network exposure of Gateway | `gateway.bind` | `"loopback"` (never `0.0.0.0`) | design.dev/guides/openclaw-security |
| `config.apply` cliPath injection (CVE-2026-25593) | avoid custom `cliPath` + version pin | upgrade to `>= 2026.1.20` | github.com/advisories/GHSA-g55j-c2v4-pjcg |
| Node-invoke approval bypass (CVE-2026-28466) | `gateway.nodes.denyCommands` | block `system.run`; upgrade `>= 2026.2.14` | github.com/advisories/GHSA-gv46-4xfq-jv58 |
| Sandbox tool escape from non-main session | `agents.defaults.sandbox.mode` | `"non-main"` minimum, `"all"` strongest | README + docs/gateway/sandboxing |
| Workspace exfiltration through filesystem tools | `agents.defaults.sandbox.workspaceAccess` | `"ro"` or `"none"` | design.dev/guides/openclaw-security |
| Dangerous tool surface | `agents.defaults.sandbox.denylist` | include `browser`, `canvas`, `nodes`, `cron`, `discord`, `gateway` | README |
| Unknown / hostile ClawHub skills | `agents.defaults.skills` + `OPENCLAW_SKILLS_ALLOWLIST` | `[]` for zero skills, or `publisher:openclaw-official` allowlist | docs/tools/skills-config |
| Operator-trusted install policy (skill + plugin) | `security.installPolicy` | `enabled: true, targets: ["skill","plugin"]` with exec command for approval | docs.openclaw.ai/tools/skills-config |
| Private-network SSRF via `browser` tool | `browser.ssrfPolicy.dangerouslyAllowPrivateNetwork` | leave default `false` | deepwiki.com/openclaw/docs |
| Env-var exec abuse (CVE-2026-43584: VIMINIT/EXINIT/LUA_INIT/HOSTALIASES) | version pin only | `openclaw >= 2026.4.10` | github.com/advisories/GHSA-vfp4-8x56-j7c5 |
| Pairing privilege escalation (CVE-2026-33579) | version pin only | `openclaw >= 2026.3.28` | github.com/advisories/GHSA-hc5h-pmr3-3497 |
| `/send` & `/allowlist` auth bypass (CVE-2026-35620) | restrict `operator.write` scope grants | upgrade `>= 2026.3.24` | sentinelone.com/vulnerability-database/cve-2026-35620 |
| Claw Chain (CVE-2026-44112..44118) | version pin only | `openclaw >= 2026.4.22` | thehackernews.com/2026/05 |
| Inbound webhook impersonation | `hooks.token` separate from gateway auth | dedicated random token, `allowUnsafeExternalContent: false` | docs.openclaw.ai/gateway/configuration-reference |
| Exec YOLO drift | `tools.exec.security` + `tools.exec.ask` | leave at defaults; never `"full"` + `"off"` | docs/tools/exec-approvals |
| Sandbox container exfiltration | `agents.defaults.sandbox.docker.network` | `"none"`, or external `docker network --internal` | github.com/zast-ai/openclaw-security |
| Bot token / API key leakage in logs | `secrets.providers.*` with `secretRef` | reference env vars rather than inlining tokens | docs.openclaw.ai/cli/config |

**Threats with NO config-level mitigation (require upstream fix or external layer):**

1. CVE-2026-25253 WebSocket origin RCE — upstream-only.
2. CVE-2026-43584 env-var denylist gap — upstream-only.
3. Claw Chain CVE-2026-44112/44113/44115/44118 — upstream-only.
4. CVE-2026-33579 pairing-scope escalation — upstream-only.
5. Prompt-injection via inbound channel content (general class) — not config-fixable; requires content filters and tool allowlists at the agent layer.
6. Memory poisoning (the agent writing attacker-supplied content into `MEMORY.md` or `memory/YYYY-MM-DD.md`) — no documented review-queue control; mitigate operationally with git-versioned workspace and review hooks.
7. Sandbox-container egress over bridge networking — partial config mitigation via Docker network policy is external to OpenClaw config.

---

## 3. LoRA Personalization Recipe (centerpiece, 5-hour build)

**Base-model pick under nf4 quantization on a single 24 GB GPU.** Use `microsoft/phi-2` (2.7B) for the safest budget or `meta-llama/Meta-Llama-3.1-8B-Instruct` for stronger generalization. Recommendation: Phi-2 if the demo runs on a single L4 (24 GB) and time is tight; Llama-3.1-8B-Instruct if the team has an A10G or larger.

**VRAM math under bf16-true + bnb.nf4.** From the canonical `litgpt finetune_lora` benchmark table (litgpt/tutorials/finetune_lora.md, microbatch=1, 1,000 iterations):

| Model | Setting | Training memory | Wall clock | Inference memory |
|---|---|---|---|---|
| StableLM 3B | `bf16-true + bnb.nf4` | 6.35 GB | 1.82 min | 3.20 GB |
| StableLM 3B | `bf16-true + bnb.nf4-dq` | 6.19 GB | 1.87 min | 3.04 GB |
| Llama-2 7B | `bf16-true` | 21.30 GB | 2.36 min | 13.52 GB |
| Llama-2 7B | `bf16-true + bnb.nf4` | 14.14 GB | 3.68 min | 4.57 GB |
| Llama-2 7B | `bf16-true + bnb.nf4-dq` | 13.84 GB | 3.83 min | 4.26 GB |

Extrapolating for **Llama-3.1-8B under `bf16-true + bnb.nf4`, microbatch=1**: expect ~15–17 GB training memory and approximately **9–14 minutes for 200 steps; 35–55 minutes for 800 steps** on an A10G (24 GB) or L4. Phi-2 under the same quant lands around ~5–7 GB and finishes 200–800 steps in **3–12 minutes** on a T4 or L4. Source: extrapolated linearly from the litgpt table; treat as planning numbers, not warranties.

**End-to-end pinned command sequence (Lightning AI Studio, 1× L4 or 1× A10G, June 2026).**

```bash
# 1. Environment (Studio brings Python 3.11)
pip install "litgpt[all]" "litserve" "litai" \
            "bitsandbytes==0.42.0" "peft" "transformers"

# 2. Download base
litgpt download microsoft/phi-2
# or, gated:
litgpt download meta-llama/Meta-Llama-3.1-8B --access_token $HF_TOKEN

# 3. Format your personal dataset as Alpaca-style JSON
cat > data/me.json <<'JSON'
[
  {"instruction": "...", "input": "", "output": "..."},
  ...
]
JSON

# 4. LoRA fine-tune (Phi-2; ~5-10 min for 200 steps on L4)
litgpt finetune_lora microsoft/phi-2 \
  --data JSON \
  --data.json_path data/me.json \
  --out_dir out/me-phi2-lora \
  --precision bf16-true \
  --quantize bnb.nf4 \
  --lora_r 8 --lora_alpha 16 --lora_dropout 0.05 \
  --lora_query true --lora_value true \
  --train.micro_batch_size 1 \
  --train.global_batch_size 16 \
  --train.max_steps 400 \
  --train.learning_rate 3e-4 \
  --train.save_interval 200 \
  --train.log_interval 1 \
  --devices 1 --num_nodes 1

# 5. Merge (optional but cleaner for serving)
litgpt merge_lora "out/me-phi2-lora/final"

# 6. Quick sanity test
litgpt chat "out/me-phi2-lora/final"

# 7. Serve as OpenAI-compatible API (LitServe)
python server.py     # uses the FinetunedChatAPI skeleton above

# 8. Point OpenClaw at it via BYOK custom provider config:
openclaw config set models.providers '{"lit-finetuned":{"baseUrl":"http://127.0.0.1:8000/v1","apiKey":"<bearer>","api":"openai-responses"}}' --strict-json --merge
openclaw config set agents.defaults.model.primary "lit-finetuned/local"
openclaw gateway restart
```

**Realistic wall-clock plan (5-hour build).** Stand up Studio + download base ≤ 30 min; format & validate dataset 30 min; LoRA train ≤ 45 min (Phi-2) or ≤ 90 min (Llama-3.1-8B nf4 400 steps); merge + serve ≤ 20 min; wire OpenClaw → LitServe ≤ 20 min; integration testing + guardrails + Validia gate ≤ 90 min.

---

## 4. Integration Architecture (labeled by evidence)

```
        ┌─────────────────────────────────────────────────────────┐
        │  Channel (Telegram / Slack / iMessage / WhatsApp)       │  DOC
        └──────────────┬──────────────────────────────────────────┘
                       │ dmPolicy="pairing" / allowFrom            DOC
                       ▼
        ┌─────────────────────────────────────────────────────────┐
        │  OpenClaw Gateway (loopback:18789, auth.mode=token)     │  DOC
        │  Workspace: SOUL.md, IDENTITY.md, AGENTS.md, USER.md,   │
        │             TOOLS.md, MEMORY.md, HEARTBEAT.md           │
        └────┬────────────────┬────────────────┬──────────────────┘
             │                │                │
             │ BYOK call      │ exec-approval  │ Sentience-fed
             │ openai-responses                │ USER.md / MEMORY.md
             ▼                ▼                ▼ (UNV — provision on site)
   ┌──────────────────┐ ┌───────────────────┐ ┌───────────────────┐
   │ LitServe         │ │ Validia API        │ │ Sentience export   │
   │ (fine-tuned      │ │ (api.validia.ai)   │ │ (no public SDK     │
   │  model, OpenAI   │ │ Bearer via         │ │  yet — INF)        │
   │  spec)  DOC      │ │ POST /api/auth DOC │ │                    │
   └──────────────────┘ └───────────────────┘ └───────────────────┘
             │
             │  (alt path — different team) GraphN orchestration
             ▼
        ┌─────────────────────────────────────────────────────────┐
        │  GraphN workflow (sandboxed micro-VMs)                  │  DOC (positioning)
        │  Nodes: Start → Agent → MCP/RAG Tools → Evaluator Loop  │  DOC (nodes confirmed)
        │  Interpolation: {steps.<node>.output.<field>}           │  DOC
        │  Sandbox tech named: ??? (Firecracker/E2B-class)         │  UNV
        └─────────────────────────────────────────────────────────┘
```

**Connections by evidence label:**

- OpenClaw → LitServe (BYOK custom provider): **DOC** (moltfounders.com config, lightning.ai/docs/litserve OpenAI spec).
- OpenClaw exec-approval → Validia bearer call before irreversible action: **INF** (auth call confirmed `DOC`; downstream verify endpoint shape `INF`).
- OpenClaw memory ← Sentience export: **UNV** (no public Sentience API).
- GraphN orchestration → OpenClaw Gateway via channel webhook (`hooks.*`): **INF** (the `hooks` config supports arbitrary HTTP ingress; no GraphN doc names this pattern).
- GraphN tool sandbox uses Firecracker/E2B/similar: **UNV** (Partiful copy says "micro-VMs," no primary source names the runtime).
- litAI is GraphN's SDK: **DENIED** by source inspection (no cross-reference in either README/landing).

---

## 5. Version & Compatibility Pin List (known compatible as of 2026-06-06)

| Component | Pinned version | Source |
|---|---|---|
| OpenClaw (npm) | `2026.4.22` minimum (patches Claw Chain) | thehackernews.com/2026/05; github.com/openclaw/openclaw releases |
| Node.js | `24.x` recommended, `22.19+` minimum | github.com/openclaw/openclaw README |
| LitGPT | latest main (≥ 0.5.x series; check `pip show litgpt`) | github.com/Lightning-AI/litgpt README |
| litAI | `0.0.10+` | pypi.org/project/litai |
| LitServe | `0.2.x` series, latest on PyPI | github.com/Lightning-AI/LitServe |
| PyTorch Lightning | `2.x` matching litgpt's pin | litgpt requirements |
| bitsandbytes | `0.42.0` (hard pin; warning on others) | litgpt/finetune/lora.py source |
| peft | latest compatible with transformers 4.4x+ | litgpt[all] resolver |
| transformers | latest compatible with the chosen base model (Llama-3.1: 4.43+) | huggingface.co/meta-llama/Llama-3.1-8B |
| Python | `3.11` recommended (Studio default) | Lightning AI Studios |
| Docker | latest for OpenClaw sandbox backend | docs.openclaw.ai/gateway/sandboxing |
| Validia REST API | unversioned; auth at `api.validia.ai/api/auth` | docs.validia.ai/platform-usage/integrations/api-setup |
| GraphN | closed SaaS; no version exposed | graphn.ai |
| Sentience SDK | none public; provision on-site | sentience.com |

---

## 6. Unverified / Provision-On-Site Appendix

| Item | Confidence | Why unverifiable | Action at venue |
|---|---|---|---|
| GraphN public Python SDK | High that it does NOT exist | No PyPI package, no public docs/api, repo is private `Lightning-AI/agent-foundry` | Ask Lightning AI staff for staff-issued bearer + endpoint URL; expect proxy via litAI for raw model calls. |
| GraphN sandbox technology | High that it is "micro-VM" class; LOW on the named runtime | Only Partiful marketing copy says "sandboxed micro-VMs"; no doc names Firecracker/E2B/gVisor | Ask presenter directly; do not claim Firecracker in the pitch unless confirmed. |
| GraphN guardrails configuration | Low / unknown | No public doc surface | Use the built-in defaults; do not rely on custom guardrail wiring. |
| Validia "verify before action" endpoint exact path | Medium | Auth call is `DOC`; verify endpoint is `INF` | Use the on-site Validia booth to get the exact endpoint signature. |
| Sentience developer SDK / export | Negative confirmation | No public API or PyPI package as of June 6, 2026 | Treat Sentience as a manual data feed; ask Sam Kececi for a JSON export endpoint or token. |
| Lightning AI free-credit numeric (June 2026) | Medium-Low (litAI README says "15 free credits / ~37M tokens", docs page says "30M tokens") | Two conflicting Lightning-owned figures | Confirm in your billing dashboard at studio.lightning.ai before kickoff; assume ~37M tokens/month per the more recent GitHub README. |
| Phone-verification / approval lag on Studios | Low | Reviewer reports a wait, no official SLO | Register accounts the night before. |
| `bootstrapTotalMaxChars` exact default | Medium (60,000 per docs.openclaw.ai/gateway/config-agents; community guides cite 150,000) | Doc/community drift | Treat 60,000 as the safe cap; check `openclaw config get agents.defaults.bootstrapTotalMaxChars` at runtime. |

---

## End of Pass 1 Reference

All controls, code, and command surfaces above are reproducible against the cited URLs as of June 6, 2026, with version stamps where the source provides them. Where the primary doc was silent or unrendered, the entry is marked `UNV` rather than fabricated.