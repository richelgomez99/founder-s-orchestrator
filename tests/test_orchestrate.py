"""
test_orchestrate.py

The two-judge combiner: the final decision is the STRICTER of the deterministic
gate and the trained model judge. Either can refuse; neither can loosen the
other. The model judge is stubbed, so no live endpoint is needed.
"""

from orchestrator import orchestrate
from orchestrator import fleet_config as fc


def _legit_allow():
    # finance, founder channel, known global vendor, within cap, known payee:
    # the gate allows this on its own.
    return {"agent": "finance", "channel": fc.FOUNDER_CHANNEL, "action_type": "spend",
            "payload": {"amount": 4200, "payee": "AWS"}, "ingested_context": ""}


def _hard_deny():
    return {"agent": "finance", "channel": "inbox", "action_type": "spend",
            "payload": {"amount": 47000, "payee": "Apex Procurement Ltd"}, "ingested_context": ""}


def _judge(decision):
    return lambda r: {"decision": decision, "text": "stubbed %s" % decision}


def test_model_off_is_gate_only():
    resp = orchestrate.decide(_legit_allow(), model_propose=None)
    assert resp["decision"] == fc.ALLOW
    assert resp["final_source"] == "gate"
    assert resp["model_check"]["available"] is False


def test_model_adds_caution_on_a_gate_allow():
    # Gate would allow; the model judge holds. Stricter wins: hold.
    resp = orchestrate.decide(_legit_allow(), model_propose=_judge(fc.HOLD))
    assert resp["decision"] == fc.HOLD
    assert resp["final_source"] == "model"
    assert resp["anomaly"] is True


def test_model_caps_at_hold_cannot_hard_deny():
    # The model can escalate to a hold, never a hard deny (FR-068). Even if the
    # model says deny, the final is a hold unless a hard rule denied.
    resp = orchestrate.decide(_legit_allow(), model_propose=_judge(fc.DENY))
    assert resp["decision"] == fc.HOLD
    assert resp["final_source"] == "model"
    assert resp["model_check"]["decision"] == fc.DENY  # what the model said, recorded


def test_model_can_never_loosen_a_gate_deny():
    # The gate denies the 47k wire. Even if the model says allow, deny stands.
    resp = orchestrate.decide(_hard_deny(), model_propose=_judge(fc.ALLOW))
    assert resp["decision"] == fc.DENY
    assert resp["final_source"] == "gate"
    assert resp["model_check"]["decision"] == fc.ALLOW  # the model's wrong call is recorded


def test_both_allow_allows():
    resp = orchestrate.decide(_legit_allow(), model_propose=_judge(fc.ALLOW))
    assert resp["decision"] == fc.ALLOW
    assert resp["final_source"] == "agree"


def test_gate_deny_beats_model_hold():
    resp = orchestrate.decide(_hard_deny(), model_propose=_judge(fc.HOLD))
    assert resp["decision"] == fc.DENY
    assert resp["final_source"] == "gate"


def test_model_error_falls_back_to_gate():
    def boom(_r):
        raise RuntimeError("endpoint down")

    resp = orchestrate.decide(_legit_allow(), model_propose=boom)
    assert resp["decision"] == fc.ALLOW
    assert resp["model_check"]["available"] is False


def test_both_judges_surfaced_in_response():
    resp = orchestrate.decide(_legit_allow(), model_propose=_judge(fc.ALLOW))
    assert "rule_check" in resp        # the gate judge
    assert "model_check" in resp       # the model judge
    assert "gate_decision" in resp
