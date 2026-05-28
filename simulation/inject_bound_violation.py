"""
simulation/inject_bound_violation.py
Demonstrates constitutional enforcement:
1. Attempt to write to gov_store as INGESTION_LAYER -> BLOCKED
2. Attempt to read from spine_store as TANTRA_MODULE -> BLOCKED
3. Attempt to emit GOV_POLICY_CHECK as API_LAYER directly -> BLOCKED
4. Perform a permitted operation (GOVERNANCE_ROUTER reads ingestion_store)
5. Verify 3 GOV_BOUND_VIOLATION events exist in gov_store after the demo.
"""

import hashlib
import json
import os
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constitution.bound_checker import check as bound_check
from constitution.violation_emitter import emit_violation
from spine import gov_store


def main():
    print("=" * 72)
    print("  SHAKTI CONSTITUTIONAL BOUND VIOLATION -- SIMULATION")
    print("=" * 72)

    tmp = tempfile.mkdtemp(prefix="shakti_violation_")
    gov_db = os.path.join(tmp, "violation_gov.db")

    attempts = []
    violation_count = 0
    permit_count = 0

    # -- Attempt 1: INGESTION_LAYER writes to gov_store --
    print("\n-- Attempt 1: INGESTION_LAYER -> write -> gov_store --")
    result1 = bound_check("INGESTION_LAYER", "write", "gov_store")
    vid1 = result1.violation_id[:16] if result1.violation_id else "None"
    print(f"  component:    {result1.component}")
    print(f"  operation:    {result1.operation}")
    print(f"  target:       {result1.target}")
    print(f"  permitted:    {result1.permitted}")
    print(f"  violation_id: {vid1}...")
    print(f"  reason:       {result1.reason}")

    if not result1.permitted:
        parent_trace = hashlib.sha256(b"violation_attempt_1").hexdigest()
        emit_violation(result1, parent_trace, "2026-05-28T00:00:01", db_path=gov_db)
        violation_count += 1
        print("  -> BLOCKED. GOV_BOUND_VIOLATION emitted.")
    attempts.append(result1)

    # -- Attempt 2: TANTRA_MODULE reads from spine_store --
    print("\n-- Attempt 2: TANTRA_MODULE -> read -> spine_store --")
    result2 = bound_check("TANTRA_MODULE", "read", "spine_store")
    vid2 = result2.violation_id[:16] if result2.violation_id else "None"
    print(f"  component:    {result2.component}")
    print(f"  operation:    {result2.operation}")
    print(f"  target:       {result2.target}")
    print(f"  permitted:    {result2.permitted}")
    print(f"  violation_id: {vid2}...")
    print(f"  reason:       {result2.reason}")

    if not result2.permitted:
        parent_trace = hashlib.sha256(b"violation_attempt_2").hexdigest()
        emit_violation(result2, parent_trace, "2026-05-28T00:00:02", db_path=gov_db)
        violation_count += 1
        print("  -> BLOCKED. GOV_BOUND_VIOLATION emitted.")
    attempts.append(result2)

    # -- Attempt 3: API_LAYER emits GOV_POLICY_CHECK directly --
    print("\n-- Attempt 3: API_LAYER -> emit -> GOV_POLICY_CHECK --")
    result3 = bound_check("API_LAYER", "emit", "GOV_POLICY_CHECK")
    vid3 = result3.violation_id[:16] if result3.violation_id else "None"
    print(f"  component:    {result3.component}")
    print(f"  operation:    {result3.operation}")
    print(f"  target:       {result3.target}")
    print(f"  permitted:    {result3.permitted}")
    print(f"  violation_id: {vid3}...")
    print(f"  reason:       {result3.reason}")

    if not result3.permitted:
        parent_trace = hashlib.sha256(b"violation_attempt_3").hexdigest()
        emit_violation(result3, parent_trace, "2026-05-28T00:00:03", db_path=gov_db)
        violation_count += 1
        print("  -> BLOCKED. GOV_BOUND_VIOLATION emitted.")
    attempts.append(result3)

    # -- Attempt 4: GOVERNANCE_ROUTER reads ingestion_store (permitted) --
    print("\n-- Attempt 4: GOVERNANCE_ROUTER -> read -> ingestion_store --")
    result4 = bound_check("GOVERNANCE_ROUTER", "read", "ingestion_store")
    print(f"  component:    {result4.component}")
    print(f"  operation:    {result4.operation}")
    print(f"  target:       {result4.target}")
    print(f"  permitted:    {result4.permitted}")
    print(f"  violation_id: {result4.violation_id or 'None'}")
    print(f"  reason:       {result4.reason}")
    print("  -> PERMITTED. No violation emitted.")
    permit_count += 1
    attempts.append(result4)

    # -- Verification: Check gov_store for violations --
    print("\n-- Verification: Checking gov_store for GOV_BOUND_VIOLATION events --")
    violation_events = gov_store.read_by_event_type("GOV_BOUND_VIOLATION", db_path=gov_db)
    print(f"  GOV_BOUND_VIOLATION events found: {len(violation_events)}")

    for i, evt in enumerate(violation_events):
        gid_short = evt['gov_event_id'][:16]
        print(f"\n  Violation {i+1}:")
        print(f"    gov_event_id: {gid_short}...")
        print(f"    event_type:   {evt['event_type']}")
        print(f"    decision:     {evt['decision']}")
        print(f"    component:    {evt['metadata'].get('component', 'N/A')}")
        print(f"    operation:    {evt['metadata'].get('operation', 'N/A')}")
        print(f"    target:       {evt['metadata'].get('target', 'N/A')}")

    # -- Summary --
    print("\n" + "=" * 72)
    print(f"Violation demo complete. {violation_count} blocked. {permit_count} permitted. "
          f"{len(violation_events)} governance events emitted.")
    print("=" * 72)


if __name__ == "__main__":
    main()
