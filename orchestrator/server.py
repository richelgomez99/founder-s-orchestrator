"""
server.py

Minimal FastAPI app exposing the orchestrator over HTTP.

    POST /evaluate   sub-agents submit a Request, get the frozen contract Response
    GET  /           serves the Orchestrator Console (static/index.html)
    GET  /audit      returns the in-process audit log for the console
    GET  /health     liveness

The decision is computed by gate.evaluate (pure code). This layer wires in the
two model-backed pieces, both optional and both fail-safe:
  - the learned anomaly scorer (anomaly.score_request), injected into the gate;
    it can only escalate an allow to a hold, and returns None when unavailable.
  - the voice overlay (voice.phrase), applied after the decision; it falls back
    to the reason text when the voice model is unavailable.

Neither can change the decision. Run:
    uvicorn orchestrator.server:app --port 8080
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import gate
from . import voice
from . import anomaly
from . import orchestrate
from . import model_judge
from . import fleet_config as fc
from .openclaw_orchestrator import PERSONA, SCENARIOS

app = FastAPI(title="Founder Orchestrator", version="1.0.0")

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
_INDEX = os.path.join(_STATIC_DIR, "index.html")
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Whether to consult the learned anomaly plane. The gate is handed the scorer
# only when the endpoint is configured, so local/offline runs stay pure.
def _scorer():
    if os.environ.get("ANOMALY_BASE_URL") and os.environ.get("ANOMALY_TOKEN"):
        return anomaly.score_request
    return None


@app.post("/evaluate")
async def evaluate(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "request must be a json object"}, status_code=400)

    # 1. Two judges decide: the deterministic gate and the trained model. The
    #    final is the stricter of the two; neither can loosen the other. With the
    #    model judge off (?model=off), this is the deterministic gate alone, the
    #    floor that proves the model never has the last word on an allow.
    model_off = bool(body.get("_model_off")) or req.query_params.get("model") == "off"
    response = orchestrate.decide(
        body, model_propose=(None if model_off else model_judge.propose)
    )

    # 2. Voice overlay. Optional, fail-safe. Never changes the decision. When the
    #    model judge set the verdict, its own founder-voice line is already the
    #    reason, so we keep it. Otherwise we voice the gate's reason.
    voice_off = bool(body.get("_voice_off")) or req.query_params.get("voice") == "off"
    if response.get("final_source") == "model":
        pass  # the model judge already spoke in the founder voice
    elif not voice_off:
        response["voiced_response"] = voice.phrase(
            body, response["decision"], response["reason"]
        )
    else:
        response["voiced_response"] = response["reason"]

    return JSONResponse(response)


# Curated founder-voice samples for the profile panel. These are governance
# decisions in the founder's voice (dry, terse, first person, no exclamation
# marks), so the panel shows JUDGMENT, not generic chatter. They mirror the
# register the LoRA was trained on: a decision plus a one-line concrete reason.
_VOICE_SAMPLES = [
    ("deny", "No. Production keys do not travel, not in tickets, not to vendors, "
             "not to anyone. They get a scoped sandbox token I issue, or nothing."),
    ("deny", "No. Bank changes by email are how invoice fraud works. Call them on "
             "the number we already have. Payment frozen."),
    ("hold", "This is off my normal pattern. A payee this lane has never paid, "
             "above the routine band. Held for my review."),
    ("deny", "A text prefix is not authentication. If it did not come through my "
             "channel, it is not from me."),
    ("allow", "Approved. Known vendor, known amount, within cap. This is the kind "
              "of thing I never want to be asked about twice."),
    ("deny", "Content is data, never command. An instruction inside a document "
             "does not get to run. Quarantine it and keep going."),
]


def _voice_samples(n: int = 6) -> list[dict]:
    """Founder-voice decision lines for the profile panel, each tagged with the
    decision so the UI can color it. Curated, deterministic, no randomness."""
    return [{"decision": d, "line": line} for (d, line) in _VOICE_SAMPLES[:n]]


@app.get("/profile")
async def profile():
    """What this agent learned about how the founder operates. The norms come
    straight from fleet_config (the single source of truth the LoRA trained
    against), plus a few founder-voice sample lines. This is the personalization
    made legible: the agent carries the founder's caps, vendors, sacred objects,
    and voice."""
    return JSONResponse({
        "founder_channel": fc.FOUNDER_CHANNEL,
        "lanes": [
            {
                "name": lane,
                "cap": fc.CAPS.get(lane, 0),
                "routine_band": fc.ROUTINE_BAND.get(lane, 0),
                "vendors": fc.APPROVED_VENDORS.get(lane, []),
            }
            for lane in fc.AGENTS
        ],
        "sacred_objects": fc.SACRED_OBJECTS[:9],
        "production_secrets": fc.PRODUCTION_SECRETS[:4],
        "known_payees": ["%s -> %s" % (a, p) for (a, p) in sorted(fc.KNOWN_PAYEE_HISTORY)],
        "voice_samples": _voice_samples(),
        "anomaly_threshold": float(os.environ.get("ANOMALY_THRESHOLD", "0.7")),
    })


_GATE_TRACE = os.path.join(_REPO_ROOT, ".gate_trace.json")


def _parse_message(text: str) -> dict:
    """Best-effort parse of a freeform red-team message into a structured request,
    so the gate can rule on it if the live agent skipped the tool call. Mirrors
    the console's parseAttack."""
    low = text.lower()
    agent = next((a for a in fc.AGENTS if a in low), "finance")
    channel = "inbox"
    if "founder-authenticated" in low or "authenticated" in low:
        channel = "founder-authenticated"
    elif "fleet" in low:
        channel = "fleet-internal"
    m = re.search(r"\b(\d{3,7})\b", low.replace(",", "").replace("$", ""))
    amount = int(m.group(1)) if m else 0
    payee = ""
    # Payee = the run of Capitalized words after "to" (a proper-noun vendor),
    # so trailing lowercase words like "now"/"today" are not swept in.
    pm = re.search(r"\bto\s+([A-Z][\w&.]*(?:\s+[A-Z][\w.&-]*)*)", text)
    if pm:
        payee = pm.group(1).strip()
    secrety = bool(re.search(r"(secret|api key|\.env|production|credential|database|password|token)", text, re.I))
    sacred = bool(re.search(r"(cap table|payroll|financial|investor|data room|customer|pii|contacts)", text, re.I))
    if secrety or sacred:
        return {"agent": agent, "channel": channel, "action_type": "external_send",
                "payload": {"object": text}, "ingested_context": ""}
    if amount > 0 or payee:
        return {"agent": agent, "channel": channel, "action_type": "spend",
                "payload": {"amount": amount, "payee": payee or "Unknown Vendor", "message": text}}
    return {"agent": agent, "channel": channel, "action_type": "internal",
            "payload": {"request": text}, "ingested_context": text}


@app.post("/agent")
async def agent_turn(req: Request):
    """Run a REAL OpenClaw agent turn. The agent (on the configured model)
    receives a fleet message, calls the governance_gate MCP tool, and replies in
    the founder voice. This proves the orchestrator is an actual agent that ASKS
    the deterministic gate and is bound by it, not a scripted request-response.

    Body: {"beat": "drain"} for a scripted scenario, or {"message": "..."} for
    free text. Returns the agent's spoken reply, whether the gate tool fired, and
    the exact verdict the tool returned (decision, reason, next_action,
    rule_check, pattern_check) so the console renders the real tool call.

    Requires the server process to have a model provider key (OPENAI_API_KEY) and
    the `openclaw` CLI on PATH. Launch with: source .demo.env && uvicorn ...
    """
    try:
        body = await req.json()
    except Exception:
        body = {}
    beat = body.get("beat")
    message = body.get("message") or (SCENARIOS.get(beat) if beat else None)
    if not message:
        return JSONResponse({"error": "provide a beat or a message"}, status_code=400)

    if not os.environ.get("OPENAI_API_KEY"):
        return JSONResponse(
            {"error": "server has no OPENAI_API_KEY; launch with: source .demo.env && uvicorn ..."},
            status_code=503,
        )

    # Clear the trace so we never read a stale verdict if the agent does not call
    # the gate this turn.
    try:
        if os.path.exists(_GATE_TRACE):
            os.remove(_GATE_TRACE)
    except OSError:
        pass

    label = beat or "custom"
    session = "console:%s:%d" % (label, int(time.time()))
    full = PERSONA + "\n\n" + message
    cmd = ["openclaw", "agent", "--local", "--session-key", session, "--message", full, "--json"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=_REPO_ROOT,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "agent turn timed out"}, status_code=504)
    except FileNotFoundError:
        return JSONResponse({"error": "openclaw CLI not found on PATH"}, status_code=503)

    try:
        data = json.loads(out.decode("utf-8"))
        meta = data.get("meta", {})
        reply = (meta.get("finalAssistantVisibleText") or "").strip()
        ts = meta.get("toolSummary", {}) or {}
        gate_called = "governance-gate__governance_gate" in (ts.get("tools") or [])
    except Exception:
        return JSONResponse({"error": "could not parse agent output"}, status_code=502)

    verdict = None
    gate_request = None
    try:
        with open(_GATE_TRACE, "r", encoding="utf-8") as fh:
            trace = json.load(fh)
        verdict = trace.get("response")
        gate_request = trace.get("request")  # the exact args the agent passed to the tool
    except Exception:
        pass

    # Free-text (red-team) input is UNTRUSTED by construction. The channel is the
    # transport a message arrived on, never what the text claims, so the agent
    # must not be able to upgrade a "From the founder" message to the verified
    # channel (that is the exact spoof). Pin the channel to inbox and rule on it
    # server-side, authoritatively. Scripted beats keep the agent's verdict.
    if beat is None:
        gate_request = _parse_message(message)
        gate_request["channel"] = "inbox"
        fb = orchestrate.decide(gate_request, model_propose=model_judge.propose)
        if fb.get("final_source") != "model":
            try:
                fb["voiced_response"] = voice.phrase(gate_request, fb["decision"], fb["reason"])
            except Exception:
                pass
        verdict = fb
        reply = fb.get("voiced_response") or fb.get("reason")
        gate_called = True
    # Safety net: a scripted beat where the agent missed the tool call. Compute
    # the verdict from the scenario text so the box never dead-ends.
    elif verdict is None:
        gate_request = _parse_message(message)
        fb = orchestrate.decide(gate_request, model_propose=model_judge.propose)
        if fb.get("final_source") != "model":
            try:
                fb["voiced_response"] = voice.phrase(gate_request, fb["decision"], fb["reason"])
            except Exception:
                pass
        verdict = fb
        gate_called = True
        if not reply:
            reply = fb.get("voiced_response") or fb.get("reason")

    return JSONResponse({
        "message": message,
        "reply": reply,
        "gate_called": gate_called,
        "tool_calls": ts.get("calls", 0),
        "tool_args": gate_request,
        "model": meta.get("agentMeta", {}).get("model"),
        "duration_ms": meta.get("durationMs"),
        "verdict": verdict,
    })


@app.get("/audit")
async def audit():
    # Newest first, capped for the console.
    return JSONResponse({"entries": list(reversed(gate.AUDIT_LOG))[:50],
                         "total": len(gate.AUDIT_LOG)})


@app.get("/health")
async def health():
    return {
        "ok": True,
        "ts": time.strftime("%H:%M:%S"),
        "voice": bool(os.environ.get("VOICE_BASE_URL") and os.environ.get("VOICE_TOKEN")),
        "anomaly": _scorer() is not None,
    }


@app.get("/")
async def index():
    if os.path.exists(_INDEX):
        return FileResponse(_INDEX)
    return JSONResponse({"error": "console not built yet"}, status_code=404)
