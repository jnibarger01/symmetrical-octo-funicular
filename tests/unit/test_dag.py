"""Tests for the Task DAG Engine."""

import pytest

from codex_agent.core.models import Task, TaskStatus, TaskType
from codex_agent.dag.engine import DAGCycleError, TaskDAG


@pytest.fixture
def dag():
    """Create a DAG instance."""
    return TaskDAG()


@pytest.fixture
def sample_tasks():
    """Create sample tasks."""
    return [
        Task(id="task1", type=TaskType.SCAFFOLD, title="Task 1", description="First task"),
        Task(
            id="task2",
            type=TaskType.IMPLEMENT,
            title="Task 2",
            description="Second task",
            dependencies=["task1"],
        ),
        Task(
            id="task3",
            type=TaskType.TEST,
            title="Task 3",
            description="Third task",
            dependencies=["task2"],
        ),
    ]


def test_add_task(dag, sample_tasks):
    """Test adding tasks to DAG."""
    dag.add_task(sample_tasks[0])
    assert len(dag) == 1
    assert dag.get_task("task1") == sample_tasks[0]


def test_add_tasks_with_dependencies(dag, sample_tasks):
    """Test adding tasks with dependencies."""
    for task in sample_tasks:
        dag.add_task(task)

    assert len(dag) == 3
    assert len(dag.get_task_dependencies("task2")) == 1
    assert len(dag.get_task_dependencies("task3")) == 1


def test_cycle_detection(dag):
    """Test that cycles are detected."""
    task1 = Task(
        id="task1",
        type=TaskType.IMPLEMENT,
        title="Task 1",
        description="First",
        dependencies=["task2"],
    )
    task2 = Task(
        id="task2",
        type=TaskType.IMPLEMENT,
        title="Task 2",
        description="Second",
        dependencies=["task1"],
    )

    dag.add_task(task1)
    with pytest.raises(DAGCycleError):
        dag.add_task(task2)


def test_topological_sort(dag, sample_tasks):
    """Test topological sorting."""
    for task in sample_tasks:
        dag.add_task(task)

    sorted_tasks = dag.topological_sort()
    task_ids = [t.id for t in sorted_tasks]

    # task1 should come before task2, task2 before task3
    assert task_ids.index("task1") < task_ids.index("task2")
    assert task_ids.index("task2") < task_ids.index("task3")


def test_get_ready_tasks(dag, sample_tasks):
    """Test getting ready tasks."""
    for task in sample_tasks:
        dag.add_task(task)

    # Initially, only task1 should be ready
    ready = dag.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task1"

    # Complete task1, task2 should become ready
    dag.get_task("task1").status = TaskStatus.COMPLETED
    ready = dag.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task2"


def test_get_next_task(dag, sample_tasks):
    """Test getting the next task to execute."""
    for task in sample_tasks:
        dag.add_task(task)

    next_task = dag.get_next_task()
    assert next_task.id == "task1"

    # Complete task1
    dag.get_task("task1").status = TaskStatus.COMPLETED
    next_task = dag.get_next_task()
    assert next_task.id == "task2"


def test_priority_ordering(dag):
    """Test that tasks are ordered by priority."""
    high_priority = Task(
        id="high",
        type=TaskType.IMPLEMENT,
        title="High",
        description="High priority",
        priority=1,
    )
    low_priority = Task(
        id="low",
        type=TaskType.IMPLEMENT,
        title="Low",
        description="Low priority",
        priority=10,
    )

    dag.add_task(low_priority)
    dag.add_task(high_priority)

    next_task = dag.get_next_task()
    assert next_task.id == "high"  # Lower number = higher priority


def test_get_progress(dag, sample_tasks):
    """Test progress tracking."""
    for task in sample_tasks:
        dag.add_task(task)

    progress = dag.get_progress()
    assert progress["total"] == 3
    assert progress["pending"] == 3
    assert progress["completed"] == 0

    # Complete a task
    dag.get_task("task1").status = TaskStatus.COMPLETED
    progress = dag.get_progress()
    assert progress["completed"] == 1
    assert progress["pending"] == 2


def test_is_complete(dag, sample_tasks):
    """Test completion detection."""
    for task in sample_tasks:
        dag.add_task(task)

    assert not dag.is_complete()

    # Complete all tasks
    for task_id in ["task1", "task2", "task3"]:
        dag.get_task(task_id).status = TaskStatus.COMPLETED

    assert dag.is_complete()


def test_remove_task(dag, sample_tasks):
    """Test removing tasks."""
    for task in sample_tasks:
        dag.add_task(task)

    dag.remove_task("task2")
    assert len(dag) == 2
    assert dag.get_task("task2") is None
