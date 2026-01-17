"""Task DAG Engine - Dependency management and execution planning."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Optional

from ..core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class DAGCycleError(Exception):
    """Raised when a cycle is detected in the task DAG."""

    pass


class DAGValidationError(Exception):
    """Raised when the DAG fails validation."""

    pass


class TaskDAG:
    """
    Directed Acyclic Graph for task dependency management.

    Handles task ordering, dependency validation, and execution planning.
    """

    def __init__(self) -> None:
        """Initialize the task DAG."""
        self.tasks: dict[str, Task] = {}
        self._adjacency_list: dict[str, list[str]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)

    def add_task(self, task: Task) -> None:
        """
        Add a task to the DAG.

        Args:
            task: Task to add

        Raises:
            DAGValidationError: If adding task would create invalid state
        """
        if task.id in self.tasks:
            logger.warning(f"Task {task.id} already exists in DAG, replacing")

        self.tasks[task.id] = task

        # Build adjacency lists
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                logger.warning(f"Task {task.id} depends on unknown task {dep_id}")
            self._adjacency_list[dep_id].append(task.id)
            self._reverse_adjacency[task.id].append(dep_id)

        # Validate no cycles
        if self._has_cycle():
            # Remove the task we just added
            del self.tasks[task.id]
            raise DAGCycleError(f"Adding task {task.id} would create a cycle")

    def remove_task(self, task_id: str) -> None:
        """
        Remove a task from the DAG.

        Args:
            task_id: ID of task to remove
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found in DAG")
            return

        task = self.tasks[task_id]

        # Remove from adjacency lists
        for dep_id in task.dependencies:
            if task_id in self._adjacency_list[dep_id]:
                self._adjacency_list[dep_id].remove(task_id)

        # Remove reverse adjacency
        for dependent_id in self._adjacency_list[task_id]:
            if task_id in self._reverse_adjacency[dependent_id]:
                self._reverse_adjacency[dependent_id].remove(task_id)

        del self.tasks[task_id]
        if task_id in self._adjacency_list:
            del self._adjacency_list[task_id]
        if task_id in self._reverse_adjacency:
            del self._reverse_adjacency[task_id]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks in the DAG."""
        return list(self.tasks.values())

    def get_ready_tasks(self) -> list[Task]:
        """
        Get tasks that are ready to execute.

        A task is ready if:
        - Status is PENDING
        - All dependencies are COMPLETED
        - Task is not blocked

        Returns:
            List of ready tasks, sorted by priority
        """
        ready: list[Task] = []

        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_completed = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )

            if deps_completed:
                ready.append(task)

        # Sort by priority (lower number = higher priority)
        ready.sort(key=lambda t: (t.priority, t.created_at))
        return ready

    def get_next_task(self) -> Optional[Task]:
        """
        Get the next task to execute.

        Returns:
            Highest priority ready task, or None if no tasks are ready
        """
        ready_tasks = self.get_ready_tasks()
        return ready_tasks[0] if ready_tasks else None

    def get_blocked_tasks(self) -> list[Task]:
        """
        Get tasks that are blocked.

        A task is blocked if it has dependencies that are FAILED.

        Returns:
            List of blocked tasks
        """
        blocked: list[Task] = []

        for task in self.tasks.values():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]:
                continue

            # Check if any dependency is failed
            has_failed_dep = any(
                self.tasks[dep_id].status == TaskStatus.FAILED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )

            if has_failed_dep:
                task.status = TaskStatus.BLOCKED
                blocked.append(task)

        return blocked

    def topological_sort(self) -> list[Task]:
        """
        Perform topological sort on the DAG.

        Returns:
            Tasks in dependency order (dependencies first)

        Raises:
            DAGCycleError: If DAG contains a cycle
        """
        # Kahn's algorithm
        in_degree = {task_id: len(deps) for task_id, deps in self._reverse_adjacency.items()}

        # Add tasks with no dependencies
        for task_id in self.tasks:
            if task_id not in in_degree:
                in_degree[task_id] = 0

        # Queue of tasks with no dependencies
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        result: list[Task] = []

        while queue:
            task_id = queue.popleft()
            result.append(self.tasks[task_id])

            # Reduce in-degree for dependent tasks
            for dependent_id in self._adjacency_list[task_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        if len(result) != len(self.tasks):
            raise DAGCycleError("DAG contains a cycle")

        return result

    def _has_cycle(self) -> bool:
        """
        Check if the DAG contains a cycle using DFS.

        Returns:
            True if cycle detected
        """
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for dependent_id in self._adjacency_list[task_id]:
                if dependent_id not in visited:
                    if dfs(dependent_id):
                        return True
                elif dependent_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def get_task_dependencies(self, task_id: str) -> list[Task]:
        """Get all direct dependencies of a task."""
        task = self.tasks.get(task_id)
        if not task:
            return []

        return [self.tasks[dep_id] for dep_id in task.dependencies if dep_id in self.tasks]

    def get_task_dependents(self, task_id: str) -> list[Task]:
        """Get all tasks that depend on this task."""
        dependent_ids = self._adjacency_list[task_id]
        return [self.tasks[dep_id] for dep_id in dependent_ids if dep_id in self.tasks]

    def get_progress(self) -> dict[str, int]:
        """
        Get execution progress statistics.

        Returns:
            Dictionary with task counts by status
        """
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
            "skipped": 0,
        }

        for task in self.tasks.values():
            stats[task.status.value] += 1

        return stats

    def is_complete(self) -> bool:
        """Check if all tasks are completed or terminal state."""
        terminal_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED}
        return all(task.status in terminal_states for task in self.tasks.values())

    def validate(self) -> list[str]:
        """
        Validate the DAG for common issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check for cycles
        if self._has_cycle():
            errors.append("DAG contains a cycle")

        # Check for missing dependencies
        for task in self.tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    errors.append(f"Task {task.id} depends on non-existent task {dep_id}")

        # Check for unreachable tasks (no path from any root)
        try:
            sorted_tasks = self.topological_sort()
            if len(sorted_tasks) != len(self.tasks):
                errors.append("Some tasks are unreachable")
        except DAGCycleError:
            pass  # Already caught above

        return errors

    def __len__(self) -> int:
        """Get number of tasks in DAG."""
        return len(self.tasks)

    def __repr__(self) -> str:
        """String representation."""
        return f"TaskDAG(tasks={len(self.tasks)}, edges={sum(len(deps) for deps in self._adjacency_list.values())})"
