"""Tests for the formal state machine."""

from __future__ import annotations

import pytest

from production_pipeline.constants import (
    WorkflowState, StageState,
    WORKFLOW_TRANSITIONS, STAGE_TRANSITIONS,
    TERMINAL_WORKFLOW_STATES, TERMINAL_STAGE_STATES,
)
from production_pipeline.exceptions import WorkflowStateError, StageStateError
from production_pipeline.state_machine import WorkflowStateMachine, StageStateMachine


class TestWorkflowStateMachine:
    def test_initial_state(self):
        wsm = WorkflowStateMachine()
        assert wsm.state == WorkflowState.CREATED

    def test_initial_state_custom(self):
        wsm = WorkflowStateMachine(WorkflowState.QUEUED)
        assert wsm.state == WorkflowState.QUEUED

    def test_valid_transition(self):
        wsm = WorkflowStateMachine()
        wsm.transition_to(WorkflowState.QUEUED)
        assert wsm.state == WorkflowState.QUEUED
        wsm.transition_to(WorkflowState.RUNNING)
        assert wsm.state == WorkflowState.RUNNING

    def test_all_valid_transitions(self):
        for from_state, to_states in WORKFLOW_TRANSITIONS.items():
            wsm = WorkflowStateMachine(from_state)
            for to_state in to_states:
                wsm.transition_to(to_state)
                assert wsm.state == to_state
                wsm = WorkflowStateMachine(from_state)

    def test_illegal_transition_raises(self):
        wsm = WorkflowStateMachine(WorkflowState.CREATED)
        with pytest.raises(WorkflowStateError):
            wsm.transition_to(WorkflowState.COMPLETED)

    def test_illegal_transition_message(self):
        wsm = WorkflowStateMachine(WorkflowState.CREATED)
        try:
            wsm.transition_to(WorkflowState.ARCHIVED)
        except WorkflowStateError as e:
            assert "created" in str(e)
            assert "archived" in str(e)
            assert "Allowed" in str(e)

    def test_same_state_noop(self):
        wsm = WorkflowStateMachine(WorkflowState.CREATED)
        result = wsm.transition_to(WorkflowState.CREATED)
        assert result == WorkflowState.CREATED

    def test_can_transition_to_true(self):
        wsm = WorkflowStateMachine(WorkflowState.CREATED)
        assert wsm.can_transition_to(WorkflowState.QUEUED) == True

    def test_can_transition_to_false(self):
        wsm = WorkflowStateMachine(WorkflowState.CREATED)
        assert wsm.can_transition_to(WorkflowState.COMPLETED) == False

    def test_is_terminal(self):
        wsm = WorkflowStateMachine(WorkflowState.COMPLETED)
        assert wsm.is_terminal() == True
        wsm2 = WorkflowStateMachine(WorkflowState.RUNNING)
        assert wsm2.is_terminal() == False

    def test_is_running(self):
        wsm = WorkflowStateMachine(WorkflowState.RUNNING)
        assert wsm.is_running() == True
        wsm2 = WorkflowStateMachine(WorkflowState.PAUSED)
        assert wsm2.is_running() == False

    def test_is_failed(self):
        wsm = WorkflowStateMachine(WorkflowState.FAILED)
        assert wsm.is_failed() == True

    def test_is_completed(self):
        wsm = WorkflowStateMachine(WorkflowState.COMPLETED)
        assert wsm.is_completed() == True

    def test_is_cancelled(self):
        wsm = WorkflowStateMachine(WorkflowState.CANCELLED)
        assert wsm.is_cancelled() == True

    def test_reset(self):
        wsm = WorkflowStateMachine(WorkflowState.COMPLETED)
        wsm.reset()
        assert wsm.state == WorkflowState.CREATED

    def test_reset_custom(self):
        wsm = WorkflowStateMachine(WorkflowState.COMPLETED)
        wsm.reset(WorkflowState.QUEUED)
        assert wsm.state == WorkflowState.QUEUED

    def test_full_lifecycle(self):
        wsm = WorkflowStateMachine()
        wsm.transition_to(WorkflowState.QUEUED)
        wsm.transition_to(WorkflowState.RUNNING)
        wsm.transition_to(WorkflowState.COMPLETED)
        assert wsm.is_terminal()

    def test_failure_lifecycle(self):
        wsm = WorkflowStateMachine()
        wsm.transition_to(WorkflowState.QUEUED)
        wsm.transition_to(WorkflowState.RUNNING)
        wsm.transition_to(WorkflowState.FAILED)
        wsm.transition_to(WorkflowState.RETRYING)
        wsm.transition_to(WorkflowState.RUNNING)
        wsm.transition_to(WorkflowState.COMPLETED)
        assert wsm.is_completed()

    def test_pause_resume_lifecycle(self):
        wsm = WorkflowStateMachine()
        wsm.transition_to(WorkflowState.QUEUED)
        wsm.transition_to(WorkflowState.RUNNING)
        wsm.transition_to(WorkflowState.PAUSED)
        wsm.transition_to(WorkflowState.RUNNING)
        wsm.transition_to(WorkflowState.COMPLETED)

    def test_terminal_states_correct(self):
        assert WorkflowState.COMPLETED in TERMINAL_WORKFLOW_STATES
        assert WorkflowState.CANCELLED in TERMINAL_WORKFLOW_STATES
        assert WorkflowState.ARCHIVED in TERMINAL_WORKFLOW_STATES
        assert WorkflowState.RUNNING not in TERMINAL_WORKFLOW_STATES


class TestStageStateMachine:
    def test_initial_state(self):
        ssm = StageStateMachine()
        assert ssm.state == StageState.PENDING

    def test_valid_transition(self):
        ssm = StageStateMachine()
        ssm.transition_to(StageState.READY)
        ssm.transition_to(StageState.RUNNING)
        ssm.transition_to(StageState.COMPLETED)
        assert ssm.state == StageState.COMPLETED

    def test_illegal_transition_raises(self):
        ssm = StageStateMachine(StageState.PENDING)
        with pytest.raises(StageStateError):
            ssm.transition_to(StageState.COMPLETED)

    def test_can_transition_to_true(self):
        ssm = StageStateMachine(StageState.PENDING)
        assert ssm.can_transition_to(StageState.READY) == True

    def test_can_transition_to_false(self):
        ssm = StageStateMachine(StageState.COMPLETED)
        assert ssm.can_transition_to(StageState.RUNNING) == False

    def test_is_terminal(self):
        ssm = StageStateMachine(StageState.COMPLETED)
        assert ssm.is_terminal() == True
        ssm2 = StageStateMachine(StageState.RUNNING)
        assert ssm2.is_terminal() == False

    def test_is_completed(self):
        ssm = StageStateMachine(StageState.COMPLETED)
        assert ssm.is_completed() == True
        ssm2 = StageStateMachine(StageState.FAILED)
        assert ssm2.is_completed() == False

    def test_is_failed(self):
        ssm = StageStateMachine(StageState.FAILED)
        assert ssm.is_failed() == True

    def test_retry_lifecycle(self):
        ssm = StageStateMachine()
        ssm.transition_to(StageState.READY)
        ssm.transition_to(StageState.RUNNING)
        ssm.transition_to(StageState.FAILED)
        ssm.transition_to(StageState.RETRYING)
        ssm.transition_to(StageState.RUNNING)
        ssm.transition_to(StageState.COMPLETED)
        assert ssm.is_completed()

    def test_timeout_lifecycle(self):
        ssm = StageStateMachine()
        ssm.transition_to(StageState.READY)
        ssm.transition_to(StageState.RUNNING)
        ssm.transition_to(StageState.TIMEOUT)
        assert ssm.state == StageState.TIMEOUT

    def test_skipped_state(self):
        ssm = StageStateMachine()
        ssm.transition_to(StageState.SKIPPED)
        assert ssm.is_terminal()

    def test_terminal_states_correct(self):
        assert StageState.COMPLETED in TERMINAL_STAGE_STATES
        assert StageState.SKIPPED in TERMINAL_STAGE_STATES
        assert StageState.RUNNING not in TERMINAL_STAGE_STATES
