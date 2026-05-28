"""
constitution/bound_checker.py
Pure function: check(component, operation, target) -> BoundCheckResult.
No side effects. No I/O. Same inputs → always same result.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

from constitution.authority_bounds import get_constitution


@dataclass
class BoundCheckResult:
    component: str
    operation: str
    target: str
    permitted: bool
    violation_id: Optional[str]
    reason: str

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "operation": self.operation,
            "target": self.target,
            "permitted": self.permitted,
            "violation_id": self.violation_id,
            "reason": self.reason,
        }


def check(component: str, operation: str, target: str) -> BoundCheckResult:
    """
    Check whether a component is permitted to perform an operation on a target.
    operation: "read" | "write" | "emit"
    target: the store name or event type being accessed
    
    This is a PURE FUNCTION. No side effects. No I/O.
    Same inputs → always same result.
    """
    # Validate operation type
    if operation not in ("read", "write", "emit"):
        return BoundCheckResult(
            component=component,
            operation=operation,
            target=target,
            permitted=False,
            violation_id=hashlib.sha256(
                f"{component}{operation}{target}".encode("utf-8")
            ).hexdigest(),
            reason=f"Invalid operation type: '{operation}'. Must be 'read', 'write', or 'emit'.",
        )

    # Get the component's constitution
    try:
        constitution = get_constitution(component)
    except ValueError:
        return BoundCheckResult(
            component=component,
            operation=operation,
            target=target,
            permitted=False,
            violation_id=hashlib.sha256(
                f"{component}{operation}{target}".encode("utf-8")
            ).hexdigest(),
            reason=f"No constitution declared for component: '{component}'.",
        )

    # Check if the target is in the permitted list for this operation
    permitted_targets = constitution.get(operation, [])
    if target in permitted_targets:
        return BoundCheckResult(
            component=component,
            operation=operation,
            target=target,
            permitted=True,
            violation_id=None,
            reason=f"Component '{component}' is permitted to {operation} '{target}'.",
        )
    else:
        violation_id = hashlib.sha256(
            f"{component}{operation}{target}".encode("utf-8")
        ).hexdigest()
        return BoundCheckResult(
            component=component,
            operation=operation,
            target=target,
            permitted=False,
            violation_id=violation_id,
            reason=(f"Component '{component}' is NOT permitted to {operation} '{target}'. "
                    f"Permitted {operation} targets: {permitted_targets}."),
        )
