"""
telemetry/continuity_probe.py
Telemetry that proves it is complete and gap-free.
probe() is a READ-ONLY operation — it must NOT write anything to the store.
NEVER generate probe_id from random(). NEVER call datetime.now() inside probe().
"""

import hashlib
from dataclasses import dataclass, field
from typing import List


@dataclass
class ContinuityResult:
    probe_id: str           # SHA-256 of (device_id + from_seq + to_seq)
    device_id: str
    from_sequence: int
    to_sequence: int
    expected_count: int     # to_seq - from_seq + 1
    actual_count: int       # records actually found in store
    gaps: List[dict]        # each gap: {after_seq, before_seq, missing_count}
    is_continuous: bool     # True only if gaps is empty
    continuity_proof: str   # SHA-256 chain hash of all trace_ids in sequence order

    def to_dict(self) -> dict:
        return {
            "probe_id": self.probe_id,
            "device_id": self.device_id,
            "from_sequence": self.from_sequence,
            "to_sequence": self.to_sequence,
            "expected_count": self.expected_count,
            "actual_count": self.actual_count,
            "gaps": self.gaps,
            "is_continuous": self.is_continuous,
            "continuity_proof": self.continuity_proof,
        }


def probe(store, device_id: str, from_seq: int, to_seq: int) -> ContinuityResult:
    """
    Probe a telemetry sequence range for a device and detect any gaps.
    
    This is a READ-ONLY operation. It does NOT write anything to the store.
    probe_id is deterministic: SHA-256 of (device_id + from_seq + to_seq).
    
    continuity_proof is a chain hash:
      Start with empty string.
      For each record in sequence order:
        continuity_proof = SHA-256(continuity_proof + record.trace_id)
      This makes the proof dependent on the exact order and content of every record.
      Any gap, swap, or insertion changes the proof.
    """
    # Deterministic probe_id — never from random()
    probe_id = hashlib.sha256(
        f"{device_id}{from_seq}{to_seq}".encode("utf-8")
    ).hexdigest()

    expected_count = to_seq - from_seq + 1

    # READ-ONLY: fetch records from the store
    records = store.read_range(from_seq, to_seq)

    # Filter for this device's records
    device_records = [r for r in records if r.get("device_id") == device_id]
    actual_count = len(device_records)

    # Detect gaps by looking at sequence numbers
    gaps = []
    device_seqs = sorted([r["sequence_number"] for r in device_records])

    if device_seqs:
        # Check for gap at start
        if device_seqs[0] > from_seq:
            missing = device_seqs[0] - from_seq
            gaps.append({
                "after_seq": from_seq - 1,
                "before_seq": device_seqs[0],
                "missing_count": missing,
            })

        # Check for gaps between consecutive records
        for i in range(1, len(device_seqs)):
            if device_seqs[i] - device_seqs[i - 1] > 1:
                missing = device_seqs[i] - device_seqs[i - 1] - 1
                gaps.append({
                    "after_seq": device_seqs[i - 1],
                    "before_seq": device_seqs[i],
                    "missing_count": missing,
                })

        # Check for gap at end
        if device_seqs[-1] < to_seq:
            missing = to_seq - device_seqs[-1]
            gaps.append({
                "after_seq": device_seqs[-1],
                "before_seq": to_seq + 1,
                "missing_count": missing,
            })
    elif expected_count > 0:
        # No records found at all in range — entire range is a gap
        gaps.append({
            "after_seq": from_seq - 1,
            "before_seq": to_seq + 1,
            "missing_count": expected_count,
        })

    is_continuous = len(gaps) == 0

    # Compute chain hash continuity proof
    # Start with empty string, chain SHA-256 over each trace_id in sequence order
    proof = ""
    for record in device_records:
        trace_id = record.get("trace_id", "")
        proof = hashlib.sha256(
            f"{proof}{trace_id}".encode("utf-8")
        ).hexdigest()

    # If no records, proof is hash of empty
    if not device_records:
        proof = hashlib.sha256(b"").hexdigest()

    return ContinuityResult(
        probe_id=probe_id,
        device_id=device_id,
        from_sequence=from_seq,
        to_sequence=to_seq,
        expected_count=expected_count,
        actual_count=actual_count,
        gaps=gaps,
        is_continuous=is_continuous,
        continuity_proof=proof,
    )
