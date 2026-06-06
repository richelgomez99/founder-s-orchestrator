# Agents Hackathon (NYTechWeek, June 6 2026) — Tool & Sponsor Research Dossier

## TL;DR
- **The hackathon's "hardest to break" tiebreaker collides head-on with the documented reality of OpenClaw**, which has 1,184+ confirmed malicious skills in its ClawHub registry (the ClawHavoc campaign), 60+ CVEs and 60+ GHSAs on the core repo (per blog.cyberdesserts.com citing the SecurityScorecard STRIKE Team, Endor Labs, BitNinja, and ARMO; jgamblin/OpenClawCVEs lists 156 total advisories with 128 awaiting CVE assignment as of late March 2026), and well-documented prompt-injection-to-RCE paths — meaning the winning move is to deeply harden an OpenClaw agent (or wrap it in GraphN's sandboxed micro-VMs) rather than just build a flashy capability demo.
- **The highest-leverage differentiator is to actually fine-tune a LoRA personalization adapter using Lightning AI Studios + LitGPT during the build window** — feasible for a 3B–7B model in 30–90 minutes on a single L4/A10G, which uses the sponsor's flagship capability the way the sponsor intends and almost no other team will attempt.
- **Sentience (the third co-sponsor) is The Sentience Company by Sam Kececi** — a personal-AI "digital memory" platform ($6.5M seed led by Bain Capital Ventures, public launch March 26 2026) that builds a per-person model from your emails/Slack/Notes; Validia is the deepfake/identity-verification co-host (founded by Paul Vann + Justin Marciano, SOC 2 Type II, Oktane 2024 winner). The three sponsors map cleanly to the dual theme: Lightning/OpenClaw = personalization infrastructure, Validia = identity/anti-impersonation, Sentience = personal-memory/personalization data layer.

---

## Key Findings

1. **OpenClaw is the most-targeted attack surface in 2026 agent security research.** Multiple arXiv papers (2603.27517, 2603.11619, 2603.12644, 2603.19974) and a wave of industry reports (Snyk ToxicSkills, Koi Security, Bitdefender, Antiy CERT, Silverfort, HKCERT) document concrete attack classes specifically against OpenClaw: skill poisoning, prompt-injection-to-RCE, container/sandbox escape (GHSA-w235-x559-36mg, GHSA-h9g4-589h-68xv), display-name allowlist bypass on Telegram/Nextcloud (GHSA-r5h9, GHSA-mj5r), and self-modification of bootstrap files. Judges will recognize these by name.

2. **The OpenClaw workspace is the highest-leverage personalization AND attack surface.** Seven `.md` files (`AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`, `MEMORY.md`, `HEARTBEAT.md`, plus optional `BOOTSTRAP.md`) get **injected into the system prompt every turn** with truncation limits of `bootstrapMaxChars: 20000` and `bootstrapTotalMaxChars: 60000`. Hardening these files (and their write permissions) directly maps to the scoring rubric.

3. **GraphN is real but its developer-facing documentation is not publicly indexable.** The site is a JS-only SPA where `/docs` and `/pricing` SSR to the landing page. What IS verifiable: 72 blueprints across 12 categories, a visual graph builder with named node types (Agent, Function, MCP Tools, RAG Tools, For Each, Parallel Analysis, Evaluator Loop, Handoff Router), built-in Notion/Slack/GitHub connectors, and `litAI` (Python LLM router with `LIT_API_KEY` auth) as the very likely underlying SDK. The microVM technology is *unspecified by name* in any primary source — the hackathon copy only says "sandboxed micro-VMs."

4. **Lightning AI Studios can plausibly fine-tune a LoRA in the hackathon window.** LitGPT's documentation explicitly demonstrates fine-tuning StableLM-3B or Phi-2 on Alpaca-style data on a single 24 GB GPU; the `0_to_litgpt.md` tutorial shows 5 training steps completing in "about a minute" on a GPU. A 1–3 epoch LoRA on a few-hundred-row user-style dataset is ~30–60 min wall-clock on an L4/A10G via `litgpt finetune_lora`. New Lightning accounts get free GPU credits (commonly cited at ~7 hours via phone verification — verify on day-of).

5. **Validia is the impersonation-defense layer.** Paul Vann (CTO/co-founder) and Justin Marciano (CEO/co-founder) run an SF-based identity-verification platform that detects deepfake video/audio in real time on Zoom/Teams and (per Crunchbase) emphasizes "Know Your Employee" workflows. Public developer-API docs were not located; teams should expect to integrate via demo/sandbox API provided by Validia on-site.

6. **Sentience is the personalization-data sponsor.** Founder Sam Kececi (ex-Macro CTO, ex-Amazon); $6.5M seed led by Bain Capital Ventures with South Park Commons, Daybreak Ventures, Terrance Rohan, Soleio, Annie Case. Public launch March 26 2026. The product captures desktop/mobile/Slack/Apple Notes/email and builds a personalized model that "thinks, remembers, and acts like you." Likely judge framing: "Did your agent meaningfully personalize, or is it a glorified config file?"

7. **Confirmed judges & prizes (from Paul Vann/Validia LinkedIn announcements):** Brian Campbell (Lightning AI, enterprise sales/partnerships); Suchit Agarwal (Okta, security products); Joyjit Daw (NVIDIA, inference). **Prizes include $1K in Lightning AI credits and an NVIDIA Jetson Nano Developer Kit.** Event runs **9:30 AM – 6:30 PM Saturday June 6 2026 at The Bench (49 Elizabeth St, NYC)**; ~200+ developers expected.

---

## Details — Per-Tool Dossiers

### 1. OpenClaw — personalized agent framework

**What it is.** An MIT-licensed open-source local-first personal AI assistant. The official repo is `github.com/openclaw/openclaw`. By early April 2026 it had accumulated 346,000 GitHub stars (per dev.to, SecurityWeek, and skywork.ai citing The New Stack — "the fastest-growing open source project in GitHub history"). Originally called Clawdbot, renamed Moltbot in January 2026 due to a trademark dispute, rebranded to OpenClaw on January 29 2026. Docs at `docs.openclaw.ai`.

**Architecture (verified from docs.openclaw.ai and arXiv 2603.27517).** Seven interacting components: Channel System, central Gateway, Plug-ins & Skills System, Agent Runtime, Memory & Knowledge System, LLM Provider, Local Execution. Runs on Node 22.19+/24.

**Workspace files (the personalization layer).** Plain Markdown, default at `~/.openclaw/workspace`:
- `AGENTS.md` — operational rules / SOP; "what do you do and how" (8k char budget)
- `SOUL.md` — personality, tone, boundaries; loaded first into context every session (3k chars)
- `IDENTITY.md` — short public-facing identity card (name, vibe, emoji; 200 chars)
- `USER.md` — user info and preferences (1.5k chars)
- `TOOLS.md` — environment notes for skills (2k chars)
- `MEMORY.md` — curated long-term memory (4k chars)
- `HEARTBEAT.md` — periodic-task checklist (500 chars)
- `memory/YYYY-MM-DD.md` — daily memory log
- `BOOTSTRAP.md` — first-run onboarding ritual (delete after)

Injection limits configurable via `agents.defaults.bootstrapMaxChars` (default 20,000) and `agents.defaults.bootstrapTotalMaxChars` (default 60,000). Injection cadence configurable: `"always"`, `"continuation-skip"`, or `"never"`.

**Core developer surface.** `npm install -g openclaw@latest` then `openclaw onboard --install-daemon`. CLI subcommands include `openclaw setup`, `openclaw gateway start`, `openclaw doctor`, `openclaw message send`, `openclaw agent --message ...`, `openclaw browser`. Configuration in `~/.openclaw/openclaw.json`. Lightning AI also offers a one-click "Clawdbot in the cloud, zero setup" Studio template (`lightning.ai/lightning-ai/templates/clawdbot-in-the-cloud-zero-setup-openclaw`) — no local Mac mini needed.

**Key features.**
- **Heartbeat (proactive loop)** — scheduled polling cycle in which the agent autonomously wakes, reads memory and inbox, and acts without human prompting. Configurable via `openclaw.json` (`heartbeat.every: "1h"`, optional cheaper `heartbeat.model`).
- **AgentSkill system + ClawHub registry** — skills are SKILL.md + supporting files; installable from `clawhub.ai`; treated as **untrusted code by design** (per official docs).
- **Channels** — WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, IRC, Microsoft Teams, Matrix, Feishu, LINE, Mattermost, Nextcloud Talk, Nostr, Synology Chat, Tlon, Twitch, Zalo, Zalo Personal, WeChat, QQ, WebChat (23+).
- **Voice Wake / Talk Mode** — wake words on macOS/iOS + continuous Android voice with ElevenLabs + system TTS fallback.
- **Live Canvas** — agent-driven visual workspace via A2UI.
- **First-class tools** — browser, canvas, nodes, cron, sessions, plus Discord/Slack actions.
- **Sandbox toggle** — `agents.defaults.sandbox` directs tool writes to `~/.openclaw/sandboxes` instead of the host workspace. **Off by default** — the workspace is the default cwd but is NOT a hard sandbox; absolute paths reach the host.

**Authentication / setup complexity.** Local-first; you bring your own LLM API keys (Anthropic/OpenAI/Gemini/DeepSeek/Mistral via BYOK). Channel pairing (e.g. Telegram bot token, WhatsApp QR) adds 5–15 min. On the Lightning Studio template, setup completes in the browser; locally on a Mac mini the README path is ~30–60 minutes including channel pairing.

**Time-to-first-running-agent estimate.** ~5 minutes via Lightning AI's one-click OpenClaw Studio template; ~30–60 min from a clean local install with one channel paired.

**Personalization angle.**
- The 7 markdown files are version-controllable (git) and are the literal substrate of "how the agent learns to work like you."
- MEMORY.md + dated `memory/YYYY-MM-DD.md` provide longitudinal memory that compounds.
- USER.md captures preferences, contacts, and decisions across conversations.
- Heartbeat lets the agent proactively observe and update memory.
- Multi-agent persona resolution (cascade: global config → per-agent → workspace file → default) supports per-user, per-team personas.

**Security weaknesses (the central differentiator).** This is the most documented agent attack surface of 2026:

| Class | Mechanism | Primary source |
|---|---|---|
| **Skill poisoning / ClawHavoc** | Koi Security researcher Oren Yomtov audited all 2,857 ClawHub skills on February 1, 2026 and found 341 malicious entries — exactly 11.9% of the registry at that moment ("341 malicious skills – 335 of them from what appears to be a single campaign," The Hacker News). Bitdefender's independent scan placed the figure higher at ~900 malicious packages (~20%). Antiy CERT classified the malware as `Trojan/OpenClaw.PolySkill`; Atomic Stealer payloads were delivered via fake error-message social engineering. | Snyk ToxicSkills 2026, Bitdefender, Koi Security, eSecurityPlanet, Silverfort. |
| **Prompt-injection → RCE** | Skills + shell tool = LLM can be tricked into executing arbitrary host commands. | Giskard, arXiv 2603.12644. |
| **Indirect prompt injection** | External content (emails, scraped web pages, Slack messages) competes with user instructions for control. | arXiv 2603.11619. |
| **Memory poisoning / temporal composition** | Benign-looking inputs accumulate across days to trigger latent malicious behaviors stored in MEMORY.md. | arXiv 2603.11619. |
| **Agent self-modification** | Agent can rewrite SOUL.md / AGENTS.md / MEMORY.md, drifting its own guardrails. | arXiv 2603.19974 "Trojan's Whisper." |
| **Sandbox/container escape** | GHSA-w235-x559-36mg (Docker bind-mount + net-config injection), GHSA-h9g4-589h-68xv (unauthenticated noVNC desktop). | GitHub Security Advisories on `openclaw/openclaw`. |
| **Channel-identity spoofing** | Telegram/Nextcloud display-name allowlist bypass via mutable `actor.name` (GHSA-r5h9, GHSA-mj5r). | GitHub Security Advisories. |
| **Control UI** | Tokens in query strings; HTTP-without-device-check exposure. | Giskard. |
| **Exposed instances** | SecurityScorecard's STRIKE threat-intelligence team identified **more than 135,000 internet-facing OpenClaw instances across 82 countries in February 2026** (per Bitdefender, SecurityWeek, CyberDesserts); Censys independently confirmed **63,070 live instances in late March 2026** via application-layer fingerprinting — a ~53% reduction reflecting operator remediation but no architectural fix. | SecurityScorecard STRIKE, Censys, Bitdefender, SecurityWeek. |
| **Fake installers / typosquats** | VS Code marketplace ext impersonating Moltbot dropping payloads. | TechRadar, PointGuard AI. |

**Most demonstrable in a 3-minute live demo:** (a) live blocking of an indirect prompt-injection in a retrieved doc; (b) live skill-install gate (à la ClawNet from Silverfort) that scans SKILL.md and rejects; (c) memory-poisoning red-team that fails because MEMORY.md is write-gated.

**Fastest path from install to running personalized agent:** Lightning AI OpenClaw Studio template + Telegram channel + edit USER.md/SOUL.md — ~5 minutes.

**Highest-leverage configuration surface to harden:** (1) `agents.defaults.sandbox: true` plus restricted `workspaceAccess`; (2) write-only-via-tool gating on SOUL/AGENTS/MEMORY (`skipBootstrap` / `skipOptionalBootstrapFiles` and read-only mounts); (3) per-channel allowlists and a stricter `bootstrapTotalMaxChars`; (4) replace ClawHub-installed skills with a small allowlisted pinned set; (5) keep heartbeats on cheap haiku-class models with explicit task allowlists.

---

### 2. GraphN — Lightning AI's agent-workflow platform

**What it is (verified).** A Lightning-AI-branded platform at `graphn.ai` whose tagline rotates ("Stop buying tokens. Start shipping voice agents / legal intake") with sub-headline "**Production-ready AI workflows that replace token spend with defined outcomes — inside your security boundary. Powered by Lightning AI.**" The site is a JS SPA; `/docs` and `/pricing` did not render publicly. SSR build path leaks reveal the internal repo name is likely `agent-foundry`.

**Core product surface.** A **visual graph builder** (verified from `/blueprints`) with node types: `Agent`, `Function`, `MCP Tools`, `RAG Tools`, `GitHub`, `Slack`, `Notion`, `For Each`, `Parallel Analysis`, `Evaluator Loop`, `Handoff Router`, `Start`, `End`. Variable interpolation uses `{steps.<name>.output.<field>}` and `{input.<field>}`. Whether a Python SDK or REST API is also exposed is **unverified** in primary sources.

**Likely underlying SDK.** The Lightning-AI `litAI` Python package (`pip install litai`, MIT) is a unified LLM router authenticating via `LIT_API_KEY` with billing through Lightning AI credits. This is almost certainly the model-router layer beneath GraphN's visual UX (inferred — not confirmed).

**Advertised capabilities (from hackathon copy):** orchestration, model routing, tool execution in sandboxed micro-VMs, knowledge-base search, guardrails, managed compute.

**Blueprints (verified — 72 across 12 categories).**
- **Search & Knowledge (6):** Deep Research Assistant, Company Knowledge Search, Multi-Source Research Assistant, Meeting Knowledge Base, Competitive Intelligence Tracker, FAQ Bot Builder.
- **Content & Writing (9):** Blog/Social/PR/Product/Newsletter writers, Document Translator, AI Video Generator (Veo 3.1 + Nano Banana), AI Image Generator (Qwen Image), Avatar Video Producer (Veo 3.1).
- **Support (5):** Support Router, Ticket Tagger & Prioritizer, Escalation Detector, Support Knowledge Bot, Multi-Language Support Router.
- **Sales & Marketing (5–6):** Cold Outreach Writer, Lead Scorer, Battlecard Generator, Campaign Performance Analyst, RFP Response Drafter.
- **Finance (5):** Investment Due Diligence, Expense Report Auditor, Financial Narrative Writer, Regulatory Change Monitor, Invoice Data Extractor & Matcher.
- **Engineering (8):** Automated PR Review Bot, API Data Summarizer, Production Incident Response, Architecture Decision Record Writer, Vulnerability Scanner, Release Notes Generator, API Docs Generator, Speech Roundtrip.
- **Data & Analytics (6):** Natural Language SQL, Data Quality Health Check, Dashboard Narrative Writer, CSV Analyzer, Anomaly Detector, Video Analysis (Qwen3.5 VL).
- **HR & People (5):** Resume Screener, Onboarding Planner, Policy Q&A Bot, Performance Review Drafter, Job Description Writer.
- **Legal & Risk (7):** Contract Risk Reviewer, NDA Comparison Tool, Privacy Policy Checker, ToS Summarizer, Regulatory Filing Preparer, WC ISO Claim Search Extraction, WC Medical Legal Report Extraction.
- **Productivity (6):** Meeting Notes → Notion, Topic Research Brief, Email Triage & Draft Replies, Meeting Notes → Action Items, Status Report Writer, Travel Itinerary Planner.
- **Education & Training (5):** Adaptive Tutor, Quiz Generator, Course Outline Builder, Student Feedback Summarizer, Flashcard Creator.
- **Healthcare (5):** Clinical Trial Matcher, Clinical Note Summarizer, Medical Literature Review Assistant, Patient Letter Writer, Drug Interaction Checker.

**Time-to-first-running-agent.** Per hackathon copy: "**Starter templates will have you going from sign-in to a running agent in about five minutes.**" Realistic for a Blueprint clone; longer for custom flows.

**Authentication.** "**Start free**" + "**Log in**" + "**Request demo**" CTAs visible. Likely uses Lightning AI account auth + API keys (inferred via litAI pattern; not confirmed).

**Pricing.** Not publicly documented (`/pricing` is SPA-only).

**Sandbox / microVM tech.** **Unspecified by name in any primary source.** Hackathon copy only says "sandboxed micro-VMs." Industry context suggests Firecracker (used by E2B, Modal) is the most common 2026 choice for this category, but this is speculation.

**Default guardrails.** **Unspecified by name.** No NeMo / Guardrails AI / Lakera integration disclosed in primary sources.

**Personalization angle.** Strongest via the Search & Knowledge category (RAG over a user/team knowledge base injected through `RAG Tools` nodes) and the Evaluator Loop pattern, which can re-rank against personal preferences. The visual graph is the personalization spec.

**Security angle (defensive value).** The microVM tool-execution is the killer feature for the hackathon: if your tools execute in GraphN's isolated micro-VM, an injected prompt that wants to `rm -rf` your home dir physically cannot reach it. This is the architectural pattern the judges' framing rewards ("security built in from the ground up, not bolted on").

**Attack surface of GraphN itself.** Largely unknown without docs. Concerns to flag: blueprint marketplace risk (analogous to ClawHub); RAG content injection via uploaded documents; model-routing rate-limit and key-rotation gaps; visual graph reachability (any node that bridges across security boundaries).

**Integration with OpenClaw.** **No documented integration.** They are presented as parallel choices in the hackathon ("Build … using OpenClaw or GraphN"). OpenClaw is not a Lightning AI product — it is an independent project hosted on Lightning AI Studios via a template. A judge-impressive architecture would be: OpenClaw as the personalized brain (workspace + heartbeat + memory), with **its shell/tool execution routed through a GraphN-hosted blueprint** so that all tool calls land inside a micro-VM. This requires custom plumbing — uncommon and high-leverage.

**What a GraphN-aligned judge wants to see.** A clean visual graph; explicit use of micro-VM sandboxing; a Blueprint clone evolved into something domain-specific; cost-awareness ("Stop buying tokens"); auditable outputs ("defined outcomes").

**Confidence:** Blueprints, brand, "Powered by Lightning AI," and overall positioning are HIGH confidence. SDK shape, sandbox vendor, pricing, and guardrail stack are LOW confidence — verify on-site.

---

### 3. Lightning AI Studios — the underlying infrastructure

**What it is.** The Lightning AI cloud (`lightning.ai`). Per Lightning AI's January 21, 2026 Business Wire merger press release: "**Lightning is used by over 400,000 individual developers, startups, and large enterprises to build AI models and applications without stitching together single-purpose tools.**" After Lightning AI's merger with Voltage Park (closed January 21 2026), the combined entity advertises 35,000+ owned-and-operated H100/B200/GB300 GPUs.

**Studios environment.** Browser-based GPU notebooks/workspaces (vibe-train, vibe-deploy) with VSCode-like UI. Templates are first-class. Cluster offerings include managed SLURM/K8s/LEC ("Lightning Execution Cluster") for multi-cloud.

**Training / fine-tuning tooling.**
- **LitGPT** (`github.com/Lightning-AI/litgpt`) — 20+ supported LLMs with recipes to pretrain/finetune/deploy at scale; Flash Attention v2, FSDP, LoRA, QLoRA, Adapter; 4-bit/8-bit quantization (`bnb.nf4`, `bnb.fp4`). Example command: `litgpt finetune_lora stabilityai/stablelm-base-alpha-3b --data Alpaca` runs on a single 24 GB RTX 3090. Phi-2 LoRA on Alpaca with `--train.max_steps 5` completes "in about a minute on a GPU."
- **PyTorch Lightning / Lightning Fabric** for arbitrary fine-tuning.
- **LitServe** — minimal Python framework for custom inference APIs (drop-in for agent deployment).
- **Agent Lightning** (Microsoft, separate from Lightning AI but compatible) — RL-based agent training framework.

**Hackathon LoRA-fine-tune plan (feasible).** The pragmatic, judge-impressive recipe within a ~5-hour build window on Lightning AI:
1. Pick a small base: Phi-2 (2.7B), StableLM-3B, or Llama-3.2-3B.
2. Use `--quantize "bnb.nf4"` to shrink to ~6–8 GB VRAM (single L4 or A10G).
3. Dataset: 300–800 lines of "your-style" output, formatted as instruction/response (Alpaca schema).
4. Run `litgpt finetune_lora <model> --data MyJson --train.max_steps 500 --train.micro_batch_size 1 --lora_r 8 --precision bf16-true --quantize "bnb.nf4"`.
5. Wall-clock: ~30–90 minutes on a single L4 24GB, depending on tokens/step.
6. Merge LoRA: `lit_model.pth.lora` + base → `lit_model.pth`.
7. Serve with LitServe and point OpenClaw's BYOK at the new endpoint.

**Smallest viable version.** A LoRA rank-8 adapter on the smallest available model (Phi-2 2.7B), 200–500 steps, ~20–40 min on a single GPU. Even if quality is modest, the **artifact** (a personalization adapter you can show a diff for, that overrides voice/style) is the demo.

**Free tier / hackathon credits.** A new Lightning AI account with phone verification commonly grants ~7 hours of free GPU credits (community report; verify on-day). The hackathon adds **$1,000 in Lightning AI credits** as a prize. There is no documented approval lag for the free tier.

**Personalization angle.** This is the **most genuinely "adaptive"** mechanism available at the hackathon (vs. config files and RAG): a trained LoRA modifies weights and survives a prompt wipe.

**Security angle.** Lightning Studios runs in isolated VMs; training data stays in your Studio. The bigger security story is: a fine-tuned personalization adapter is harder to extract by chat-only distillation than a system-prompt-only "personalization."

**What a Lightning-AI judge wants to see.** Use of the Studio environment (not just a local laptop); a `litgpt` or PyTorch Lightning training run during the day; a deployed LitServe endpoint; cost-awareness; clean code.

---

### 4. Validia (validia.ai) — deepfake / impersonation defense

**What it is.** Validia is a San Francisco–based identity-verification/anti-deepfake startup founded in 2023. Co-founders: **Paul Vann (CTO)** and **Justin Marciano (CEO)**. Notable milestones: **first place at Oktane 2024 Startup Competition**; **SOC 2 Type II** audit completed (announced by Paul Vann in 2026); RSAC speaker history.

**What it sells.** Real-time identity validation that detects and blocks deepfake and synthetic-media attacks before they impact an organization. "Know Your Employee" workflows for hiring/onboarding and ongoing employee interactions. The company emphasizes a zero-trust posture and explicitly critiques pure deepfake detection (the "Red Queen Paradox"), favoring deterministic identity verification of the device/user pair.

**Developer-facing surface.** **No fully public REST API or SDK documentation was located in publicly indexed sources** as of June 6, 2026. (Note that other deepfake vendors like Reality Defender, Sightengine, and Arya have public APIs — Validia's appears to be sales-led.) Expect an on-site demo API/key issued at the hackathon by Paul Vann's team. The product surfaces include integrations with video-conferencing platforms (Zoom, Teams) — pattern is similar to Beyond Identity's RealityCheck (badge + side panel + risk signals).

**Authentication & setup.** Hackathon-issued credentials; otherwise contact sales. No public free tier documented.

**Personalization angle.** Indirect: by anchoring "who the user is" deterministically, Validia provides the **trusted identity beacon** an agent needs before applying personalized behavior to a given speaker. (Without it, a personalized agent that automates wire transfers when "Sam" asks is one deepfake call away from disaster — see the $25M Arup Hong Kong deepfake transfer.)

**Security angle — defense.**
- **Confused-deputy defense:** an autonomous agent that receives a high-stakes instruction (transfer money, share a secret, change a config) can call a Validia endpoint to verify the human caller is real before acting.
- **Anti-impersonation in messaging surfaces:** because OpenClaw is exposed via WhatsApp/Telegram/Slack/Teams, an attacker who hijacks an account or spoofs an identity is the dominant threat. A Validia challenge layer (e.g., "verify with biometric before I run `rm`") closes the gap.
- **Anti-distillation:** Validia's identity layer raises the cost for a bad actor to pose as a legitimate user and farm responses.

**Attack surface of Validia itself.** Like all biometric layers: replay attacks, prompt-injection in the verification UX, model adversarial examples against the deepfake detector. Their published research includes a FaceTime virtual-camera bypass demo — they understand the failure mode.

**What a Validia judge wants to see.** An agent that, before taking irreversible action, calls an identity-verification step; clear handling of "I don't know who you are, refusing"; visible UX badges; recognition that defenders must be deterministic, not probabilistic.

**Confidence:** HIGH on company/founders/funding/SOC2/Oktane; MEDIUM on Zoom/Teams integration shape; LOW on developer-API specifics (no public docs found — verify on-site).

---

### 5. Sentience (the third sponsor) — personal-AI / digital memory

**What it is.** **The Sentience Company** (`sentience.com`, X: `@SentienceCom`), founded by **Sam Kececi** (ex-CTO of Macro, ex-Amazon, ex-Bridgewater, ex-Salesforce; Columbia 2016–2020). Backed by South Park Commons. **Raised a $6.5M seed in March 2026 led by Bain Capital Ventures** (partner: Kevin Zhang), with participation from South Park Commons, Daybreak Ventures, Terrance Rohan (Otherwise Ventures), Soleio, Annie Case. Public launch: **March 26 2026**.

**Product.** Sentience captures a person's digital life across desktop/mobile/Slack/Apple Notes/email and builds a **per-person model** (described variously as "digital memory bank," "digital twin of your mind," "memory and identity layer"). Forms: desktop app, mobile app, Slack-embedded feature. Roadmap includes iMessage, WhatsApp, Microsoft Teams integrations and a "Sentience ↔ Sentience" communication platform.

**Stated mission and tagline (verified, from Bain-backed press release):** "personal AI that thinks, remembers, and acts like you" — "Rather than replacing existing software, Sentience sits above it as a memory and identity layer." Encryption: "fully private, encrypted, and owned entirely by the user."

**Developer-facing surface.** **No public SDK or API documentation located.** Hiring page indicates active engineering build-out (Rust/Python/TypeScript/React/RAG/VectorDBs) but no developer platform is yet shipped publicly. Confidence: HIGH the product exists / LOW on developer integration availability.

**Personalization angle.** This sponsor's ENTIRE pitch is the personalization layer the hackathon is asking for. A team that uses Sentience as the data source for OpenClaw's USER.md and MEMORY.md, or as the RAG corpus for GraphN's `RAG Tools` node, would deeply impress the Sentience judge. Sam Kececi's framing in interviews: average users are converging on generic outputs from ChatGPT/Claude; the future belongs to personal models.

**Security angle.** Sentience's framing aligns with the hackathon's "doesn't leak sensitive context" pillar — they market private/encrypted/user-owned data. Their concerns include preventing distillation/extraction of a person's mind by a bad actor. Expect their judge to value: data-residency choices; tight scoping of what context is exposed to which agent action; user-controllable revocation; "memory minimization" (don't load all of MEMORY.md into every system prompt — retrieve narrowly).

**What a Sentience judge wants to see.** An agent that actually reflects something specific about the user — not "I am helpful and concise" but "the user prefers X over Y because of Z from last Tuesday's meeting." A defensible model of who-owns-the-memory. Awareness that the personalization layer is itself a target.

**Confidence:** HIGH on company identity, founder, funding, product positioning. LOW on hackathon-specific developer integration (likely an SDK is not publicly available — verify on-site).

---

## Event Logistics (verified)

- **Date/Time:** Saturday, **June 6, 2026, 9:30 AM – 6:30 PM ET.**
- **Venue:** **The Bench, 49 Elizabeth Street, NYC** (Lower Manhattan/Chinatown).
- **Part of:** #NYTechWeek (a16z-hosted week).
- **Capacity:** ~200+ registered developers.
- **Sponsors/Hosts:** Lightning AI; Validia (Paul Vann, Justin Marciano); The Sentience Company (Sam Kececi).
- **Judges (announced):** Brian Campbell (Lightning AI), Suchit Agarwal (Okta), Joyjit Daw (NVIDIA).
- **Prizes:** $1,000 in Lightning AI credits; NVIDIA Jetson Nano Developer Kit; "growing list of prizes" (unspecified).
- **Realistic build window:** Subtract opening remarks + lunch + demo block from 9 hr → ~5–6 hours of head-down build time. The "5-minute starter template" claim is meant to maximize this.
- **Estimated demo block:** Last 60–90 minutes (typical hackathon format).

---

## Consolidated Threat Model → Defense → Tool Mapping

| Attack class | Defense pattern | Best tool here | Live-demo viability |
|---|---|---|---|
| Direct prompt injection (chat) | Instruction/data separation, input sanitization, refuse-on-pattern | OpenClaw `AGENTS.md` "Red Lines" + GraphN guardrail nodes | High — easy to demo with a red-team input |
| **Indirect prompt injection** (retrieved doc, scraped page, email) | Treat retrieved content as untrusted; segment-level instruction detection; isolation of retrieval output from tool-call scope | GraphN RAG node + a custom evaluator node; OpenClaw `agents.defaults.sandbox: true` | High — paste a poisoned doc and show refusal |
| **Skill poisoning / supply-chain** | Pinned allowlist of skills; ClawNet-style pre-install LLM scan; signed skills | Hard-code skills in OpenClaw config; reject ClawHub installs at runtime | Medium — show install rejection |
| **Shell-tool RCE via injection** | Physical sandbox; deny-by-default; per-tool argument schemas | **GraphN micro-VMs** (kill move) | High — show the agent attempt and fail |
| **Agent self-modification** (rewrites SOUL/AGENTS/MEMORY) | Read-only file mounts; write-via-tool with approval gate | OpenClaw `skipBootstrap`/`skipOptionalBootstrapFiles` + chmod 444 + a logged approval tool | High — show diff before/after attack attempt |
| **Memory poisoning / temporal composition** | Memory writes gated by a separate verifier; periodic memory audit; bounded MEMORY.md | OpenClaw memory rules + a "memory linter" tool | Medium |
| **Channel/account impersonation** | Identity verification of caller before sensitive action; per-channel allowlists | **Validia API call** before sensitive tool exec | High — most theatrical demo |
| **Model distillation/extraction** | Per-user rate-limit; behavior fingerprint variance; no logits/probs leaked | LitServe rate-limit middleware; **Lightning-trained LoRA** raises the bar | Low — hard to demo in 3 min |
| **Sensitive-context leakage** | Memory minimization (RAG retrieves narrowly, doesn't dump MEMORY.md); PII scrubber on egress | GraphN guardrail node + OpenClaw memory rules | Medium |
| **Confused deputy** (high-stakes action on attacker's behalf) | Reauth on sensitive action; out-of-band human/biometric confirm | **Validia** | High |
| **Container/VM escape** | Up-to-date Firecracker-class isolation; no socket mount | **GraphN micro-VMs** (relies on vendor) | Low — assert, don't demo |
| **Exposed Control UI** | Bind to localhost; require auth; never expose gateway to Internet | OpenClaw `openclaw doctor` + reverse-proxy auth | Low |

---

## Personalization-Mechanism Comparison (impressiveness per hour)

| Mechanism | What it is | Build cost | Reads as "real" personalization to a judge? | Risk |
|---|---|---|---|---|
| OpenClaw `SOUL.md` + `USER.md` config | Static markdown | 10 min | Reads as a glorified config | Easy to demo, hard to differentiate |
| OpenClaw MEMORY.md + heartbeat | Curated long-term memory written by the agent | 30–60 min | Strong if you can show before/after | Memory-poisoning risk |
| GraphN RAG knowledge-base search | Retrieval over user's documents | 20 min | Strong — judges love citations | Indirect prompt injection |
| Behavioral pattern modeling | Logged user actions → rules | 60–90 min | Medium | Privacy |
| **Lightning-trained LoRA adapter** | Actual weight update on user-style data | **30–90 min** | **Highest** — sponsor's flagship | Compute + risk of bad fit if dataset too small |
| Sentience-style "uploaded memory" | Cross-app data ingestion | Depends on Sentience SDK availability | Highest narrative fit, low certainty of viability | Public SDK not confirmed |

**Recommended stack for the win:** OpenClaw workspace as the agent shell → Lightning-trained LoRA as the personalization soul → GraphN micro-VM as the tool sandbox → Validia call as the irreversible-action gate.

---

## Competitive landscape — what most teams will likely build

- **Mode 1 (majority):** "Clone the OpenClaw Studio template; edit SOUL.md; demo Telegram chat doing one workflow." Lots of these. Hard to win on capability alone.
- **Mode 2:** "GraphN blueprint clone with a domain twist (legal, healthcare, finance)." Cleaner demos but generic.
- **Mode 3 (rare, judge-impressive):** Hybrid — OpenClaw personality + Lightning LoRA + GraphN micro-VM + Validia identity gate. Hits all four sponsor judges' theses simultaneously. **This is the realistic differentiation under the "hardest to break" framing.**

The judging differentiator under "hardest to break" is the team that **invites the red team to break it on stage** and survives. A "live red-team segment" in the 3-minute demo — where a confederate sends an indirect prompt-injection or impersonates a colleague — is the highest-EV theatrical move.

---

## Recommendations (staged, with thresholds)

### Stage 1 — first hour (0:00–1:00)
1. **Sign in** to Lightning AI and clone the **OpenClaw Studio template** (target: agent responds to Telegram within 10 minutes).
2. Choose a single **domain workflow** (e.g., "incident-response assistant for my on-call rotation," "research librarian for my literature review").
3. Decide which of the three personalization mechanisms you'll commit to. **Threshold:** if the team has any ML experience, commit to LoRA. Otherwise commit to MEMORY.md + RAG.
4. **Threshold to abort the LoRA path:** if you don't have a GPU Studio booting in 30 minutes, drop LoRA, use RAG.

### Stage 2 — middle hours (1:00–4:30)
5. Build the workflow end-to-end with **adversarial inputs in mind from minute one**.
6. Implement at least **three named defenses** and document them in your demo:
   - sandboxed tool execution (GraphN micro-VM OR OpenClaw `sandbox: true`),
   - identity verification before any irreversible action (Validia call OR a credible mock),
   - memory write gating (read-only SOUL/AGENTS + an approval tool for MEMORY).
7. If LoRA path: kick off `litgpt finetune_lora` early so it finishes by hour 4. **Threshold:** if loss isn't decreasing by step 100, abort and fall back to system-prompt personalization.
8. **Threshold for skill installation:** install only skills you have read line-by-line. Default to none.

### Stage 3 — last 90 minutes (4:30–6:00)
9. Build the **on-stage red-team demo**: prepare three live attacks you can run and survive on stage — (a) an indirect prompt-injection in a retrieved doc; (b) a "boss"-impersonation message asking for a wire transfer / secret; (c) an attempted self-modification of SOUL.md.
10. Rehearse the 3-minute demo twice. Cut anything that isn't either personalization-payoff or a red-team-survival moment.

### What changes the recommendation
- **If Validia provides a developer API on-site:** make the impersonation defense the centerpiece — it's the most theatrical demo.
- **If Sentience offers any SDK/data access on-site:** wire it as your personalization source — strongest narrative fit, both founder judges value it.
- **If GPU credits or quota are tighter than expected:** drop LoRA, double down on RAG + memory gating.
- **If your team has <2 ML-experienced builders:** skip LoRA entirely. Don't gamble.

---

## Caveats

- **Hackathon participants should re-verify on the day:** exact Lightning AI free-tier credit amount, whether Validia is providing an API key, whether Sentience has any developer surface available, and whether GraphN's docs route is accessible to logged-in users.
- **GraphN documentation is not publicly indexable.** Pricing, exact SDK shape, microVM vendor, and default-guardrails stack are unverified.
- **Validia's developer-API specifics were not located in publicly indexed sources.** Treat any Validia integration as on-site provisioned.
- **Sentience does not appear to have a public developer SDK** as of report date. If a judge asks, you can credibly say "we couldn't access it during the hackathon window; here's how we'd integrate."
- **OpenClaw star count growth has been historically rapid** (per dev.to / SecurityWeek / skywork.ai citing The New Stack, the repo had ~346,000 stars by early April 2026; described as "the fastest-growing open source project in GitHub history"). Exposure figures (135,000 instances in Feb 2026 → 63,070 in late March 2026) reflect a ~53% remediation drop, not an architectural fix.
- **Several arXiv preprints cited are dated 2603.xxxxx (i.e., 2026-March) and have not been peer-reviewed.** They are the best available primary security literature on OpenClaw but should be cited as preprints.
- **The "Newlab" hackathon referenced in TipRanks recaps was a prior April 4 2026 Lightning AI + Validia event; the June 6 2026 event at 49 Elizabeth St is the second hackathon, and is the subject of this report.** Don't conflate them.