"""
spine/router.py
Governance Router — the core of the mini-spine.
Wires: event creation → BHIV verify → TANTRA validate → store → return.
BHIV always runs BEFORE TANTRA. TANTRA is the gatekeeper to the store.
datetime.now() is NEVER called here — timestamp is always injected.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

from governance.event_types import create_gov_event
from bhiv.alignment import BhivResult, verify as bhiv_verify
from tantra.alignment import TantraResult, validate as tantra_validate
from spine import gov_store


@dataclass
class GovernanceResult:
    gov_event: dict
    tantra_result: TantraResult
    bhiv_result: BhivResult
    stored: bool
    rejection_reason: Optional[str]

    def to_dict(self) -> dict:
        return {
            "gov_event": self.gov_event,
            "tantra_result": self.tantra_result.to_dict(),
            "bhiv_result": self.bhiv_result.to_dict(),
            "stored": self.stored,
            "rejection_reason": self.rejection_reason,
        }


def _compute_gov_event_id(event_type: str, parent_trace_id: str,
                           policy_id: str, timestamp: str) -> str:
    raw = f"{event_type}{parent_trace_id}{policy_id}{timestamp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def process(
    event_type: str,
    parent_trace_id: str,
    payload: dict,
    timestamp: str,
    operator_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> GovernanceResult:
    """
    Process a governance event through the full spine pipeline:
      1. Fetch last 10 governance events for BHIV context.
      2. Create the raw governance event draft.
      3. Run BHIV verify (BHIV always runs FIRST).
      4. Inject bhiv_verdict and bhiv_confidence into the event.
      5. Recompute gov_event_id after all fields are set.
      6. Run TANTRA validate (gatekeeper).
      7. If TANTRA aligned → write to store; else → do NOT write.
      8. Return GovernanceResult.
    """

    # Step 1: BHIV context — last 10 events from store
    recent_events = gov_store.read_last_n(10, db_path=db_path)

    # Step 2: Build the initial governance event draft via event_types dispatcher
    gov_event_draft = create_gov_event(event_type, parent_trace_id, payload, timestamp)

    # Step 3: BHIV verify (BHIV runs BEFORE TANTRA — non-negotiable)
    bhiv_result = bhiv_verify(gov_event_draft, recent_events)

    # Step 4: Inject BHIV verdict into the event (TANTRA-R05 needs it)
    gov_event_draft["bhiv_verdict"] = bhiv_result.verdict
    gov_event_draft["bhiv_confidence"] = bhiv_result.confidence

    # Step 5: Recompute gov_event_id — must be done AFTER all identity fields are stable.
    # gov_event_id depends on: event_type, parent_trace_id, policy_id, governance_timestamp.
    # bhiv fields are NOT part of the ID hash (they don't change the 4 canonical fields).
    gov_event_id = _compute_gov_event_id(
        gov_event_draft["event_type"],
        gov_event_draft["parent_trace_id"],
        gov_event_draft["policy_id"],
        gov_event_draft["governance_timestamp"],
    )
    gov_event_draft["gov_event_id"] = gov_event_id

    # Step 6: TANTRA validate — the gatekeeper to the store
    tantra_result = tantra_validate(gov_event_draft)

    # Step 7: Write to store ONLY if TANTRA aligned
    stored = False
    rejection_reason: Optional[str] = None
    sequence_number = -1

    if tantra_result.aligned:
        gov_event_draft["tantra_aligned"] = True
        sequence_number = gov_store.write(gov_event_draft, db_path=db_path)
        gov_event_draft["sequence_number"] = sequence_number
        stored = True
    else:
        gov_event_draft["tantra_aligned"] = False
        rejection_reason = "; ".join(tantra_result.failed_rules)

    # Step 8: Return full result
    return GovernanceResult(
        gov_event=gov_event_draft,
        tantra_result=tantra_result,
        bhiv_result=bhiv_result,
        stored=stored,
        rejection_reason=rejection_reason,
    )
