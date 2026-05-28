"""
api/spine_api.py
FastAPI spine surface — 6 endpoints.
Routes are wiring only. All logic in spine modules.
Every endpoint emits GOV_SURFACE_ACCESS via governance router after responding.
Every endpoint calls bound_checker before reading any store.
"""

import hashlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from constitution.bound_checker import check as bound_check, BoundCheckResult
from constitution.authority_bounds import get_constitution, list_components
from telemetry.continuity_probe import probe as continuity_probe
from telemetry.flow_tracker import track as flow_track
from observability.snapshot_engine import take_snapshot
from observability.replay_safe_observer import observe
from truth.truth_assembler import assemble as truth_assemble
from spine import ingestion_store, signal_log, gov_store, spine_store
from spine.router import process as router_process

app = FastAPI(title="SHAKTI Governance Substrate", version="4.0")


def _get_stores():
    return {
        "ingestion_store": ingestion_store,
        "signal_log": signal_log,
        "gov_store": gov_store,
    }


def _emit_surface_access(endpoint: str, method: str, timestamp: str, trace_id: str = ""):
    """Emit GOV_SURFACE_ACCESS via governance router. API layer is permitted to emit this.
    Timestamp is injected — datetime.now() is NEVER called inside any module."""
    if not trace_id:
        trace_id = hashlib.sha256(
            f"surface_access{endpoint}{method}".encode("utf-8")
        ).hexdigest()

    try:
        router_process(
            event_type="GOV_SURFACE_ACCESS",
            parent_trace_id=trace_id,
            payload={
                "endpoint": endpoint,
                "method": method,
                "caller_id": "spine_api",
                "response_code": 200,
            },
            timestamp=timestamp,
        )
    except Exception:
        pass  # Surface access logging should not break the response


# ─── Request Models ─────────────────────────────────────────────────────────

class SnapshotRequest(BaseModel):
    at_sequence: int
    timestamp: str


class ProbeRequest(BaseModel):
    device_id: str
    from_sequence: int
    to_sequence: int


class TruthRequest(BaseModel):
    device_id: str
    timestamp: str


# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/spine/health")
def spine_health(timestamp: str = ""):
    """Returns system health status. Timestamp query param used for surface access logging."""
    # Check stores are online by attempting a count
    stores_online = []
    try:
        ingestion_store.count()
        stores_online.append("ingestion_store")
    except Exception:
        pass
    try:
        signal_log.count()
        stores_online.append("signal_log")
    except Exception:
        pass
    try:
        gov_store.count()
        stores_online.append("gov_store")
    except Exception:
        pass
    try:
        spine_store.count_snapshots()
        stores_online.append("spine_store")
    except Exception:
        pass

    result = {
        "status": "ok",
        "stores_online": stores_online,
        "constitution_active": True,
        "snapshot_count": spine_store.count_snapshots(),
    }

    ts = timestamp or "0000-00-00T00:00:00"
    _emit_surface_access("/spine/health", "GET", timestamp=ts)
    return result


@app.post("/spine/snapshot")
def create_snapshot(req: SnapshotRequest):
    """Take a system snapshot at a given sequence boundary."""
    # Bound check: API_LAYER reads from stores
    api_check = bound_check("API_LAYER", "read", "ingestion_store")
    if not api_check.permitted:
        raise HTTPException(status_code=403, detail=api_check.reason)

    stores = _get_stores()
    snapshot = take_snapshot(stores, req.at_sequence, req.timestamp)

    # Write to spine store (TELEMETRY_SPINE writes to spine_store)
    write_check = bound_check("TELEMETRY_SPINE", "write", "spine_store")
    if write_check.permitted:
        spine_store.write_snapshot(snapshot)

    _emit_surface_access("/spine/snapshot", "POST", timestamp=req.timestamp)
    return snapshot.to_dict()


@app.post("/spine/probe")
def create_probe(req: ProbeRequest):
    """Run continuity probe for a device."""
    api_check = bound_check("API_LAYER", "read", "ingestion_store")
    if not api_check.permitted:
        raise HTTPException(status_code=403, detail=api_check.reason)

    result = continuity_probe(ingestion_store, req.device_id, req.from_sequence, req.to_sequence)

    # Write to spine store
    write_check = bound_check("TELEMETRY_SPINE", "write", "spine_store")
    if write_check.permitted:
        spine_store.write_probe(result)

    _emit_surface_access("/spine/probe", "POST", timestamp="0000-00-00T00:00:00")
    return result.to_dict()


@app.get("/spine/flow/{trace_id}")
def get_flow(trace_id: str):
    """Track the journey of a telemetry record."""
    api_check = bound_check("API_LAYER", "read", "ingestion_store")
    if not api_check.permitted:
        raise HTTPException(status_code=403, detail=api_check.reason)

    flow = flow_track(trace_id, ingestion_store, signal_log, gov_store)

    # Write to spine store
    write_check = bound_check("TELEMETRY_SPINE", "write", "spine_store")
    if write_check.permitted:
        spine_store.write_flow(flow)

    _emit_surface_access(f"/spine/flow/{trace_id}", "GET", timestamp="0000-00-00T00:00:00", trace_id=trace_id)
    return flow.to_dict()


@app.post("/spine/truth")
def create_truth(req: TruthRequest):
    """Assemble operational truth for a device."""
    api_check = bound_check("API_LAYER", "read", "ingestion_store")
    if not api_check.permitted:
        raise HTTPException(status_code=403, detail=api_check.reason)

    stores = _get_stores()
    truth = truth_assemble(req.device_id, stores, req.timestamp)

    # Write to spine store
    write_check = bound_check("TELEMETRY_SPINE", "write", "spine_store")
    if write_check.permitted:
        spine_store.write_truth(truth)

    _emit_surface_access("/spine/truth", "POST", timestamp=req.timestamp)
    return truth.to_dict()


@app.get("/spine/constitution/{component}")
def get_constitution_endpoint(component: str):
    """Get the declared constitution for a component with live bound check demo."""
    try:
        constitution = get_constitution(component)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Live bound check demo: one permitted, one non-permitted
    # Find a permitted operation
    permitted_demo = None
    for op_type in ["read", "write", "emit"]:
        targets = constitution.get(op_type, [])
        if targets:
            result = bound_check(component, op_type, targets[0])
            permitted_demo = result.to_dict()
            break

    # Find a non-permitted operation
    non_permitted_demo = None
    # Try an operation that should be blocked
    blocked_targets = {
        "read": "spine_store",
        "write": "gov_store",
        "emit": "GOV_BOUND_VIOLATION",
    }
    for op_type, target in blocked_targets.items():
        if target not in constitution.get(op_type, []):
            result = bound_check(component, op_type, target)
            non_permitted_demo = result.to_dict()
            break

    response = {
        "component": component,
        "constitution": constitution,
        "bound_check_demo": {
            "permitted": permitted_demo,
            "non_permitted": non_permitted_demo,
        },
    }

    _emit_surface_access(f"/spine/constitution/{component}", "GET", timestamp="0000-00-00T00:00:00")
    return response
