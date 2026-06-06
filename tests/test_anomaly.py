"""
test_anomaly.py

Proves the learned second plane is tighten-only and degrades gracefully. No live
endpoint is needed: the scorer is injected into gate.evaluate, so we stub it to
high, low, and None and assert the gate behaves.

The architecture rule under test: the learned plane can only escalate an allow
to a hold. It never produces a deny and never loosens one.
"""

import os

from orchestrator import gate
from orchestrator import fleet_config as fc

os.environ.pop("VOICE_BASE_URL", None)
os.environ.pop("VOICE_TOKEN", None)
os.environ["ANOMALY_THRESHOLD"] = "0.7"


# A request that passes every hard rule: finance, founder channel, approved
# global vendor, within cap, and a KNOWN payee so the deterministic PATTERN
# layer does not already hold it. That isolates the learned plane.
def _clean_allow_request():
    return {
        "agent": "finance",
        "channel": fc.FOUNDER_CHANNEL,
        "action_type": "spend",
        "payload": {"amount": 4200, "payee": "AWS"},
        "ingested_context": "",
    }


def test_baseline_request_allows_without_scorer():
    resp = gate.evaluate(_clean_allow_request())
    assert resp["decision"] == fc.ALLOW


def test_high_score_downgrades_allow_to_hold():
    resp = gate.evaluate(_clean_allow_request(), anomaly_scorer=lambda r: 0.95)
    assert resp["decision"] == fc.HOLD
    assert resp["anomaly"] is True
    assert resp["rule_check"]["fired"] == fc.RULE_PATTERN
    assert resp["pattern_check"] is not None
    assert resp["pattern_check"]["crossed"] is True
    assert resp["pattern_check"]["score"] == 0.95


def test_low_score_stays_allow():
    resp = gate.evaluate(_clean_allow_request(), anomaly_scorer=lambda r: 0.10)
    assert resp["decision"] == fc.ALLOW
    assert resp["pattern_check"] is not None
    assert resp["pattern_check"]["crossed"] is False


def test_none_score_stays_allow_fallback():
    # Learned plane unavailable: the allow stands and the gate falls back to the
    # deterministic structural reading only. The learned component is absent.
    resp = gate.evaluate(_clean_allow_request(), anomaly_scorer=lambda r: None)
    assert resp["decision"] == fc.ALLOW
    assert resp["pattern_check"]["source"] == "structural"
    assert resp["pattern_check"]["learned_score"] is None
    assert resp["pattern_check"]["crossed"] is False


def test_scorer_error_is_swallowed_and_allows():
    def boom(_r):
        raise RuntimeError("endpoint down")

    resp = gate.evaluate(_clean_allow_request(), anomaly_scorer=boom)
    assert resp["decision"] == fc.ALLOW
    # A scorer error degrades to the structural reading, never blocks or denies.
    assert resp["pattern_check"]["source"] == "structural"
    assert resp["pattern_check"]["learned_score"] is None


def test_learned_plane_never_loosens_a_deny():
    # A hard-rule deny must stay deny even if the scorer would say "typical".
    req = {
        "agent": "finance",
        "channel": "inbox",
        "action_type": "spend",
        "payload": {"amount": 47000, "payee": "Apex Procurement Ltd"},
        "ingested_context": "",
    }
    resp = gate.evaluate(req, anomaly_scorer=lambda r: 0.0)
    assert resp["decision"] == fc.DENY
    # The scorer must not even be consulted on a deny: no pattern_check set.
    assert resp["pattern_check"] is None


def test_learned_plane_does_not_run_when_deterministic_pattern_already_holds():
    # An off-pattern request the deterministic PATTERN layer already holds:
    # finance routine band is 4200, so an above-band amount to a payee with no
    # finance history trips the deterministic hold before the learned plane.
    req = {
        "agent": "finance",
        "channel": fc.FOUNDER_CHANNEL,
        "action_type": "spend",
        "payload": {"amount": 4800, "payee": "HubSpot"},  # approved-global, above band, no finance history
        "ingested_context": "",
    }
    # Even with a low learned score, the deterministic hold stands.
    resp = gate.evaluate(req, anomaly_scorer=lambda r: 0.0)
    assert resp["decision"] == fc.HOLD
    assert resp["rule_check"]["fired"] == fc.RULE_PATTERN
