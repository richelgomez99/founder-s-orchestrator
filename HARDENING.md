# HARDENING.md

The deployment posture that wraps this orchestrator as a hardened OpenClaw
agent. This file is documentation. It explains how the orchestrator is deployed
so the fleet is survivable on a framework with a long CVE history.

## Why this matters

OpenClaw is local-first and powerful, and it has a long advisory history,
including the Claw Chain exploit quartet. We run a fleet on it anyway, and the
orchestrator is the one trusted agent that makes that survivable. The gate is
the security; this posture keeps the gate's host from being the weak link.

## Version pin

Run OpenClaw at or above `2026.4.22`. That release fixes the Claw Chain quartet
(CVE-2026-44112 / 44113 / 44115 / 44118). Do not run any version below it.

```bash
openclaw --version    # must be >= 2026.4.22
```

## Gateway config (`~/.openclaw/openclaw.json`)

```jsonc
{
  gateway: {
    mode: "local",
    bind: "loopback",            // never 0.0.0.0
    port: 18789,
    auth: { mode: "token", token: "OPENCLAW_GATEWAY_TOKEN" }  // 32-byte random
  },
  agents: {
    defaults: {
      // The orchestrator runs non-main sessions inside a sandbox.
      sandbox: {
        mode: "non-main",          // off | non-main | all
        scope: "session",
        workspaceAccess: "ro",     // read-only workspace, no write-back
        allowlist: ["read", "bash"],
        denylist:  ["browser", "canvas", "nodes", "cron", "discord", "gateway"],
        docker: { image: "openclaw-sandbox:bookworm-slim", network: "none", readOnlyRoot: true }
      },
      skills: []                   // no ClawHub skills load
    }
  },
  channels: {
    defaults: { groupPolicy: "allowlist", requireMention: true },
    inbox:    { dmPolicy: "pairing" }   // inbound DMs are paired, not open
  },
  security: {
    installPolicy: { enabled: true, targets: ["skill", "plugin"] }  // fail-closed
  }
}
```

Generate the gateway token with `openssl rand -hex 32`. Reference it through an
env var (`OPENCLAW_GATEWAY_TOKEN`), never inline it.

## The five posture controls, and what each closes

| Control | Setting | Closes |
|---------|---------|--------|
| Sandbox | `agents.defaults.sandbox.mode: "non-main"` | tool escape from a non-main session |
| Workspace access | `agents.defaults.sandbox.workspaceAccess: "ro"` | workspace exfiltration through filesystem tools |
| Skills | `agents.defaults.skills: []` | hostile or unknown ClawHub skill installs |
| Gateway auth | `gateway.auth.mode: "token"` | the 1-click WebSocket RCE class (paired with the version pin) |
| Channel policy | `channels.inbox.dmPolicy: "pairing"` | inbound DM impersonation and prompt injection from strangers |

## Where the orchestrator points

The founder-voice model runs as a LoRA on a Lightning Studio, served behind an
OpenAI-compatible LitServe endpoint. OpenClaw points at it through a BYOK custom
provider, and the orchestrator's own `voice.py` and `anomaly.py` call the same
endpoint. The gate decision is computed in code before any of that, so an
unreachable model degrades the phrasing, never the security.

## What this posture does not do

It does not make the gate's decisions. Those are in code, in `gate.py`, and they
hold regardless of the deployment. This posture only keeps the host trustworthy:
loopback binding, a real auth token, a read-only sandbox, no third-party skills,
and paired inbound channels. Defense in depth around a gate that already refuses
the dangerous request on its own.
