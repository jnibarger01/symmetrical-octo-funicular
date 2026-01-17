"""Tests for core data models."""

import pytest
from pydantic import ValidationError

from codex_agent.core.models import (
    LifecycleState,
    Task,
    TaskStatus,
    TaskType,
    Verification,
)


def test_task_creation():
    """Test creating a task."""
    task = Task(
        type=TaskType.IMPLEMENT,
        title="Test Task",
        description="A test task",
    )

    assert task.type == TaskType.IMPLEMENT
    assert task.title == "Test Task"
    assert task.status == TaskStatus.PENDING
    assert task.priority == 100  # Default
    assert task.attempts == 0
    assert len(task.id) > 0  # ULID generated


def test_task_with_dependencies():
    """Test task with dependencies."""
    task = Task(
        type=TaskType.TEST,
        title="Test with deps",
        description="Task with dependencies",
        dependencies=["task1", "task2"],
    )

    assert len(task.dependencies) == 2
    assert "task1" in task.dependencies


def test_task_with_verification():
    """Test task with verification."""
    verification = Verification(
        type="test",
        command="pytest tests/",
        expected_output="All tests passed",
        timeout_seconds=300,
    )

    task = Task(
        type=TaskType.IMPLEMENT,
        title="Task with verification",
        description="Test",
        verification=verification,
    )

    assert task.verification is not None
    assert task.verification.type == "test"
    assert task.verification.timeout_seconds == 300


def test_task_complexity_validation():
    """Test that complexity is validated."""
    # Valid complexity
    task = Task(
        type=TaskType.IMPLEMENT,
        title="Test",
        description="Test",
        estimated_complexity=3,
    )
    assert task.estimated_complexity == 3

    # Invalid complexity should raise error
    with pytest.raises(ValidationError):
        Task(
            type=TaskType.IMPLEMENT,
            title="Test",
            description="Test",
            estimated_complexity=10,  # Out of range
        )


def test_lifecycle_state_enum():
    """Test lifecycle state enum."""
    assert LifecycleState.IDLE.value == "IDLE"
    assert LifecycleState.PLANNING.value == "PLANNING"
    assert LifecycleState.BUILDING.value == "BUILDING"


def test_task_type_enum():
    """Test task type enum."""
    assert TaskType.SCAFFOLD.value == "scaffold"
    assert TaskType.IMPLEMENT.value == "implement"
    assert TaskType.TEST.value == "test"


def test_task_status_enum():
    """Test task status enum."""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
