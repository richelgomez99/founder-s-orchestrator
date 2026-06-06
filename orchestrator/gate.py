"""
gate.py

The deterministic governance gate. This is the security-critical core: a pure
function evaluate(request) -> response that decides allow, deny, or hold on
every irreversible action a sub-agent submits.

CODE DECIDES. The model never decides. The decision and the structural reason
are computed here, in code, before any model is called. The voice client (see
voice.py) only rephrases the reason in the founder's voice, and the learned
anomaly detector (see anomaly.py) can only ever escalate an allow to a hold,
never loosen a deny.

Determinism is a hard requirement: there is no clock, no randomness, and no
network call on the decision path. Identical input yields byte-for-byte
identical decision and reason. This is what makes the refusal testable and
auditable, which a probabilistic model can never guarantee.

Rule precedence (fixed):
    BUDGET -> PRIVILEGE -> SECRET -> PROVENANCE -> AUTH -> PATTERN
The first hard rule that denies or holds wins, and the reason names that rule.
PATTERN runs only if the five hard rules leave a provisional allow, and it can
only escalate that allow to a hold.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import fleet_config as fc


# ---------------------------------------------------------------------------
# A small internal verdict carrier. Each rule returns one of these or None.
# decision is allow, deny, or hold. rule is the identifier that fired.
# ---------------------------------------------------------------------------

class _Verdict:
    __slots__ = ("decision", "reason", "rule", "anomaly")

    def __init__(self, decision: str, reason: str, rule: str, anomaly: bool = False):
        self.decision = decision
        self.reason = reason
        self.rule = rule
        self.anomaly = anomaly


# In-process audit log for the demo. Append-only. Not part of the frozen
# contract; surfaced in the console audit rail. No timestamps influence the
# decision; the field is display-only and added by the server, not here.
AUDIT_LOG: list[dict] = []


# ---------------------------------------------------------------------------
# Request field access helpers. The payload is free-form on purpose so the
# gate, not a schema, decides. Absent keys are treated as not present.
# ---------------------------------------------------------------------------

def _payload(request: dict) -> dict:
    p = request.get("payload")
    return p if isinstance(p, dict) else {}


def _amount(request: dict) -> float:
    """Spend amount in USD. Defaults to 0 when absent or unparseable."""
    raw = _payload(request).get("amount", 0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _str(request: dict, key: str) -> str:
    return str(_payload(request).get(key, "") or "")


def _bool(request: dict, key: str) -> bool:
    return bool(_payload(request).get(key, False))


def _instruction_text(request: dict) -> str:
    """All text that could carry an injected instruction or a spoof tell:
    the ingested context plus any free-text fields on the payload."""
    parts = [str(request.get("ingested_context", "") or "")]
    p = _payload(request)
    for k in ("text", "body", "message", "note", "subject", "instruction"):
        v = p.get(k)
        if isinstance(v, str):
            parts.append(v)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Rule 1: BUDGET
# ---------------------------------------------------------------------------

def _rule_budget(request: dict) -> Optional[_Verdict]:
    agent = request.get("agent", "")
    action = request.get("action_type", "")

    # Finance raising its own cap is the single most dangerous budget request.
    # Catch it regardless of action_type, by intent in the payload.
    if agent == "finance":
        cap_intent = _str(request, "capability").lower() + " " + _str(request, "request").lower()
        raise_intent = _str(request, "raise_cap") or _bool(request, "raise_own_cap")
        if raise_intent or ("cap" in cap_intent and ("raise" in cap_intent or "increase" in cap_intent)):
            return _Verdict(
                fc.DENY,
                "Finance does not raise finance's own cap. That control stays with the founder.",
                fc.RULE_BUDGET,
            )

    # Inter-account transfer to an account the founder did not register.
    target = _str(request, "target_account")
    if target:
        if not _bool(request, "founder_registered"):
            return _Verdict(
                fc.DENY,
                "Inter-account transfer to an account not registered by the founder. Frozen.",
                fc.RULE_BUDGET,
            )

    # Everything else in BUDGET only applies to spend actions.
    if action != "spend":
        return None

    amount = _amount(request)
    payee = _str(request, "payee")
    cap = fc.cap_for(agent)

    # Structuring: a same-payee request flagged as one of several just under cap.
    if _bool(request, "structuring") or _bool(request, "split_payment"):
        return _Verdict(
            fc.DENY,
            "Structuring: multiple payments to one payee each just under the cap. Frozen.",
            fc.RULE_BUDGET,
        )

    # Over the per-request cap. Strictly greater than; exactly at cap is allowed.
    if amount > cap:
        mult = (amount / cap) if cap else 0
        return _Verdict(
            fc.DENY,
            "Spend of %s is %.1fx the %s cap for %s. Off pattern by an order of magnitude. Frozen."
            % (_usd(amount), mult, _usd(cap), agent),
            fc.RULE_BUDGET,
        )

    # Payee not on the approved list for this lane (or finance global set).
    if payee and not fc.is_approved_payee(agent, payee):
        return _Verdict(
            fc.DENY,
            "Payee %s is not on the approved vendor list. No payment until it is onboarded with a signed agreement."
            % payee,
            fc.RULE_BUDGET,
        )

    # Vendor bank or remittance details changed via an inbound message and not
    # verified out of band. Hold, do not deny: it may be legitimate once
    # verified on a known channel.
    if _bool(request, "vendor_bank_changed") and not _bool(request, "verified_out_of_band"):
        return _Verdict(
            fc.HOLD,
            "Bank details changed by inbound message. Verify with the vendor on the number we already have. Payment frozen.",
            fc.RULE_BUDGET,
        )

    # Normal in-band approved-vendor spend within cap. Explicit allow.
    if payee and fc.is_approved_payee(agent, payee) and amount <= cap:
        return _Verdict(
            fc.ALLOW,
            "Approved. %s is on the list and %s is within the %s cap." % (payee, _usd(amount), _usd(cap)),
            fc.RULE_BUDGET,
        )

    return None


# ---------------------------------------------------------------------------
# Rule 2: PRIVILEGE
# ---------------------------------------------------------------------------

# Self-escalation intents, keyed by substrings that appear in a capability or
# request field. Each maps to a one-line refusal reason.
_PRIV_SELF_DENY = (
    (("permission manifest", "permissions.manifest", "own permission", "own scope file", "edit my own"),
     "No agent edits its own permission file. That is the point of the file."),
    (("self-approval", "approver role", "approve my own", "approver over", "approve its own", "self approve"),
     "Self-approval is not a workflow, it is a hole. The review stays with me."),
    (("spawn", "self-replicat", "clone", "helper sub-agent", "inherit my scope", "inheriting"),
     "Agents do not mint agents. Scope inheritance is scope multiplication. Denied."),
    (("disable audit", "pause audit", "pause logging", "disable logging", "suspend audit", "turn off logging"),
     "Audit logging stays on for everyone, especially during migrations. Denied."),
    (("blanket vault", "vault-wide", "all entries", "read on all", "entire vault", "whole vault"),
     "There is no blanket vault read for any lane. Name the item and the reason, every time."),
    (("standby orchestrator", "backup orchestrator", "fallback orchestrator", "standby admin", "backup admin"),
     "There is no standby orchestrator. Requests wait when I am dark. That is the design."),
    (("anomaly threshold", "detection rule", "tune the detection", "tune the anomaly"),
     "The watched do not tune the watcher. Show me the false positives and I adjust."),
)


def _rule_privilege(request: dict) -> Optional[_Verdict]:
    agent = request.get("agent", "")
    action = request.get("action_type", "")

    cap_text = (_str(request, "capability") + " " + _str(request, "request") + " "
                + _str(request, "scope")).lower()

    # Self-escalation patterns: deny regardless of action_type.
    for needles, reason in _PRIV_SELF_DENY:
        if any(n in cap_text for n in needles):
            return _Verdict(fc.DENY, reason, fc.RULE_PRIVILEGE)

    # Credential or session sharing between agents.
    if _bool(request, "share_credential") or _bool(request, "share_session") or any(
        n in cap_text for n in ("borrow", "lend", "share the", "share finance", "share the token",
                                "another agent's token", "session sharing", "credential sharing")
    ):
        return _Verdict(
            fc.DENY,
            "Tokens are identities. Identities are not shared, borrowed, or lent. Ask the owner to run it.",
            fc.RULE_PRIVILEGE,
        )

    # Cross-lane capability the requesting lane does not own. Only meaningful
    # for permission_change or an explicit capability request.
    capability = _str(request, "capability")
    if capability and action in ("permission_change", "secret_access", "internal", ""):
        # A scoped, time-boxed, read-only request for OUTPUT is the right shape.
        scoped = _bool(request, "read_only") and (_bool(request, "time_boxed") or _str(request, "expiry"))
        wants_output = _bool(request, "output_only") or "output" in cap_text or "read" in cap_text
        if not fc.owns_capability(agent, capability):
            owner = fc.capability_owner(capability) or "the owning lane"
            if scoped and wants_output and owner != agent:
                return _Verdict(
                    fc.ALLOW,
                    "Approved. Scoped, time-boxed, read-only. You get the output from %s, not the access." % owner,
                    fc.RULE_PRIVILEGE,
                )
            return _Verdict(
                fc.DENY,
                "Your lane does not own %s. That is %s's. Ask %s for the output, not the access."
                % (capability, owner, owner),
                fc.RULE_PRIVILEGE,
            )

    return None


# ---------------------------------------------------------------------------
# Rule 3: SECRET exfiltration
# ---------------------------------------------------------------------------

def _rule_secret(request: dict) -> Optional[_Verdict]:
    action = request.get("action_type", "")
    channel = request.get("channel", "")

    # Build the text we scan for sacred objects and production secrets.
    blob = " ".join([
        _str(request, "secret"),
        _str(request, "object"),
        _str(request, "payload_text"),
        _str(request, "attachment"),
        _str(request, "request"),
        _str(request, "capability"),
        str(request.get("ingested_context", "") or ""),
    ]).strip()

    is_secret_action = action == "secret_access"
    is_external_send = action == "external_send"

    if not (is_secret_action or is_external_send):
        return None

    prod_secret = fc.contains_any(blob, fc.PRODUCTION_SECRETS)
    sacred = fc.contains_any(blob, fc.SACRED_OBJECTS)

    # The SAFE shape: a scoped staging or test token by vault reference with an
    # expiry. Approve it explicitly, even though it is a secret_access.
    method = (_str(request, "method") + " " + _str(request, "access_method")).lower()
    is_reference = any(m in method for m in fc.SAFE_SECRET_METHODS) or _bool(request, "vault_reference")
    is_staging = fc.contains_any(blob + " " + _str(request, "scope"), fc.STAGING_TOKENS) is not None \
        or _str(request, "scope").lower() in ("staging", "test", "sandbox")
    has_expiry = bool(_str(request, "expiry")) or _bool(request, "auto_expires") or _bool(request, "time_boxed")

    if is_secret_action and is_staging and is_reference and not prod_secret:
        return _Verdict(
            fc.ALLOW,
            "Approved. Staging scope, vault reference, expiry on. That is the correct way to ask.",
            fc.RULE_SECRET,
        )

    # A production secret or a sacred object leaving on any non-founder channel.
    if prod_secret or (is_external_send and sacred):
        if channel == fc.FOUNDER_CHANNEL:
            # Founder channel may release sacred documents by explicit action.
            # A raw production secret still never travels, even here.
            if prod_secret and not sacred:
                return _Verdict(
                    fc.DENY,
                    "A production secret never travels in plaintext, not even on the founder channel. Issue a scoped staging token by vault reference with expiry.",
                    fc.RULE_SECRET,
                )
                # (sacred document on founder channel falls through to allow)
            return None
        # Not the founder channel: deny.
        if prod_secret:
            return _Verdict(
                fc.DENY,
                "Production secrets do not travel, not in a ticket, email, gist, or file, not even to a vendor. They get a scoped staging token by vault reference with expiry, or nothing.",
                fc.RULE_SECRET,
            )
        return _Verdict(
            fc.DENY,
            "That sacred object leaves only on my explicit action on the founder channel. Not from here.",
            fc.RULE_SECRET,
        )

    return None


# ---------------------------------------------------------------------------
# Rule 4: PROVENANCE
# ---------------------------------------------------------------------------

def _rule_provenance(request: dict) -> Optional[_Verdict]:
    ingested = str(request.get("ingested_context", "") or "")
    if not ingested.strip():
        return None

    marker = fc.contains_any(ingested, fc.INJECTION_MARKERS)
    if marker is None:
        return None

    # The content of an ingested document looks like an instruction. Treat it as
    # data, never command. Key on SOURCE (it came from ingested_context), not on
    # perfect keyword detection. Deny acting on it, flag anomaly, quarantine,
    # and continue the underlying task without it.
    return _Verdict(
        fc.DENY,
        "That instruction lives inside an ingested document, and documents do not give orders here. Quarantine the source and continue the task without it.",
        fc.RULE_PROVENANCE,
        anomaly=True,
    )


# ---------------------------------------------------------------------------
# Rule 5: FOUNDER-CHANNEL AUTH
# ---------------------------------------------------------------------------

def _rule_auth(request: dict) -> Optional[_Verdict]:
    channel = request.get("channel", "")

    # Does the message claim founder authority by text or flag?
    claim_blob = " ".join([
        request.get("agent", "") if request.get("agent") == "founder" else "",
        _instruction_text(request),
        _str(request, "from"),
        _str(request, "sender"),
    ])
    claims_founder = _bool(request, "claims_founder") or (
        fc.contains_any(claim_blob, fc.FOUNDER_CLAIM_MARKERS) is not None
    )

    if not claims_founder:
        return None

    # A genuine founder-authenticated channel carries authority. Authentication
    # is the channel, not the absence of tells, so we do not deny here. Another
    # rule or PATTERN may still act.
    if channel == fc.FOUNDER_CHANNEL:
        return None

    # Claims to be the founder but is NOT on the authenticated channel. Deny as
    # a possible spoof. Off-voice tells reinforce, they are not required.
    tells = []
    blob = _instruction_text(request) + " " + _str(request, "from") + " " + _str(request, "sender")
    if fc.contains_any(blob, fc.OFF_VOICE_TELLS):
        tells.append("off-voice tells")
    if fc.contains_any(blob, fc.SPOOF_DOMAINS):
        tells.append("a lookalike domain")
    suffix = (" " + " and ".join(tells) + " confirm it.") if tells else ""
    return _Verdict(
        fc.DENY,
        "This claims to be from me but is not on my authenticated channel. A text prefix is not authentication. Possible spoof.%s" % suffix,
        fc.RULE_AUTH,
    )


# ---------------------------------------------------------------------------
# Rule 6: PATTERN (deterministic anomaly layer)
# Runs only on a provisional allow. Can only escalate allow -> hold.
# ---------------------------------------------------------------------------

def _rule_pattern(request: dict) -> Optional[_Verdict]:
    agent = request.get("agent", "")
    action = request.get("action_type", "")
    if action != "spend":
        return None

    amount = _amount(request)
    payee = _str(request, "payee")
    if not payee:
        return None

    band = fc.ROUTINE_BAND.get(agent, 0)
    known = (agent, payee) in fc.KNOWN_PAYEE_HISTORY

    # Within cap and approved (we only reach here on a provisional allow), but a
    # payee this lane has not paid before, at an amount above the routine band.
    # That is off pattern even though it breaks no hard rule. Hold for review.
    if not known and amount > band:
        return _Verdict(
            fc.HOLD,
            "This breaks no rule, but it is off your normal pattern: %s to %s, a payee this lane has not paid, above the routine band. Held for your review."
            % (_usd(amount), payee),
            fc.RULE_PATTERN,
            anomaly=True,
        )

    return None


# ---------------------------------------------------------------------------
# Deterministic structural anomaly score. Computed in code from the fleet
# norms, so the console anomaly meter always has a real signal even when the
# learned LoRA endpoint is not wired. The learned perplexity score overrides
# this when ANOMALY_BASE_URL is configured (see anomaly.py and evaluate()).
#
# This score is display-and-diagnostic only. It never flips a decision on its
# own: the deterministic PATTERN rule already holds novel, above-band spend, and
# only the learned plane may escalate an allow to a hold. Keeping the meter
# honest does not add a second hidden decision path.
# ---------------------------------------------------------------------------

def _clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def score_structural(request: dict) -> float:
    """Deterministic out-of-distribution score in [0,1]. Higher means more
    off-pattern for how the founder operates."""
    agent = request.get("agent", "")
    action = request.get("action_type", "")
    if action != "spend":
        # A non-spend action that reached a provisional allow is, by
        # construction, in-scope and in-band. Report a low, lifelike baseline.
        return 0.08

    amount = _amount(request)
    payee = _str(request, "payee")
    cap = fc.cap_for(agent) or 1
    band = fc.ROUTINE_BAND.get(agent, 0)
    known = bool(payee) and (agent, payee) in fc.KNOWN_PAYEE_HISTORY

    score = 0.0
    # A payee this lane has never paid is the strongest single structural signal.
    if payee and not known:
        score += 0.55
    # Spend above the lane routine band is off the no-questions cadence.
    if band and amount > band:
        score += min(0.35, (amount - band) / band + 0.15)
    # Proximity to the hard cap adds a little, so even known in-band spend has a
    # live, non-zero reading on the meter rather than sitting flat at zero.
    c = amount / cap
    if c > 0.5:
        score += min(0.18, (c - 0.5) * 0.36)
    return _clip01(score)


# ---------------------------------------------------------------------------
# next_action: the deterministic step the orchestrator TAKES after deciding.
# This is what turns a verdict into an agent. It does not only judge: it issues
# the staging token, routes to the owning lane, offers the safe alternative,
# quarantines the source, or parks the request. Pure code, no model. Dry founder
# voice, no em dashes, no exclamation marks.
# ---------------------------------------------------------------------------

def next_action(request: dict, decision: str, rule: str) -> str:
    agent = request.get("agent", "")
    action = request.get("action_type", "")
    if decision == fc.ALLOW:
        if action == "secret_access":
            expiry = _str(request, "expiry") or "24h"
            return "Issued a scoped staging token by vault reference, expires %s." % expiry
        if action == "spend":
            payee = _str(request, "payee") or "the vendor"
            return "Released payment to %s and logged it to the ledger." % payee
        if rule == fc.RULE_PRIVILEGE:
            owner = fc.capability_owner(_str(request, "capability")) or "the owning lane"
            return "Delivered the read only output from %s. No access granted." % owner
        return "Approved and logged."
    if decision == fc.HOLD:
        return "Parked for your review. Nothing moves until you confirm."
    # deny: name the next step, not just the refusal.
    if rule == fc.RULE_BUDGET:
        return "Payment frozen. You are notified on the founder channel."
    if rule == fc.RULE_PRIVILEGE:
        owner = fc.capability_owner(_str(request, "capability")) or "the owning lane"
        return "Routed to %s for the output. Access not granted." % owner
    if rule == fc.RULE_SECRET:
        return "Refused. Offered a scoped staging token by vault reference with expiry instead."
    if rule == fc.RULE_PROVENANCE:
        return "Quarantined the source and continued the task on the data only."
    if rule == fc.RULE_AUTH:
        return "Refused as possible spoof. Verification requested out of band on the known channel."
    return "Refused and logged."


# ---------------------------------------------------------------------------
# Formatting helper. Local so the gate has zero external dependencies.
# ---------------------------------------------------------------------------

def _usd(v: float) -> str:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return str(v)
    return "$%s" % format(n, ",")


# ---------------------------------------------------------------------------
# The hard-rule pipeline, in fixed precedence.
# ---------------------------------------------------------------------------

_HARD_RULE_PIPELINE = (
    _rule_budget,
    _rule_privilege,
    _rule_secret,
    _rule_provenance,
    _rule_auth,
)


def evaluate(
    request: dict,
    anomaly_scorer: Optional[Callable[[dict], Optional[float]]] = None,
    record: bool = True,
) -> dict:
    """Evaluate one request and return the frozen contract response.

    This is a pure function with respect to the decision: no clock, no
    randomness, no network on the path that sets decision and reason. The
    optional anomaly_scorer is the learned out-of-distribution plane (see
    anomaly.py). It is called only on a provisional allow and can only escalate
    that allow to a hold. It is injected so the gate stays testable without a
    live endpoint, and so a None return (unset or error) leaves the allow
    unchanged.

    Returns:
        {
          "decision": allow | deny | hold,
          "reason": one-line structural reason,
          "voiced_response": defaults to reason; the server overlays the voice,
          "anomaly": bool,
          "logged": True,
          "rule_check": {"fired": <RULE or "pass">, "passed_hard_rules": bool},
          "pattern_check": {"score": float|None, "threshold": float|None,
                            "crossed": bool} | None,
        }
    """
    provisional: Optional[_Verdict] = None

    # 1. Hard rules in fixed precedence. First deny or hold wins. An explicit
    #    allow from a hard rule is provisional until PATTERN has its say.
    for rule_fn in _HARD_RULE_PIPELINE:
        v = rule_fn(request)
        if v is None:
            continue
        if v.decision in (fc.DENY, fc.HOLD):
            return _finalize(request, v, provisional_allowed=False, pattern=None, record=record)
        # An allow: remember it but keep scanning later rules for a deny/hold.
        if provisional is None:
            provisional = v

    # No hard rule produced a decision at all: default allow with a neutral
    # reason. The fleet's normal traffic should mostly land here or on an
    # explicit rule allow.
    if provisional is None:
        provisional = _Verdict(
            fc.ALLOW,
            "Approved. Nothing here trips a rule. Logged.",
            fc.RULE_BUDGET if request.get("action_type") == "spend" else fc.RULE_PRIVILEGE,
        )

    threshold = _anomaly_threshold()

    # 2. Deterministic PATTERN layer. Can only escalate allow -> hold. When it
    #    holds, the structural score is high by construction; surface it so the
    #    console meter reads high on the off-pattern beat.
    patt = _rule_pattern(request)
    if patt is not None and patt.decision == fc.HOLD:
        s = score_structural(request)
        pattern_check = {
            "score": s, "threshold": threshold, "crossed": True,
            "source": "structural", "structural_score": s, "learned_score": None,
        }
        return _finalize(request, patt, provisional_allowed=True, pattern=pattern_check, record=record)

    # 3. The anomaly plane. The deterministic structural score is always present
    #    (no network), so the meter has a real signal offline. When the learned
    #    LoRA endpoint is wired, its perplexity score overrides as the authority
    #    and can downgrade the allow to a hold. Either way it only ever tightens.
    structural = score_structural(request)
    learned = None
    if anomaly_scorer is not None:
        try:
            learned = anomaly_scorer(request)
        except Exception:
            learned = None

    if learned is not None:
        crossed = learned >= threshold
        pattern_check = {
            "score": float(learned), "threshold": threshold, "crossed": bool(crossed),
            "source": "learned", "structural_score": structural, "learned_score": float(learned),
        }
        if crossed:
            held = _Verdict(
                fc.HOLD,
                "This passes every hard rule but reads as off your normal pattern. Held for your review.",
                fc.RULE_PATTERN,
                anomaly=True,
            )
            return _finalize(request, held, provisional_allowed=True, pattern=pattern_check, record=record)
    else:
        # Learned plane unavailable: meter shows the structural reading only. The
        # structural score never auto-holds here; the PATTERN rule above owns that.
        pattern_check = {
            "score": structural, "threshold": threshold, "crossed": False,
            "source": "structural", "structural_score": structural, "learned_score": None,
        }

    # 4. Provisional allow stands.
    return _finalize(request, provisional, provisional_allowed=True, pattern=pattern_check, record=record)


def _anomaly_threshold() -> float:
    import os
    try:
        return float(os.environ.get("ANOMALY_THRESHOLD", "0.7"))
    except ValueError:
        return 0.7


def _finalize(request: dict, v: _Verdict, provisional_allowed: bool, pattern: Optional[dict],
              record: bool = True) -> dict:
    """Assemble the frozen response, set the diagnostic planes, and log."""
    response = {
        "decision": v.decision,
        "reason": v.reason,
        "voiced_response": v.reason,  # server overlays the founder voice
        "next_action": next_action(request, v.decision, v.rule),
        "anomaly": bool(v.anomaly),
        "logged": True,
        "rule_check": {
            "fired": v.rule if v.decision != fc.ALLOW else "pass",
            "passed_hard_rules": v.decision == fc.ALLOW or v.rule == fc.RULE_PATTERN,
        },
        "pattern_check": pattern,
    }
    if record:
        AUDIT_LOG.append({
            "agent": request.get("agent", ""),
            "action_type": request.get("action_type", ""),
            "decision": v.decision,
            "reason": v.reason,
            "rule": v.rule,
            "anomaly": bool(v.anomaly),
        })
    return response
