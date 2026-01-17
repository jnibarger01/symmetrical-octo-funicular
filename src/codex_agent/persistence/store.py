"""Persistence layer - SQLite + JSON storage."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..core.models import (
    AuditEvent,
    Checkpoint,
    EventType,
    LifecycleState,
    StateTransition,
    Task,
)

logger = logging.getLogger(__name__)


class StateStore:
    """
    State persistence using SQLite and JSON files.

    Handles lifecycle state, tasks, audit events, and checkpoints.
    """

    SCHEMA_SQL = """
    -- Core state
    CREATE TABLE IF NOT EXISTS lifecycle_state (
        id INTEGER PRIMARY KEY,
        current_state TEXT NOT NULL,
        previous_state TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Task tracking
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        data JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Audit log
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_type TEXT NOT NULL,
        event_data JSON NOT NULL,
        actor TEXT NOT NULL
    );

    -- Checkpoints
    CREATE TABLE IF NOT EXISTS checkpoints (
        id TEXT PRIMARY KEY,
        state_snapshot JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- State transitions
    CREATE TABLE IF NOT EXISTS state_transitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_state TEXT NOT NULL,
        to_state TEXT NOT NULL,
        trigger TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSON
    );
    """

    def __init__(self, db_path: Path, tasks_dir: Path) -> None:
        """
        Initialize the state store.

        Args:
            db_path: Path to SQLite database file
            tasks_dir: Directory for task JSON files
        """
        self.db_path = db_path
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        # Initialize lifecycle state if needed
        self._init_lifecycle_state()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(self.SCHEMA_SQL)
        conn.commit()
        conn.close()

        logger.info(f"Database initialized at {self.db_path}")

    def _init_lifecycle_state(self) -> None:
        """Initialize lifecycle state if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM lifecycle_state")
        count = cursor.fetchone()[0]

        if count == 0:
            cursor.execute(
                "INSERT INTO lifecycle_state (current_state, previous_state) VALUES (?, ?)",
                (LifecycleState.IDLE.value, None),
            )
            conn.commit()
            logger.info("Initialized lifecycle state to IDLE")

        conn.close()

    # Lifecycle State Methods

    def get_current_state(self) -> LifecycleState:
        """Get current lifecycle state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT current_state FROM lifecycle_state WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            return LifecycleState(row[0])
        return LifecycleState.IDLE

    def update_state(self, new_state: LifecycleState) -> None:
        """Update lifecycle state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE lifecycle_state
            SET previous_state = current_state,
                current_state = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (new_state.value,),
        )

        conn.commit()
        conn.close()

        logger.info(f"Updated lifecycle state to {new_state.value}")

    def save_transition(self, transition: StateTransition) -> None:
        """Save a state transition."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO state_transitions (from_state, to_state, trigger, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                transition.from_state.value,
                transition.to_state.value,
                transition.trigger,
                transition.timestamp,
                json.dumps(transition.metadata),
            ),
        )

        conn.commit()
        conn.close()

    def get_transition_history(self, limit: int = 100) -> list[StateTransition]:
        """Get state transition history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT from_state, to_state, trigger, timestamp, metadata
            FROM state_transitions
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )

        transitions = []
        for row in cursor.fetchall():
            transitions.append(
                StateTransition(
                    from_state=LifecycleState(row[0]),
                    to_state=LifecycleState(row[1]),
                    trigger=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    metadata=json.loads(row[4]) if row[4] else {},
                )
            )

        conn.close()
        return transitions

    # Task Methods

    def save_task(self, task: Task) -> None:
        """Save or update a task."""
        # Save to SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        task_data = task.model_dump_json()

        cursor.execute(
            """
            INSERT OR REPLACE INTO tasks (id, type, status, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (task.id, task.type.value, task.status.value, task_data, task.created_at),
        )

        conn.commit()
        conn.close()

        # Save detailed JSON to file
        task_file = self.tasks_dir / f"{task.id}.json"
        with open(task_file, "w") as f:
            json.dump(task.model_dump(), f, indent=2, default=str)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        task_file = self.tasks_dir / f"{task_id}.json"

        if not task_file.exists():
            return None

        try:
            with open(task_file) as f:
                data = json.load(f)
                return Task(**data)
        except Exception as e:
            logger.error(f"Failed to load task {task_id}: {e}")
            return None

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks."""
        tasks = []

        for task_file in self.tasks_dir.glob("*.json"):
            try:
                with open(task_file) as f:
                    data = json.load(f)
                    tasks.append(Task(**data))
            except Exception as e:
                logger.warning(f"Failed to load task from {task_file}: {e}")

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        # Delete from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        # Delete JSON file
        task_file = self.tasks_dir / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
            return True

        return False

    # Audit Event Methods

    def save_audit_event(self, event: AuditEvent) -> None:
        """Save an audit event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO audit_log (timestamp, event_type, event_data, actor)
            VALUES (?, ?, ?, ?)
            """,
            (event.timestamp, event.event_type.value, json.dumps(event.event_data), event.actor),
        )

        conn.commit()
        conn.close()

    def get_audit_events(
        self, event_type: Optional[EventType] = None, limit: int = 100
    ) -> list[AuditEvent]:
        """Get audit events."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if event_type:
            cursor.execute(
                """
                SELECT id, timestamp, event_type, event_data, actor
                FROM audit_log
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (event_type.value, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, timestamp, event_type, event_data, actor
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

        events = []
        for row in cursor.fetchall():
            events.append(
                AuditEvent(
                    id=str(row[0]),
                    timestamp=datetime.fromisoformat(row[1]),
                    event_type=EventType(row[2]),
                    event_data=json.loads(row[3]),
                    actor=row[4],
                )
            )

        conn.close()
        return events

    # Checkpoint Methods

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO checkpoints (id, state_snapshot, created_at)
            VALUES (?, ?, ?)
            """,
            (checkpoint.id, checkpoint.model_dump_json(), checkpoint.created_at),
        )

        conn.commit()
        conn.close()

        logger.info(f"Saved checkpoint {checkpoint.id}")

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT state_snapshot FROM checkpoints WHERE id = ?", (checkpoint_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Checkpoint(**json.loads(row[0]))
        return None

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT state_snapshot FROM checkpoints ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return Checkpoint(**json.loads(row[0]))
        return None

    def cleanup_old_checkpoints(self, keep_count: int = 10) -> int:
        """
        Delete old checkpoints, keeping only the most recent N.

        Args:
            keep_count: Number of checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM checkpoints
            WHERE id NOT IN (
                SELECT id FROM checkpoints
                ORDER BY created_at DESC
                LIMIT ?
            )
            """,
            (keep_count,),
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleaned up {deleted} old checkpoints")
        return deleted
