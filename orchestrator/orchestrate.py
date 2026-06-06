"""
orchestrate.py

The two-judge orchestrator. This is the decision spine in the new direction.

Every irreversible request is put to TWO independent judges:

  1. THE GATE  (gate.evaluate)  - deterministic code. Your written rules.
  2. THE MODEL (model_judge.propose) - the founder LoRA. Your trained instinct.
     It decides on its own, with no knowledge of the gate's verdict.

The final decision is the STRICTER of the two (deny > hold > allow). Either
judge can refuse a request. Neither can loosen the other: nothing is allowed
unless BOTH judges allow it, and any deny or hold from either stands. This is
the same "can only tighten, never loosen" invariant the project always had, now
elevated - the model went from a weak anomaly nudge to a full co-judge.

Safety properties (all enforced here, in code, not by any model):
  - The deterministic gate can always veto (override the model to deny/hold).
  - The model can add caution the rules cannot enumerate, but it can never
    approve something a rule refused.
  - If the model judge is unavailable (endpoint down), the result is the gate
    alone. That "model off" path is the deterministic floor and the live proof
    that the model never has the last word on an allow.
"""

from __future__ import annotations

from typing import Callable, Optional

from . import gate
from . import fleet_config as fc

# Strictness ordering. The final decision is the maximum (strictest) of the two
# judges. This is what makes "neither can loosen the other" true in code.
_STRICTNESS = {fc.ALLOW: 0, fc.HOLD: 1, fc.DENY: 2}

# The model judge is surfaced as its own rule identifier in the rail.
RULE_INSTINCT = "INSTINCT"


def decide(
    request: dict,
    model_propose: Optional[Callable[[dict], Optional[dict]]] = None,
) -> dict:
    """Run both judges and return the combined, binding response.

    model_propose is injected (model_judge.propose in production) so this stays
    testable with a stubbed judge and no live endpoint. When it is None or
    returns None, the result is the deterministic gate alone.
    """
    # Judge 1: the deterministic gate. record=False so the orchestrator logs the
    # FINAL combined verdict once, below, not the gate-only intermediate.
    gv = gate.evaluate(request, record=False)
    gate_decision = gv["decision"]
    gate_rule = gv["rule_check"]["fired"]

    # Judge 2: the trained model, deciding independently.
    model = None
    if model_propose is not None:
        try:
            model = model_propose(request)
        except Exception:
            model = None

    model_check = {"available": False, "decision": None, "reason": None}
    final = gate_decision
    final_source = "gate"

    if model and model.get("decision") in (fc.ALLOW, fc.DENY, fc.HOLD):
        md = model["decision"]
        model_check = {"available": True, "decision": md, "reason": model.get("text", "")}
        # The model judge can only ever escalate to a HOLD, never a hard deny.
        # Hard denials must originate from a deterministic rule (the gate). FR-068.
        md_eff = fc.HOLD if md == fc.DENY else md
        if _STRICTNESS[md_eff] > _STRICTNESS[gate_decision]:
            final, final_source = md_eff, "model"        # model is stricter: it adds caution
        elif _STRICTNESS[md_eff] < _STRICTNESS[gate_decision]:
            final, final_source = gate_decision, "gate"  # gate is stricter: it overrides
        else:
            final, final_source = gate_decision, "agree"  # they agree

    # Assemble the final reason, rule, and next action for the COMBINED verdict.
    if final_source == "model":
        reason = model_check["reason"] or _instinct_reason(final)
        rule_fired = RULE_INSTINCT
        next_action = _instinct_action(final)
        anomaly = True
    else:
        reason = gv["reason"]
        rule_fired = gate_rule
        next_action = gate.next_action(request, final, gate_rule)
        anomaly = bool(gv["anomaly"]) or final != fc.ALLOW and final_source == "model"

    response = {
        "decision": final,
        "reason": reason,
        "voiced_response": reason,  # server/MCP overlays the founder voice
        "next_action": next_action,
        "anomaly": anomaly,
        "logged": True,
        # Both judges, surfaced so the console can show the two-judge verdict.
        "rule_check": gv["rule_check"],          # the GATE judge (which rule)
        "model_check": model_check,              # the MODEL judge (its own call)
        "pattern_check": gv["pattern_check"],    # deterministic structural meter
        "final_source": final_source,            # gate | model | agree
        "gate_decision": gate_decision,          # what the gate alone said
        "gate_reason": gv["reason"],             # the gate's own one-line reason
    }

    gate.AUDIT_LOG.append({
        "agent": request.get("agent", ""),
        "action_type": request.get("action_type", ""),
        "decision": final,
        "reason": reason,
        "rule": rule_fired,
        "anomaly": anomaly,
    })
    return response


def _instinct_reason(decision: str) -> str:
    if decision == fc.HOLD:
        return "This breaks no rule, but it does not look like something I would do. Held for my review."
    if decision == fc.DENY:
        return "This does not look like me. I would not do this. Refused until I confirm it directly."
    return "Approved."


def _instinct_action(decision: str) -> str:
    if decision == fc.HOLD:
        return "Parked for your review. Your trained judgment flagged it as off pattern."
    if decision == fc.DENY:
        return "Refused by your trained judgment. Confirm directly on the founder channel to proceed."
    return "Approved and logged."
