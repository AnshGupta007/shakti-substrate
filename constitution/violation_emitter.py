"""
constitution/violation_emitter.py
When a bound check returns permitted=False, this emitter fires a
GOV_BOUND_VIOLATION governance event via the governance router.

Order is non-negotiable: Block → emit violation → return.
NEVER permit a bound-violating operation to proceed.
NEVER emit GOV_BOUND_VIOLATION without first blocking the operation.
"""

from constitution.bound_checker import BoundCheckResult
from spine.router import GovernanceResult, process as router_process


def emit_violation(
    bound_result: BoundCheckResult,
    parent_trace_id: str,
    timestamp: str,
    db_path: str = None,
) -> GovernanceResult:
    """
    Emit a GOV_BOUND_VIOLATION governance event for a bound check failure.
    
    Precondition: bound_result.permitted must be False.
    If permitted=True, raises ValueError — violation emission requires a violation.
    """
    if bound_result.permitted:
        raise ValueError("Cannot emit violation for a permitted operation.")

    payload = {
        "component": bound_result.component,
        "operation": bound_result.operation,
        "target": bound_result.target,
        "violation_id": bound_result.violation_id,
    }

    return router_process(
        event_type="GOV_BOUND_VIOLATION",
        parent_trace_id=parent_trace_id,
        payload=payload,
        timestamp=timestamp,
        db_path=db_path,
    )
