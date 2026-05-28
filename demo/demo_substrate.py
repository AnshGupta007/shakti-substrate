"""
demo/demo_substrate.py
Demonstrates the full governance substrate in one script.
"""

import hashlib
import json
import os
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine import ingestion_store, signal_log, gov_store, spine_store
from spine.router import process as router_process
from telemetry.continuity_probe import probe as continuity_probe
from telemetry.flow_tracker import track as flow_track
from telemetry.heartbeat_emitter import check_and_emit
from observability.snapshot_engine import take_snapshot
from truth.truth_assembler import assemble as truth_assemble


def main():
    print("=" * 72)
    print("  SHAKTI GOVERNANCE SUBSTRATE -- DEMO")
    print("=" * 72)

    # Use temp directory for demo databases
    tmp = tempfile.mkdtemp(prefix="shakti_demo_")
    ing_db = os.path.join(tmp, "demo_ingestion.db")
    sig_db = os.path.join(tmp, "demo_signal.db")
    gov_db = os.path.join(tmp, "demo_gov.db")
    spine_db = os.path.join(tmp, "demo_spine.db")

    # Create store proxies
    class Proxy:
        def __init__(self, mod, path):
            self._mod = mod
            self._path = path
        def __getattr__(self, name):
            attr = getattr(self._mod, name)
            if callable(attr):
                def wrapper(*args, **kwargs):
                    kwargs.setdefault("db_path", self._path)
                    return attr(*args, **kwargs)
                return wrapper
            return attr

    ing = Proxy(ingestion_store, ing_db)
    sig = Proxy(signal_log, sig_db)
    gov = Proxy(gov_store, gov_db)
    sp = Proxy(spine_store, spine_db)

    stores = {
        "ingestion_store": ing,
        "signal_log": sig,
        "gov_store": gov,
    }

    # -- Step 1: Ingest 5 sensor records --
    print("\n-- Step 1: Ingesting 5 sensor records for GRID-RELAY-01 --")
    trace_ids = []
    for i in range(5):
        trace_id = hashlib.sha256(f"demo_GRID-RELAY-01_{i}".encode()).hexdigest()
        ts = f"2026-05-28T00:{i:02d}:00"
        ing.write({
            "trace_id": trace_id,
            "device_id": "GRID-RELAY-01",
            "source_type": "sensor",
            "validation_status": "valid",
            "ingestion_timestamp": ts,
            "payload": {"voltage": 230 + i * 5, "current": 45.0 + i},
        })
        trace_ids.append(trace_id)
        print(f"  Ingested record {i+1}: trace_id={trace_id[:16]}... ts={ts}")

    # Add a signal for the first record
    sig.write({
        "trace_id": trace_ids[0],
        "device_id": "GRID-RELAY-01",
        "signal_type": "OVERLOAD",
        "severity": "high",
        "signal_timestamp": "2026-05-28T00:00:01",
        "payload": {"voltage": 230},
    })

    # Add a governance event
    gov_result = router_process(
        event_type="GOV_POLICY_CHECK",
        parent_trace_id=trace_ids[0],
        payload={
            "signal_type": "OVERLOAD",
            "severity": "critical",
            "device_id": "GRID-RELAY-01",
        },
        timestamp="2026-05-28T00:00:02",
        db_path=gov_db,
    )
    print(f"  Governance event: type={gov_result.gov_event['event_type']}, "
          f"decision={gov_result.gov_event['decision']}, stored={gov_result.stored}")

    # -- Step 2: Simulate silence --
    print("\n-- Step 2: Simulating 60s of silence (threshold=0 for demo) --")

    # -- Step 3: Heartbeat --
    print("\n-- Step 3: Running heartbeat emitter --")
    hb_result = check_and_emit(
        device_id="GRID-RELAY-01",
        store=ing,
        silence_threshold_seconds=0,
        timestamp="2026-05-28T00:06:00",
    )
    print(f"  device_id:          {hb_result.device_id}")
    print(f"  last_seen_at:       {hb_result.last_seen_at}")
    print(f"  seconds_since_last: {hb_result.seconds_since_last}")
    print(f"  heartbeat_emitted:  {hb_result.heartbeat_emitted}")
    hb_trace_short = hb_result.heartbeat_trace_id[:16] if hb_result.heartbeat_trace_id else "None"
    print(f"  heartbeat_trace_id: {hb_trace_short}...")

    # -- Step 4: Continuity Probe --
    print("\n-- Step 4: Running continuity probe --")
    probe_result = continuity_probe(ing, "GRID-RELAY-01", 1, 6)
    sp.write_probe(probe_result)
    print(f"  probe_id:        {probe_result.probe_id[:16]}...")
    print(f"  from_sequence:   {probe_result.from_sequence}")
    print(f"  to_sequence:     {probe_result.to_sequence}")
    print(f"  expected_count:  {probe_result.expected_count}")
    print(f"  actual_count:    {probe_result.actual_count}")
    print(f"  gaps:            {probe_result.gaps}")
    print(f"  is_continuous:   {probe_result.is_continuous}")
    print(f"  continuity_proof:{probe_result.continuity_proof[:16]}...")

    # -- Step 5: System Snapshot --
    print("\n-- Step 5: Taking system snapshot at sequence 6 --")
    snapshot = take_snapshot(stores, 6, "2026-05-28T00:06:00")
    sp.write_snapshot(snapshot)
    print(f"  snapshot_id:       {snapshot.snapshot_id[:16]}...")
    print(f"  at_sequence:       {snapshot.at_sequence}")
    print(f"  ingestion_count:   {snapshot.ingestion_count}")
    print(f"  signal_count:      {snapshot.signal_count}")
    print(f"  governance_count:  {snapshot.governance_count}")
    esc_short = [e[:16] + "..." for e in snapshot.active_escalations[:2]]
    print(f"  active_escalations:{esc_short}")
    print(f"  is_replay_safe:    {snapshot.is_replay_safe}")

    # -- Step 6: Flow Tracker --
    print("\n-- Step 6: Tracking flow for first ingested trace_id --")
    flow = flow_track(trace_ids[0], ing, sig, gov)
    sp.write_flow(flow)
    print(f"  trace_id:         {flow.trace_id[:16]}...")
    print(f"  flow_stages:      {len(flow.flow_stages)} stages")
    for stage in flow.flow_stages:
        st = stage['stage_trace'][:16] if stage['stage_trace'] else "N/A"
        print(f"    -> {stage['stage_name']:20s} status={stage['status']:8s} trace={st}...")
    print(f"  is_complete:      {flow.is_complete}")
    print(f"  blocked_at:       {flow.blocked_at}")
    print(f"  total_duration_ms:{flow.total_duration_ms}")

    # -- Step 7: Operational Truth --
    print("\n-- Step 7: Assembling operational truth for GRID-RELAY-01 --")
    truth = truth_assemble("GRID-RELAY-01", stores, "2026-05-28T00:06:00")
    sp.write_truth(truth)
    print(f"  truth_id:            {truth.truth_id[:16]}...")
    print(f"  device_id:           {truth.device_id}")
    print(f"  assembled_at:        {truth.assembled_at}")
    print(f"  overall_confidence:  {truth.overall_confidence}")
    print(f"  constitutionally_bounded: {truth.is_constitutionally_bounded}")
    print(f"  claims ({len(truth.claims)}):")
    for claim in truth.claims:
        print(f"    [{claim.claim_type}]")
        assertion_short = claim.assertion[:80]
        print(f"      assertion:    {assertion_short}...")
        print(f"      evidence:     {len(claim.evidence)} items")
        print(f"      confidence:   {claim.confidence}")
        print(f"      is_verified:  {claim.is_verified}")

    # -- Summary --
    print("\n" + "=" * 72)
    print(f"Substrate demo complete. "
          f"Continuity: {probe_result.is_continuous}. "
          f"Truth confidence: {truth.overall_confidence}.")
    print("=" * 72)


if __name__ == "__main__":
    main()
