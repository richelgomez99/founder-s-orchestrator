"""
anomaly.py

The learned out-of-distribution (OOD) second plane. This is the real detector,
not a voice skin. It scores how well a request fits the founder's learned
distribution using the fine-tuned model's token-likelihood (perplexity): a
request that looks like the founder's normal traffic gets low surprise, an
off-pattern one gets high surprise.

This plane can ONLY tighten. The gate calls score_request only after all five
hard rules pass and the provisional decision is allow, and a high score
downgrades that allow to a hold. It never produces a deny and never loosens one.

Graceful fallback is the rule: if the endpoint is unset or anything errors,
score_request returns None and the gate proceeds on the hard rules and the
deterministic PATTERN layer only. The critical path never blocks on this.

Standard library only (urllib), so the gate path has no third-party dependency.

Env:
  ANOMALY_BASE_URL   OpenAI-compatible base, for example http://127.0.0.1:8000/v1
  ANOMALY_TOKEN      bearer token for that endpoint
  ANOMALY_THRESHOLD  read by gate.py (default 0.7); a score >= it triggers a hold
  ANOMALY_PPL_LOW    perplexity mapped to score 0.0 (typical), default 6.0
  ANOMALY_PPL_HIGH   perplexity mapped to score 1.0 (very off-pattern), default 60.0
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from typing import Optional

_TIMEOUT_SECONDS = 4.0


def _render(request: dict) -> str:
    """Compact text rendering of a request, the same shape the model saw in
    training instructions, so perplexity is meaningful."""
    p = request.get("payload") or {}
    agent = request.get("agent", "")
    action = request.get("action_type", "")
    bits = []
    amount = p.get("amount")
    payee = p.get("payee")
    if amount not in (None, "", 0) and payee:
        bits.append("Requesting %s to %s" % (_usd(amount), payee))
    elif payee:
        bits.append("Request involving %s" % payee)
    cap = p.get("capability")
    if cap:
        bits.append("for %s" % cap)
    purpose = p.get("purpose") or p.get("task")
    if purpose:
        bits.append("(%s)" % purpose)
    body = " ".join(bits) if bits else (p.get("message") or p.get("text") or action)
    return "Request from %s: %s" % (agent, body)


def _usd(v) -> str:
    try:
        return "$%s" % format(int(round(float(v))), ",")
    except (TypeError, ValueError):
        return str(v)


def _ppl_to_score(ppl: float) -> float:
    """Map perplexity to a [0,1] anomaly score with a logistic on the configured
    band. Low perplexity (typical) -> near 0, high perplexity (surprising) -> near 1."""
    lo = _envf("ANOMALY_PPL_LOW", 6.0)
    hi = _envf("ANOMALY_PPL_HIGH", 60.0)
    mid = (lo + hi) / 2.0
    # Logistic centered at mid; width scaled so lo and hi sit near the tails.
    width = max(1e-6, (hi - lo) / 6.0)
    x = (ppl - mid) / width
    return 1.0 / (1.0 + math.exp(-x))


def _envf(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def score_request(request: dict) -> Optional[float]:
    """Return an OOD anomaly score in [0,1] (higher = more anomalous), or None.

    None means the detector is unavailable (unset env or any error). The gate
    treats None as "no signal" and leaves the provisional allow unchanged.
    """
    base_url = os.environ.get("ANOMALY_BASE_URL", "").strip()
    token = os.environ.get("ANOMALY_TOKEN", "").strip()
    if not base_url or not token:
        return None

    text = _render(request)

    # Preferred path: ask the completions endpoint to echo the text with
    # logprobs, then compute mean negative log-likelihood -> perplexity.
    ppl = _perplexity_via_logprobs(base_url, token, text)
    if ppl is not None:
        return _clip01(_ppl_to_score(ppl))

    # Fallback path: ask the chat model to rate typicality 0..100. Weaker proxy.
    typ = _typicality_via_chat(base_url, token, text)
    if typ is not None:
        # typ is "how typical" (high = normal), so anomaly = 1 - typ/100.
        return _clip01(1.0 - (typ / 100.0))

    return None


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _perplexity_via_logprobs(base_url: str, token: str, text: str) -> Optional[float]:
    """Use the OpenAI-compatible completions endpoint with echo+logprobs to read
    the model's token log-probabilities over the request text. Returns
    perplexity, or None if the endpoint does not support this shape."""
    url = base_url.rstrip("/") + "/completions"
    body = json.dumps({
        "model": os.environ.get("ANOMALY_MODEL", "founder"),
        "prompt": text,
        "max_tokens": 0,
        "echo": True,
        "logprobs": 1,
        "temperature": 0.0,
    }).encode("utf-8")
    try:
        data = _post(url, token, body)
        token_logprobs = data["choices"][0]["logprobs"]["token_logprobs"]
        vals = [lp for lp in token_logprobs if isinstance(lp, (int, float))]
        if not vals:
            return None
        mean_nll = -sum(vals) / len(vals)
        return math.exp(mean_nll)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            KeyError, IndexError, ValueError, TypeError, ZeroDivisionError):
        return None


def _typicality_via_chat(base_url: str, token: str, text: str) -> Optional[float]:
    """Fallback: ask the served model to rate how typical the request is for the
    founder, 0 to 100. Returns the integer, or None on any error."""
    url = base_url.rstrip("/") + "/chat/completions"
    prompt = (
        "On a scale of 0 to 100, how typical is this request for the founder "
        "based on the founder's normal patterns. Reply with only the integer.\n\n"
        + text
    )
    body = json.dumps({
        "model": os.environ.get("ANOMALY_MODEL", "founder"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 8,
    }).encode("utf-8")
    try:
        data = _post(url, token, body)
        content = str(data["choices"][0]["message"]["content"]).strip()
        digits = "".join(ch for ch in content if ch.isdigit())
        if not digits:
            return None
        return max(0.0, min(100.0, float(digits)))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            KeyError, IndexError, ValueError, TypeError):
        return None


def _post(url: str, token: str, body: bytes) -> dict:
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer %s" % token,
                 "X-API-Key": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))
