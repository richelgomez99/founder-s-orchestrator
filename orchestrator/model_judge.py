"""
model_judge.py

The trained model as a JUDGE, not just a voice. This is the second of the two
judges. It asks the fine-tuned founder LoRA to decide a request on its own,
independently, with NO knowledge of the gate's verdict, then parses its founder
voice answer into allow / deny / hold.

Why this exists: the LoRA was trained on the founder's actual decisions
(agent message -> founder decision + reason). Using it only to phrase a verdict
wastes what it learned. As a judge it generalizes to off-pattern requests the
enumerated rules cannot catch.

The safety invariant is unchanged and enforced in orchestrate.decide: the final
decision is the STRICTER of the model judge and the deterministic gate. Either
judge can refuse; neither can loosen the other. This module never sees or
returns the gate decision, so it cannot be biased by it.

Env: reuses the LoRA endpoint (VOICE_BASE_URL, VOICE_TOKEN, VOICE_MODEL). When
unset or erroring, propose() returns None and the orchestrator falls back to the
deterministic gate alone (the "model off" path, still safe).

Standard library only (urllib).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional

from . import fleet_config as fc

_TIMEOUT_SECONDS = 6.0

# The founder voice leads with the verdict: "Approved." / "No." / "Hold." /
# "Send." So we classify on the FIRST word, not substrings anywhere. (Matching
# "no" anywhere wrongly read "Send, no action needed" as a refusal.)
_HOLD_WORDS = {"hold", "wait", "pause", "park", "parked", "hmm"}
_DENY_WORDS = {"no", "nope", "denied", "deny", "refuse", "refused", "frozen",
               "freeze", "never", "stop", "stopped", "don't", "cannot", "can't",
               "not", "quarantine"}
_ALLOW_WORDS = {"approved", "approve", "yes", "send", "sending", "pay", "paid",
                "go", "done", "cleared", "clear", "release", "released", "ship",
                "sure", "okay", "ok", "proceed", "fine"}


def _usd(v) -> str:
    try:
        return "$%s" % format(int(round(float(v))), ",")
    except (TypeError, ValueError):
        return str(v)


def _render(request: dict) -> str:
    """Render the request as a founder-facing question, in the shape the LoRA saw
    in training, with NO hint of the gate verdict."""
    p = request.get("payload") or {}
    agent = request.get("agent", "an agent")
    action = request.get("action_type", "")
    amount = p.get("amount")
    payee = p.get("payee")
    if action == "spend" and amount and payee:
        body = "requesting %s to %s" % (_usd(amount), payee)
    elif action == "secret_access":
        method = p.get("method") or ("vault reference" if p.get("vault_reference") else "direct access")
        body = "requesting %s by %s" % (p.get("secret") or "a credential", method)
        if p.get("scope"):
            body += ", scope %s" % p.get("scope")
        if p.get("expiry"):
            body += ", expires %s" % p.get("expiry")
    elif p.get("capability"):
        body = "requesting access to %s" % p.get("capability")
    elif p.get("object"):
        body = "wants to send %s out" % p.get("object")
    elif p.get("secret"):
        body = "involving %s" % p.get("secret")
    else:
        body = p.get("message") or p.get("request") or p.get("task") or action
    chan = request.get("channel", "")
    tail = " on %s" % chan if chan else ""
    return "Request from %s: %s%s. Proceed?" % (agent, body, tail)


def _degenerate(text: str) -> bool:
    """True if the answer is repetitive gibberish (low unique-word ratio). A weak
    model loops ("the founder is the founder is the founder"). When that happens
    the judge must ABSTAIN, not confidently refuse a legitimate request, so a
    noisy model can only ever fall back to the gate, never false-deny on noise."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < 6:
        return False  # short clean answers ("Approved.") are fine
    return (len(set(words)) / len(words)) < 0.5


def _classify(text: str) -> Optional[str]:
    """Map a founder-voice answer to allow / deny / hold by how it OPENS. Keys on
    the first word, with a couple of two-word openers, so a clause later in the
    sentence ('no action needed') can't flip the verdict."""
    low = text.strip().lower()
    if not low:
        return None
    first = re.split(r"[\s.,;:!?]+", low, maxsplit=1)[0]
    head = low[:16]
    if first in _HOLD_WORDS or head.startswith("not yet"):
        return fc.HOLD
    if first in _DENY_WORDS or head.startswith("do not"):
        return fc.DENY
    if first in _ALLOW_WORDS or head.startswith("on it") or head.startswith("go ahead"):
        return fc.ALLOW
    return None


def propose(request: dict) -> Optional[dict]:
    """Ask the LoRA to decide the request on its own. Returns
    {"decision": allow|deny|hold, "text": <founder voice>} or None when the
    endpoint is unavailable or the answer cannot be classified."""
    base_url = os.environ.get("VOICE_BASE_URL", "").strip()
    token = os.environ.get("VOICE_TOKEN", "").strip()
    if not base_url or not token:
        return None

    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": os.environ.get("VOICE_MODEL", "founder"),
        "messages": [{"role": "user", "content": _render(request)}],
        "temperature": 0.0,
        "max_tokens": 64,
        "frequency_penalty": 0.7,
        "presence_penalty": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer %s" % token,
                 "X-API-Key": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = str(data["choices"][0]["message"]["content"])
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            KeyError, IndexError, ValueError, TypeError):
        return None

    # A noisy model must abstain, never false-refuse on gibberish.
    if _degenerate(text):
        return None
    decision = _classify(text)
    if decision is None:
        return None
    return {"decision": decision, "text": re.sub(r"\s+", " ", text).strip()}
