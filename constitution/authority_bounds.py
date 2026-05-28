"""
constitution/authority_bounds.py
Defines the constitution for every component in SHAKTI.
Each constitution declares what a component is PERMITTED to do:
  READ  — which stores/surfaces the component may read from
  WRITE — which stores/surfaces the component may write to
  EMIT  — which event types the component may emit
"""

# ─── COMPONENT CONSTITUTIONS ────────────────────────────────────────────────
# Hardcoded exactly as specified. Declarative, not runtime-computed.

_CONSTITUTIONS = {
    "INGESTION_LAYER": {
        "read": [],
        "write": ["ingestion_store"],
        "emit": [],
    },
    "SIGNAL_ENGINE": {
        "read": ["ingestion_store"],
        "write": ["signal_log"],
        "emit": [],
    },
    "GOVERNANCE_ROUTER": {
        "read": ["ingestion_store", "signal_log", "gov_store"],
        "write": ["gov_store"],
        "emit": [
            "GOV_POLICY_CHECK",
            "GOV_COMPLIANCE_AUDIT",
            "GOV_TRACE_VERIFY",
            "GOV_SURFACE_ACCESS",
            "GOV_POLICY_VIOLATION",
            "GOV_OVERRIDE",
            "GOV_REPLAY_CONTINUITY",
            "GOV_BOUND_VIOLATION",
        ],
    },
    "TANTRA_MODULE": {
        "read": [],
        "write": [],
        "emit": [],
    },
    "BHIV_MODULE": {
        "read": [],
        "write": [],
        "emit": [],
    },
    "API_LAYER": {
        "read": ["ingestion_store", "signal_log", "gov_store", "spine_store"],
        "write": [],
        "emit": ["GOV_SURFACE_ACCESS"],
    },
    "TELEMETRY_SPINE": {
        "read": ["ingestion_store", "signal_log", "gov_store"],
        "write": ["spine_store"],
        "emit": ["GOV_BOUND_VIOLATION"],
    },
}


def get_constitution(component_name: str) -> dict:
    """Returns the constitution dict for a given component.
    Raises ValueError if the component is not declared."""
    constitution = _CONSTITUTIONS.get(component_name)
    if constitution is None:
        raise ValueError(f"No constitution declared for component: {component_name}")
    return constitution


def list_components() -> list:
    """Returns all declared component names."""
    return list(_CONSTITUTIONS.keys())
