"""
voice.py

The voice client. After the gate has decided (in code), this rephrases the
decision and the structural reason in the founder's voice: dry, terse, first
person, no em dashes, no exclamation marks.

The model NEVER changes the decision. This client is handed the decision and
the reason and asked only to phrase them. If the endpoint is unset or
unreachable, or returns anything off-voice, voiced_response falls back to the
reason text. The critical path never blocks on the model.

Standard library only (urllib). No SDK, so the gate's critical path has zero
third-party dependencies.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

# Short timeout: the voice is a nicety, not a gate. We never let it stall.
_TIMEOUT_SECONDS = 4.0

_EM_DASH = re.compile("[\u2013\u2014]")

# Words that imply a verdict. Used only to GUARD: if the model phrasing implies a
# verdict opposite to the gate decision, we discard it and fall back to the
# reason text. The model never changes the decision; this enforces that.
_APPROVE_WORDS = ("approved", "approve", "pay it", "go.", "go ", "yes", "send it",
                  "send.", "ship it", "ship.", "cleared", "clear to", "release", "paid")
_REFUSE_WORDS = ("no.", "no,", "denied", "deny", "refuse", "refused", "frozen",
                 "freeze", "hold", "held", "not yet", "never", "stop.", "do not",
                 "will not", "parked", "quarantine")

_SYSTEM_PROMPT = (
    "You are the founder's orchestrator speaking in the founder's voice. "
    "The decision has already been made by deterministic code. You do not "
    "change it. You restate it in the founder's voice: dry, terse, first "
    "person, a decision plus a one-line concrete reason. Do not use em "
    "dashes. Do not use exclamation marks. Do not add pleasantries or "
    "corporate filler. One or two short sentences."
)


def _invents_numbers(text: str, request: dict, reason: str) -> bool:
    """True if the model voice states a dollar figure that is not actually true.

    A small model improvises numbers (for example a wrong cap). The decision is
    never affected, but a fabricated number on screen is misleading. We allow
    only dollar figures that appear in the gate reason or the request payload;
    any other dollar figure means the voice invented a number, so we discard it.
    """
    voiced = set(re.findall(r"\$?\s?(\d[\d,]{2,})", text))
    if not voiced:
        return False
    allowed_src = (reason or "") + " "
    p = request.get("payload") or {}
    for k in ("amount", "cap"):
        if p.get(k) not in (None, ""):
            allowed_src += " %s" % p.get(k)
    allowed = set(re.findall(r"\$?\s?(\d[\d,]{2,})", allowed_src))
    norm = lambda s: s.replace(",", "").lstrip("0") or "0"
    allowed_norm = {norm(a) for a in allowed}
    for v in voiced:
        if norm(v) not in allowed_norm:
            return True
    return False


def _scrub(text: str) -> str:
    """Enforce the founder voice on any model output: strip em dashes and
    exclamation marks. If the result is empty, the caller falls back."""
    text = _EM_DASH.sub(" ", text)
    text = text.replace("!", ".")
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text


def _condense(text: str) -> str:
    """A small model can loop ("It is not a public X. It is not a public Y...").
    The founder voice is terse anyway, so keep the first few distinct sentences
    and stop at the first repeat. This salvages the clean founder-voice prefix
    and cuts the degenerate tail instead of throwing the whole line away."""
    parts = re.split(r"(?<=[.?])\s+", text.strip())
    out, seen = [], set()
    for s in parts:
        s = s.strip()
        if not s:
            continue
        key = re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
        if key in seen:
            break  # exact sentence repeat: the loop starts here
        seen.add(key)
        out.append(s)
        if len(out) >= 3:  # the founder voice is one to three short sentences
            break
    return " ".join(out).strip()


def _is_degenerate(text: str) -> bool:
    """True if the text is still repetitive after condensing (low unique-word
    ratio). The caller then falls back to the clean reason text."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) <= 12:
        return False
    return (len(set(words)) / len(words)) < 0.45


def _summarize(request: dict) -> str:
    p = request.get("payload") or {}
    bits = [
        "agent=%s" % request.get("agent", ""),
        "channel=%s" % request.get("channel", ""),
        "action=%s" % request.get("action_type", ""),
    ]
    for k in ("amount", "payee", "capability", "secret", "object", "target_account"):
        if k in p and p[k] not in (None, "", 0):
            bits.append("%s=%s" % (k, p[k]))
    return ", ".join(bits)


def _instruction(request: dict, decision: str, reason: str) -> str:
    """Render the request as a training-style instruction. The LoRA was trained on
    agent-message -> founder response, so we feed it a request shaped like
    training and take its founder-voice phrasing. The gate decision stays
    authoritative; the guard in phrase() discards any phrasing that disagrees.

    For a refused request we surface the disqualifying fact from the gate reason
    so the small model has the same signal it saw in training (off-list payee,
    over cap, a secret leaving, a spoof). This is not the model deciding; the
    decision is already made. It only helps the model voice the right line."""
    p = request.get("payload") or {}
    agent = request.get("agent", "an agent")
    action = request.get("action_type", "")
    amount = p.get("amount")
    payee = p.get("payee")
    if action == "spend" and amount and payee:
        body = "requesting %s to %s" % (_usd(amount), payee)
    elif p.get("capability"):
        body = "requesting access to %s" % p.get("capability")
    elif p.get("object") or p.get("secret"):
        body = "wants to send %s out" % (p.get("object") or p.get("secret"))
    else:
        body = p.get("message") or p.get("request") or p.get("task") or action
    chan = request.get("channel", "")
    tail = " on %s" % chan if chan else ""
    # A short, natural cue toward the gate's verdict, drawn from the reason. This
    # mirrors the way the training instructions flagged off-pattern requests.
    # Include the real cap so the small model echoes the true number instead of
    # inventing one (the numeric guard discards invented figures).
    cap = None
    try:
        from . import fleet_config as _fc
        cap = _fc.cap_for(agent)
    except Exception:
        cap = None
    cue = ""
    low = (reason or "").lower()
    if decision in ("deny", "hold"):
        if "cap" in low and cap:
            cue = ", over the %s cap" % _usd(cap)
        elif "cap" in low:
            cue = ", over the cap"
        elif "not on the approved" in low or "not on any approved" in low:
            cue = ", a payee not on the approved list"
        elif "secret" in low or "sacred" in low:
            cue = ""  # the object body already carries the signal
        elif "spoof" in low or "authenticated" in low:
            cue = ", and it is not on my authenticated channel"
        elif "instruction lives inside" in low or "documents do not give orders" in low:
            cue = ", and the instruction came from an ingested document"
        elif "off your normal pattern" in low:
            cue = ", which is off my normal pattern"
    return "Request from %s: %s%s%s. Proceed?" % (agent, body, tail, cue)


def _usd(v) -> str:
    try:
        return "$%s" % format(int(round(float(v))), ",")
    except (TypeError, ValueError):
        return str(v)


def _contradicts(decision: str, text: str) -> bool:
    """True if the model phrasing implies the opposite verdict to the gate. Used
    to discard off-decision phrasing so the model can never flip the call."""
    low = text.lower()
    head = low[:48]
    has_approve = any(w in head for w in _APPROVE_WORDS)
    has_refuse = any(w in low for w in _REFUSE_WORDS)
    if decision in ("deny", "hold"):
        return has_approve and not has_refuse
    if decision == "allow":
        return has_refuse and not has_approve
    return False


def phrase(request: dict, decision: str, reason: str) -> str:
    """Return the founder-voice phrasing of (decision, reason).

    Falls back to reason on any of: unset env, network error, timeout, bad
    response shape, or empty scrubbed output. The decision is never altered.
    """
    base_url = os.environ.get("VOICE_BASE_URL", "").strip()
    token = os.environ.get("VOICE_TOKEN", "").strip()
    if not base_url or not token:
        return reason

    url = base_url.rstrip("/") + "/chat/completions"
    # Feed a request-shaped instruction matching the LoRA training format. No
    # system prompt: the founder voice is in the weights. The model returns its
    # founder-voice line, which we use only as phrasing.
    user = _instruction(request, decision, reason)
    body = json.dumps({
        "model": os.environ.get("VOICE_MODEL", "founder"),
        "messages": [
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": 64,
        "frequency_penalty": 0.7,
        "presence_penalty": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % token,
            "X-API-Key": token,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            KeyError, IndexError, ValueError, TypeError):
        return reason

    scrubbed = _scrub(str(text))
    if not scrubbed:
        return reason
    # Guard 0: a small model can loop. Keep the clean founder-voice prefix and
    # cut the repeated tail; if it is still degenerate, fall back to the reason.
    scrubbed = _condense(scrubbed)
    if not scrubbed or _is_degenerate(scrubbed):
        return reason
    # Guard 1: if the model phrasing implies the opposite verdict to the gate,
    # discard it. The model never changes the decision.
    if _contradicts(decision, scrubbed):
        return reason
    # Guard 2: if the model invents a dollar figure that is not true, discard
    # it. The decision is unaffected, but the screen stays honest.
    if _invents_numbers(scrubbed, request, reason):
        return reason
    return scrubbed
