"""Formal state machine with illegal transition rejection.

Supports both workflow-level and stage-level state machines.
Every transition is validated against allowed transitions.
"""

from __future__ import annotations

import logging
from typing import Any

from production_pipeline.constants import (
    STAGE_TRANSITIONS,
    TERMINAL_STAGE_STATES,
    TERMINAL_WORKFLOW_STATES,
    WORKFLOW_TRANSITIONS,
    StageState,
    WorkflowState,
)
from production_pipeline.exceptions import StageStateError, WorkflowStateError

logger = logging.getLogger(__name__)


class WorkflowStateMachine:
    """Formal workflow-level state machine.

    Validates all transitions against WORKFLOW_TRANSITIONS rules.
    Rejects illegal transitions with clear error messages.
    """

    def __init__(self, initial_state: WorkflowState = WorkflowState.CREATED) -> None:
        self._state = initial_state

    @property
    def state(self) -> WorkflowState:
        return self._state

    def transition_to(self, new_state: WorkflowState) -> WorkflowState:
        """Attempt a state transition. Raises if illegal.

        Args:
            new_state: Target state.

        Returns:
            The new state on success.

        Raises:
            WorkflowStateError: If transition is not allowed.
        """
        if self._state == new_state:
            return self._state

        allowed = WORKFLOW_TRANSITIONS.get(self._state, [])
        if new_state not in allowed:
            raise WorkflowStateError(
                f"Illegal workflow state transition: "
                f"{self._state.value} → {new_state.value}. "
                f"Allowed from {self._state.value}: "
                f"{[s.value for s in allowed]}"
            )

        logger.debug("Workflow state: %s → %s", self._state.value, new_state.value)
        self._state = new_state
        return self._state

    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """Check if a transition is allowed without raising."""
        if self._state == new_state:
            return True
        return new_state in WORKFLOW_TRANSITIONS.get(self._state, [])

    def is_terminal(self) -> bool:
        """Check if current state is terminal."""
        return self._state in TERMINAL_WORKFLOW_STATES

    def is_running(self) -> bool:
        return self._state == WorkflowState.RUNNING

    def is_failed(self) -> bool:
        return self._state == WorkflowState.FAILED

    def is_completed(self) -> bool:
        return self._state == WorkflowState.COMPLETED

    def is_cancelled(self) -> bool:
        return self._state == WorkflowState.CANCELLED

    def reset(self, state: WorkflowState = WorkflowState.CREATED) -> None:
        self._state = state


class StageStateMachine:
    """Formal stage-level state machine.

    Validates all transitions against STAGE_TRANSITIONS rules.
    """

    def __init__(self, initial_state: StageState = StageState.PENDING) -> None:
        self._state = initial_state

    @property
    def state(self) -> StageState:
        return self._state

    def transition_to(self, new_state: StageState) -> StageState:
        if self._state == new_state:
            return self._state

        allowed = STAGE_TRANSITIONS.get(self._state, [])
        if new_state not in allowed:
            raise StageStateError(
                f"Illegal stage state transition: "
                f"{self._state.value} → {new_state.value}. "
                f"Allowed from {self._state.value}: "
                f"{[s.value for s in allowed]}"
            )

        logger.debug("Stage state: %s → %s", self._state.value, new_state.value)
        self._state = new_state
        return self._state

    def can_transition_to(self, new_state: StageState) -> bool:
        if self._state == new_state:
            return True
        return new_state in STAGE_TRANSITIONS.get(self._state, [])

    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STAGE_STATES

    def is_completed(self) -> bool:
        return self._state == StageState.COMPLETED

    def is_failed(self) -> bool:
        return self._state == StageState.FAILED
