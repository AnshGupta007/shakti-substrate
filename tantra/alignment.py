"""
tantra/alignment.py
TANTRA — governance policy validation module.
Pure function: validate(gov_event) -> TantraResult.
No side effects. No I/O. No database calls.
Same gov_event dict → always same TantraResult.
"""

import hashlib
from dataclasses import dataclass
from typing import List

TANTRA_VERSION = "TANTRA-v1.0"

VALID_EVENT_TYPES = {
    "GOV_POLICY_CHECK",
    "GOV_COMPLIANCE_AUDIT",
    "GOV_TRACE_VERIFY",
    "GOV_SURFACE_ACCESS",
    "GOV_POLICY_VIOLATION",
    "GOV_OVERRIDE",
    "GOV_REPLAY_CONTINUITY",
    "GOV_BOUND_VIOLATION",
}

VALID_DECISIONS = {"ESCALATE", "SUPPRESS", "LOG_ONLY", "BLOCK", "PASS"}
VALID_BHIV_VERDICTS = {"CONSISTENT", "ANOMALOUS", "UNVERIFIED"}


@dataclass
class TantraResult:
    aligned: bool
    failed_rules: List[str]
    policy_version: str = TANTRA_VERSION

    def to_dict(self) -> dict:
        return {
            "aligned": self.aligned,
            "failed_rules": self.failed_rules,
            "policy_version": self.policy_version,
        }


def _recompute_gov_event_id(event: dict) -> str:
    """Recompute gov_event_id from stored fields — must match stored value."""
    raw = (
        str(event.get("event_type", ""))
        + str(event.get("parent_trace_id", ""))
        + str(event.get("policy_id", ""))
        + str(event.get("governance_timestamp", ""))
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate(gov_event: dict) -> TantraResult:
    """
    Validate a governance event against all 6 TANTRA rules.
    Returns TantraResult with aligned=True only if ALL rules pass.
    GOV_BOUND_VIOLATION has no special exceptions — all 6 rules apply.
    """
    failed_rules: List[str] = []

    # TANTRA-R01: Trace Presence
    parent_trace_id = gov_event.get("parent_trace_id", "")
    if not isinstance(parent_trace_id, str) or len(parent_trace_id) < 32:
        failed_rules.append("TANTRA-R01: parent_trace_id absent or too short")

    # TANTRA-R02: Valid Event Type
    event_type = gov_event.get("event_type", "")
    if event_type not in VALID_EVENT_TYPES:
        failed_rules.append("TANTRA-R02: unrecognized governance event_type")

    # TANTRA-R03: Valid Decision
    decision = gov_event.get("decision", "")
    if decision not in VALID_DECISIONS:
        failed_rules.append("TANTRA-R03: invalid decision value")

    # TANTRA-R04: ID Integrity
    stored_id = gov_event.get("gov_event_id", "")
    recomputed_id = _recompute_gov_event_id(gov_event)
    if stored_id != recomputed_id:
        failed_rules.append("TANTRA-R04: gov_event_id does not match recomputed hash")

    # TANTRA-R05: BHIV Verdict Present
    bhiv_verdict = gov_event.get("bhiv_verdict", "")
    if bhiv_verdict not in VALID_BHIV_VERDICTS:
        failed_rules.append("TANTRA-R05: bhiv_verdict missing or invalid")

    # TANTRA-R06: Metadata Non-Empty
    metadata = gov_event.get("metadata")
    if not isinstance(metadata, dict) or len(metadata) == 0:
        failed_rules.append("TANTRA-R06: metadata is empty or missing")

    aligned = len(failed_rules) == 0
    return TantraResult(aligned=aligned, failed_rules=failed_rules, policy_version=TANTRA_VERSION)
