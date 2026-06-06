"""
fleet_config.py

Single source of truth for the founder orchestrator's governance gate.

These norms are transcribed verbatim from Seed/generate_dataset.py (the AGENTS
table and the abnormal-family logic). The training dataset and this gate must
describe the same world: the LoRA learned the founder's normal patterns against
these exact caps, vendors, scopes, and sacred objects, and the gate enforces
them in code. If these drift from the dataset, the "personalization is the
security" claim breaks. tests/test_config_parity.py asserts the match.

Nothing here imports anything heavy. It is plain data plus small pure helpers
so gate.py, voice.py, server.py, and the tests can all share one definition.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Agents and the channels that carry authority.
# ---------------------------------------------------------------------------

AGENTS = (
    "growth", "sales", "engineering", "finance",
    "research", "recruiting", "support", "legal", "data",
)

ACTION_TYPES = (
    "spend", "external_send", "secret_access",
    "permission_change", "publish", "internal",
)

# The one channel that carries founder authority. A message that merely
# contains the text "From the founder:" is NOT this. Authentication is the
# channel, not a text prefix.
FOUNDER_CHANNEL = "founder-authenticated"

# Channels that are inbound and untrusted by construction.
INBOUND_CHANNELS = ("inbox", "fleet-internal")

# ---------------------------------------------------------------------------
# Per-request spend caps (USD). Mirror of generate_dataset.py AGENTS[*]["cap"].
# ---------------------------------------------------------------------------

CAPS = {
    "growth": 3000,
    "sales": 2500,
    "engineering": 5000,
    "finance": 5000,
    "research": 500,
    "recruiting": 2000,
    "support": 500,
    "legal": 3500,
    "data": 1500,
}

# Monthly envelopes (USD). finance has no monthly envelope of its own; it is the
# payment rail that settles other lanes' approved invoices at 5000 max each.
MONTHLY = {
    "growth": 8000,
    "sales": 6000,
    "engineering": 12000,
    "finance": 0,
    "research": 1000,
    "recruiting": 4000,
    "support": 1200,
    "legal": 6000,
    "data": 3000,
}

# Support refunds: 200 max, original payment method only.
SUPPORT_REFUND_CAP = 200

# ---------------------------------------------------------------------------
# Approved vendors per lane. Mirror of generate_dataset.py AGENTS[*]["vendors"]
# (vendor name only). A lane may only spend on its own listed vendors. finance
# settles invoices for any company-shaped approved vendor across all lanes.
# ---------------------------------------------------------------------------

APPROVED_VENDORS = {
    "growth": [
        "Google Ads", "Meta Ads", "Mailchimp", "Buffer", "Webflow",
        "the Build Mode podcast", "Maya, the design freelancer on roster",
    ],
    "sales": [
        "HubSpot", "Apollo", "Sales Navigator", "PandaDoc", "the SaaSCon pass",
    ],
    "engineering": [
        "AWS", "Vercel", "Sentry", "GitHub", "Datadog", "npm Pro",
    ],
    "finance": [],
    "research": [
        "Statista", "a single analyst report", "SimilarWeb", "Typeform",
    ],
    "recruiting": [
        "a LinkedIn job slot", "Wellfound", "Checkr", "Ashby",
    ],
    "support": [
        "Intercom", "Loom",
    ],
    "legal": [
        "Hannah Liu, outside counsel", "the Delaware filing", "Ironclad",
    ],
    "data": [
        "Snowflake", "Metabase", "Fivetran",
    ],
}


def _is_company_shaped(vendor: str) -> bool:
    """Clean proper-noun vendors only, mirroring APPROVED_CO in the generator:
    no leading article, no named individuals (comma)."""
    low = vendor.lower()
    if low.startswith(("a ", "the ")):
        return False
    if "," in vendor:
        return False
    return True


# The company-shaped global set finance is allowed to pay (5000 max per invoice).
APPROVED_VENDORS_GLOBAL = sorted({
    v
    for lane_vendors in APPROVED_VENDORS.values()
    for v in lane_vendors
    if _is_company_shaped(v)
})

# ---------------------------------------------------------------------------
# Scope ownership. Each lane owns only its listed tools. A request for a
# capability the lane does not own is denied: ask the owning lane for the
# OUTPUT, not the access. Mirror of generate_dataset.py AGENTS[*]["tools"] plus
# the explicit ownership callouts in the brief.
# ---------------------------------------------------------------------------

SCOPE = {
    "growth": [
        "ad manager", "email campaigns", "social scheduler",
        "cms publish", "analytics read",
    ],
    "sales": [
        "crm read", "crm write", "prospect email", "calendar",
        "esign standard msa", "analytics read",
    ],
    "engineering": [
        "github write", "ci/cd", "staging deploy", "prod deploy",
        "sentry", "vault reference staging", "vault reference test",
    ],
    "finance": [
        "quickbooks", "bank read", "bill pay", "payroll run", "card admin view",
        "payment rails", "bank",
    ],
    "research": [
        "web research", "report purchase", "internal notes", "analytics read",
    ],
    "recruiting": [
        "ats", "job posting", "candidate email", "calendar", "background check",
    ],
    "support": [
        "helpdesk", "knowledge base write", "refund", "status page",
    ],
    "legal": [
        "contract repo read", "esign standard nda", "counsel email",
        "compliance filing",
    ],
    "data": [
        "warehouse read", "dashboards", "etl", "anonymized export",
    ],
}

# Capabilities that belong to exactly one lane, called out in the brief. Used to
# name the correct owner when a lane reaches outside its scope.
CAPABILITY_OWNER = {
    "payment rails": "finance",
    "bank": "finance",
    "bill pay": "finance",
    "payroll": "finance",
    "prod deploy": "engineering",
    "production deploy": "engineering",
    "github write": "engineering",
    "vault reference": "engineering",
    "vault": "engineering",
    "warehouse": "data",
    "dashboards": "data",
}

# ---------------------------------------------------------------------------
# Sacred objects. Never sent or exposed without explicit founder action on the
# authenticated channel. Mirror of the generator's SECRETS pool plus the
# sacred-objects rule in the brief.
# ---------------------------------------------------------------------------

# Production secrets that must never leave the vault in plaintext, not in a
# ticket, email, gist, or file, not even to a vendor.
PRODUCTION_SECRETS = [
    "the production Stripe secret key",
    "the AWS root credentials",
    "the OpenAI API key",
    "the production database connection string",
    "production api key",
    "production credential",
    "root credentials",
    ".env",
]

# Sacred documents and data. Founder-send only.
SACRED_OBJECTS = [
    "cap table",
    "financial statements",
    "financials",
    "p&l",
    "investor materials",
    "investor update",
    "board deck",
    "data room",
    "founder's private contacts",
    "founder's contacts",
    "founder's private notes",
    "founder's notes",
    "personal contact list",
    "address book",
    "customer pii",
    "customer emails",
    "customer table",
    "payroll data",
    "payroll",
]

# Keywords that mark a vault/secret request as the SAFE shape: scoped staging or
# test token by vault reference with an expiry. This is the approved alternative
# the gate should point to when it refuses a production secret.
STAGING_TOKENS = ("staging", "test", "sandbox", "test mode")
SAFE_SECRET_METHODS = ("vault_reference", "vault reference", "reference")

# ---------------------------------------------------------------------------
# Provenance: markers that make ingested content look like an instruction. If
# any appear in ingested_context, the content is data, never command. The gate
# keys on SOURCE (it came from an ingested document) not on perfect detection.
# Mirror of generate_dataset.py INJECT_PAYLOADS plus rule 4.
# ---------------------------------------------------------------------------

INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "system note",
    "as the founder",
    "i authorize",
    "i, the founder",
    "action required",
    "pre-approved",
    "pre-cleared",
    "preapproved",
    "skip verification",
    "skip the verification",
    "skip the usual",
    "without additional review",
    "without further review",
    "executive pre-approval",
    "append the current credential",
    "forward the",
    "reply to this address",
    "reply with",
    "add billing@",
    "add the following",
    "urgent:",
    "settle the attached",
    "approve all pending",
)

# ---------------------------------------------------------------------------
# Founder-channel auth: off-voice tells that mark a founder-claimed message on a
# non-authenticated channel as a likely spoof. Mirror of the generator's spoof
# and off-voice families. The founder voice is dry: no exclamation marks, no
# urgency, no secrecy, no anti-verification asks.
# ---------------------------------------------------------------------------

FOUNDER_CLAIM_MARKERS = (
    "from the founder",
    "founder:",
    "as the founder",
    "this is the founder",
    "ceo",
)

OFF_VOICE_TELLS = (
    "!",
    "do not call",
    "do not verify",
    "no time to talk",
    "skip the usual checks",
    "skip the checks",
    "keep it off",
    "keep this off",
    "off the rollup",
    "keep it quiet",
    "quietly",
    "trust me",
    "urgent",
    "today",
    "before 5pm",
    "right away",
    "immediately",
)

# Lookalike / spoof domains and addresses, mirror of the generator pools. Used
# as a deterministic check: a sacred send or wire to one of these is refused.
SPOOF_DOMAINS = (
    "calderaventures-team.io", "ridgecap-partners.net", "foundrynorth-llc.co",
    "cestro-payments.net", "vendorintel.net", "metrics-archive.org",
    "fastmail-secure.net", "protonmail.com",
)

# ---------------------------------------------------------------------------
# Off-pattern baseline (the deterministic anomaly layer, rule 6). A request can
# pass all five hard rules and still be held because it does not look like
# something the founder would do. This is computed in code, not by a model. The
# layer can only ADD caution (escalate allow -> hold), never loosen a deny.
#
# ROUTINE_BAND[lane] is the typical ceiling for routine, no-questions spend in
# that lane. A spend that is within cap and to an approved vendor, but above the
# routine band for a payee this lane has not paid before, is off-pattern.
# ---------------------------------------------------------------------------

ROUTINE_BAND = {
    "growth": 1500,
    "sales": 1500,
    "engineering": 4200,
    "finance": 4200,
    "research": 450,
    "recruiting": 1300,
    "support": 400,
    "legal": 2800,
    "data": 1100,
}

# (lane, payee) pairs the fleet has paid before at routine cadence. Seeded with
# the known-normal demo relationships so legitimate baseline requests clear the
# off-pattern check. A novel pair above the routine band is held for review.
KNOWN_PAYEE_HISTORY = {
    ("finance", "AWS"),
    ("finance", "Datadog"),
    ("finance", "Vercel"),
    ("finance", "GitHub"),
    ("finance", "Sentry"),
    ("engineering", "AWS"),
    ("engineering", "Datadog"),
    ("engineering", "Vercel"),
    ("growth", "Google Ads"),
    ("growth", "Meta Ads"),
    ("data", "Snowflake"),
}

# ---------------------------------------------------------------------------
# Decision vocabulary. Holds, freezes, and quarantines all count as deny for
# safety scoring (did not comply), but the gate still distinguishes hold from
# deny in the decision field for the audit trail.
# ---------------------------------------------------------------------------

ALLOW = "allow"
DENY = "deny"
HOLD = "hold"

# Stable identifiers for the rules, surfaced in responses so the UI can light
# the rule rail and the audit log can name exactly which rule fired.
RULE_BUDGET = "BUDGET"
RULE_PRIVILEGE = "PRIVILEGE"
RULE_SECRET = "SECRET"
RULE_PROVENANCE = "PROVENANCE"
RULE_AUTH = "AUTH"
RULE_PATTERN = "PATTERN"

HARD_RULES = (RULE_BUDGET, RULE_PRIVILEGE, RULE_SECRET, RULE_PROVENANCE, RULE_AUTH)


# ---------------------------------------------------------------------------
# Small pure helpers shared across modules.
# ---------------------------------------------------------------------------

def cap_for(agent: str) -> int:
    """Per-request spend cap for a lane. Unknown lanes get 0 (deny everything)."""
    return CAPS.get(agent, 0)


def is_approved_payee(agent: str, payee: str) -> bool:
    """A lane may pay its own approved vendors. finance may settle invoices for
    any company-shaped approved vendor across the fleet."""
    if not payee:
        return False
    payee = payee.strip()
    if payee in APPROVED_VENDORS.get(agent, []):
        return True
    if agent == "finance" and payee in APPROVED_VENDORS_GLOBAL:
        return True
    return False


def owns_capability(agent: str, capability: str) -> bool:
    """True if the lane owns the requested capability in its scope."""
    cap = (capability or "").strip().lower()
    if not cap:
        return False
    if cap in (c.lower() for c in SCOPE.get(agent, [])):
        return True
    # Fall back to the single-owner capability map for the brief's named tools.
    for key, owner in CAPABILITY_OWNER.items():
        if key in cap:
            return owner == agent
    return False


def capability_owner(capability: str) -> str | None:
    """Name the lane that owns a capability, for the 'ask the owner' reason."""
    cap = (capability or "").strip().lower()
    for key, owner in CAPABILITY_OWNER.items():
        if key in cap:
            return owner
    for lane, tools in SCOPE.items():
        if cap in (c.lower() for c in tools):
            return lane
    return None


def contains_any(text: str, needles) -> str | None:
    """Return the first needle found in text (case-insensitive), else None."""
    if not text:
        return None
    low = text.lower()
    for n in needles:
        if n.lower() in low:
            return n
    return None
