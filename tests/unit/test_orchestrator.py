"""Tests for the Orchestrator state machine."""

import pytest

from codex_agent.core.config import Config, ProjectConfig
from codex_agent.core.models import LifecycleState
from codex_agent.core.orchestrator import Orchestrator, StateTransitionError


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(project=ProjectConfig(name="test-project", stack="python-postgres"))


@pytest.fixture
def orchestrator(config):
    """Create an orchestrator instance."""
    return Orchestrator(config)


def test_initial_state(orchestrator):
    """Test that orchestrator starts in IDLE state."""
    assert orchestrator.get_state() == LifecycleState.IDLE
    assert orchestrator.previous_state is None


def test_valid_transition(orchestrator):
    """Test a valid state transition."""
    transition = orchestrator.transition(LifecycleState.PLANNING, trigger="test")

    assert orchestrator.get_state() == LifecycleState.PLANNING
    assert orchestrator.previous_state == LifecycleState.IDLE
    assert transition.from_state == LifecycleState.IDLE
    assert transition.to_state == LifecycleState.PLANNING
    assert transition.trigger == "test"


def test_invalid_transition(orchestrator):
    """Test that invalid transitions are rejected."""
    with pytest.raises(StateTransitionError):
        orchestrator.transition(LifecycleState.BUILDING, trigger="test")


def test_transition_chain(orchestrator):
    """Test a chain of valid transitions."""
    orchestrator.transition(LifecycleState.PLANNING)
    orchestrator.transition(LifecycleState.SCAFFOLDING)
    orchestrator.transition(LifecycleState.BUILDING)

    assert orchestrator.get_state() == LifecycleState.BUILDING
    assert len(orchestrator.transition_history) == 3


def test_can_transition(orchestrator):
    """Test can_transition check."""
    assert orchestrator.can_transition(LifecycleState.PLANNING)
    assert not orchestrator.can_transition(LifecycleState.BUILDING)

    orchestrator.transition(LifecycleState.PLANNING)
    assert orchestrator.can_transition(LifecycleState.SCAFFOLDING)
    assert not orchestrator.can_transition(LifecycleState.PLANNING)


def test_get_allowed_transitions(orchestrator):
    """Test getting allowed transitions."""
    allowed = orchestrator.get_allowed_transitions()
    assert LifecycleState.PLANNING in allowed
    assert len(allowed) == 1

    orchestrator.transition(LifecycleState.PLANNING)
    allowed = orchestrator.get_allowed_transitions()
    assert LifecycleState.SCAFFOLDING in allowed
    assert LifecycleState.FAILED in allowed


def test_reset(orchestrator):
    """Test reset functionality."""
    # Transition to FAILED state
    orchestrator.transition(LifecycleState.PLANNING)
    orchestrator.transition(LifecycleState.FAILED)

    # Reset should go back to IDLE
    orchestrator.reset()
    assert orchestrator.get_state() == LifecycleState.IDLE
    assert orchestrator.current_task is None


def test_is_terminal_state(orchestrator):
    """Test terminal state detection."""
    assert orchestrator.is_terminal_state()  # IDLE is terminal

    orchestrator.transition(LifecycleState.PLANNING)
    assert not orchestrator.is_terminal_state()

    orchestrator.transition(LifecycleState.FAILED)
    assert orchestrator.is_terminal_state()  # FAILED is terminal
