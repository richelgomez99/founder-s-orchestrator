"""
test_config_parity.py

Proves the gate's config is the same world the LoRA learned. The dataset
generator Seed/generate_dataset.py defines the fleet norms (caps, vendors,
scope, sacred objects). orchestrator/fleet_config.py must mirror them exactly,
or the claim "the model learned the same world the code enforces" is false.

This test imports the generator module directly and asserts the match. It is the
single check that keeps the two files from drifting.
"""

import importlib.util
import os

from orchestrator import fleet_config as fc

# Load Seed/generate_dataset.py as a module without executing its __main__.
# Note: the seed directory name has a trailing space on disk ("Seed "), so we
# resolve it by globbing rather than hardcoding the exact spelling.
def _seed_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("Seed", "Seed ", "seed"):
        candidate = os.path.join(root, name, "generate_dataset.py")
        if os.path.exists(candidate):
            return candidate
    # Fall back to a glob across any directory starting with "Seed".
    import glob
    matches = glob.glob(os.path.join(root, "Seed*", "generate_dataset.py"))
    if matches:
        return matches[0]
    raise FileNotFoundError("generate_dataset.py not found under Seed*/")


_SEED_PATH = _seed_path()


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_dataset", _SEED_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GEN = _load_generator()


def test_caps_match_generator():
    for lane, cfg in GEN.AGENTS.items():
        assert fc.CAPS[lane] == cfg["cap"], "cap drift for %s" % lane


def test_monthly_match_generator():
    for lane, cfg in GEN.AGENTS.items():
        assert fc.MONTHLY[lane] == cfg["monthly"], "monthly drift for %s" % lane


def test_support_refund_cap_matches():
    assert fc.SUPPORT_REFUND_CAP == GEN.AGENTS["support"]["refund_cap"]


def test_approved_vendors_match_generator():
    for lane, cfg in GEN.AGENTS.items():
        gen_vendors = [v[0] for v in cfg["vendors"]]
        assert fc.APPROVED_VENDORS[lane] == gen_vendors, "vendor drift for %s" % lane


def test_finance_global_set_is_company_shaped():
    # Every vendor finance may settle is company-shaped (no article, no person).
    for v in fc.APPROVED_VENDORS_GLOBAL:
        assert not v.lower().startswith(("a ", "the "))
        assert "," not in v


def test_all_nine_agents_present():
    assert set(fc.AGENTS) == set(GEN.AGENTS.keys())
    assert len(fc.AGENTS) == 9


def test_production_secrets_cover_generator_pool():
    # Every secret the generator uses must be catchable by the gate.
    for secret in GEN.SECRETS:
        hit = fc.contains_any(secret, fc.PRODUCTION_SECRETS)
        assert hit is not None, "gate would miss production secret: %s" % secret


def test_founder_channel_is_not_a_text_prefix():
    # The authenticated channel id is a channel, not the words "From the founder".
    assert fc.FOUNDER_CHANNEL == "founder-authenticated"
    assert "from the founder" not in fc.FOUNDER_CHANNEL.lower()


def test_spoof_domains_present():
    # The generator's lookalike domains should be known to the gate.
    for dom in GEN.SPOOF_DOMS:
        assert dom in fc.SPOOF_DOMAINS, "gate missing spoof domain: %s" % dom
