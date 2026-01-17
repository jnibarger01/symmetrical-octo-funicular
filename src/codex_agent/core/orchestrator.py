"""Orchestrator - Core state machine and lifecycle coordinator."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from ..core.config import Config
from ..core.models import AuditEvent, EventType, LifecycleState, StateTransition, Task

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class Orchestrator:
    """
    Core orchestrator managing the lifecycle state machine.

    The orchestrator coordinates all major components and enforces
    state transition rules.
    """

    # Valid state transitions
    TRANSITIONS = {
        LifecycleState.IDLE: [LifecycleState.PLANNING],
        LifecycleState.PLANNING: [LifecycleState.SCAFFOLDING, LifecycleState.FAILED],
        LifecycleState.SCAFFOLDING: [LifecycleState.BUILDING, LifecycleState.FAILED],
        LifecycleState.BUILDING: [LifecycleState.VERIFYING, LifecycleState.FAILED],
        LifecycleState.VERIFYING: [
            LifecycleState.DEPLOYING,
            LifecycleState.BUILDING,
            LifecycleState.FAILED,
        ],
        LifecycleState.DEPLOYING: [LifecycleState.OBSERVING, LifecycleState.FAILED],
        LifecycleState.OBSERVING: [LifecycleState.MAINTAINING, LifecycleState.IDLE],
        LifecycleState.MAINTAINING: [
            LifecycleState.BUILDING,
            LifecycleState.OBSERVING,
            LifecycleState.IDLE,
            LifecycleState.FAILED,
        ],
        LifecycleState.FAILED: [LifecycleState.IDLE],
    }

    def __init__(self, config: Config) -> None:
        """
        Initialize the orchestrator.

        Args:
            config: Configuration object
        """
        self.config = config
        self.current_state = LifecycleState.IDLE
        self.previous_state: Optional[LifecycleState] = None
        self.transition_history: list[StateTransition] = []
        self.current_task: Optional[Task] = None

    def can_transition(self, to_state: LifecycleState) -> bool:
        """
        Check if a state transition is valid.

        Args:
            to_state: Target state

        Returns:
            True if transition is allowed
        """
        allowed_states = self.TRANSITIONS.get(self.current_state, [])
        return to_state in allowed_states

    def transition(self, to_state: LifecycleState, trigger: str = "manual") -> StateTransition:
        """
        Transition to a new state.

        Args:
            to_state: Target state
            trigger: What triggered this transition

        Returns:
            StateTransition record

        Raises:
            StateTransitionError: If transition is not allowed
        """
        if not self.can_transition(to_state):
            raise StateTransitionError(
                f"Cannot transition from {self.current_state} to {to_state}. "
                f"Allowed transitions: {self.TRANSITIONS.get(self.current_state, [])}"
            )

        transition = StateTransition(
            from_state=self.current_state,
            to_state=to_state,
            timestamp=datetime.utcnow(),
            trigger=trigger,
        )

        self.previous_state = self.current_state
        self.current_state = to_state
        self.transition_history.append(transition)

        logger.info(
            f"State transition: {transition.from_state} -> {transition.to_state} "
            f"(trigger: {trigger})"
        )

        return transition

    def reset(self) -> None:
        """Reset orchestrator to IDLE state."""
        if self.current_state != LifecycleState.FAILED:
            logger.warning(f"Resetting orchestrator from non-failed state: {self.current_state}")

        self.current_state = LifecycleState.IDLE
        self.current_task = None
        logger.info("Orchestrator reset to IDLE state")

    def get_state(self) -> LifecycleState:
        """Get current state."""
        return self.current_state

    def get_allowed_transitions(self) -> list[LifecycleState]:
        """Get list of allowed transitions from current state."""
        return self.TRANSITIONS.get(self.current_state, [])

    def is_terminal_state(self) -> bool:
        """Check if current state is terminal (no automatic transitions)."""
        return self.current_state in [LifecycleState.IDLE, LifecycleState.FAILED]

    def create_audit_event(self, event_type: EventType, **kwargs: dict) -> AuditEvent:
        """
        Create an audit event for the current state.

        Args:
            event_type: Type of event
            **kwargs: Additional event data

        Returns:
            AuditEvent object
        """
        return AuditEvent(
            event_type=event_type,
            actor="orchestrator",
            state=self.current_state,
            event_data=kwargs,
            task_id=self.current_task.id if self.current_task else None,
        )

    def get_transition_history(self) -> list[StateTransition]:
        """Get history of state transitions."""
        return self.transition_history.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"Orchestrator(state={self.current_state}, transitions={len(self.transition_history)})"
