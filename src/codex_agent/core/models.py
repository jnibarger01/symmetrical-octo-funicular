"""Core data models for the Codex Lifecycle Agent."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from uuid import uuid4


class LifecycleState(str, Enum):
    """Lifecycle state machine states."""

    IDLE = "IDLE"
    PLANNING = "PLANNING"
    SCAFFOLDING = "SCAFFOLDING"
    BUILDING = "BUILDING"
    VERIFYING = "VERIFYING"
    DEPLOYING = "DEPLOYING"
    OBSERVING = "OBSERVING"
    MAINTAINING = "MAINTAINING"
    FAILED = "FAILED"


class TaskType(str, Enum):
    """Task types."""

    SCAFFOLD = "scaffold"
    IMPLEMENT = "implement"
    TEST = "test"
    REFACTOR = "refactor"
    DEPLOY = "deploy"
    MAINTAIN = "maintain"
    DOCUMENT = "document"


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class PolicyType(str, Enum):
    """Policy types."""

    SECURITY = "security"
    QUALITY = "quality"
    SAFETY = "safety"
    COMPLIANCE = "compliance"


class PolicySeverity(str, Enum):
    """Policy violation severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Audit event types."""

    STATE_CHANGE = "state_change"
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    POLICY_VIOLATION = "policy_violation"
    LLM_CALL = "llm_call"
    DEPLOYMENT = "deployment"
    ERROR = "error"


class Verification(BaseModel):
    """Task verification specification."""

    type: str = Field(..., description="Verification type (test, lint, build, manual)")
    command: Optional[str] = Field(None, description="Command to run for verification")
    expected_output: Optional[str] = Field(None, description="Expected output pattern")
    timeout_seconds: int = Field(300, description="Verification timeout in seconds")


class Task(BaseModel):
    """Task model representing a unit of work."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique task ID")
    type: TaskType = Field(..., description="Task type")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed task description")
    dependencies: list[str] = Field(default_factory=list, description="Task IDs to complete first")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status")
    priority: int = Field(default=100, description="Execution priority (lower = higher priority)")
    estimated_complexity: int = Field(default=3, ge=1, le=5, description="Complexity score 1-5")

    # Execution context
    target_files: list[str] = Field(default_factory=list, description="Files this task modifies")
    verification: Optional[Verification] = Field(None, description="Verification specification")

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = Field(default=0, description="Number of execution attempts")
    last_error: Optional[str] = Field(None, description="Last error message if failed")

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")

    class Config:
        """Pydantic config."""

        use_enum_values = True


class StateTransition(BaseModel):
    """State machine transition record."""

    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trigger: str = Field(..., description="What triggered this transition")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyViolation(BaseModel):
    """Policy violation record."""

    policy_type: PolicyType
    policy_name: str
    severity: PolicySeverity
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    blocking: bool = Field(default=True, description="Whether this blocks execution")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditEvent(BaseModel):
    """Audit log event."""

    id: str = Field(default_factory=lambda: str(ULID()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType
    actor: str = Field(..., description="Who/what triggered this event (user, agent, system)")
    event_data: dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    state: Optional[LifecycleState] = None

    class Config:
        """Pydantic config."""

        use_enum_values = True


class Symbol(BaseModel):
    """Code symbol extracted from a file."""

    name: str
    type: str = Field(..., description="function, class, variable, type")
    line_start: int
    line_end: int
    signature: Optional[str] = None


class FileIndex(BaseModel):
    """File index entry for repository inspector."""

    path: str
    language: str
    size_bytes: int
    hash: str = Field(..., description="Content hash for change detection")
    symbols: list[Symbol] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    exports: list[str] = Field(default_factory=list)
    last_modified: datetime = Field(default_factory=datetime.utcnow)


class Checkpoint(BaseModel):
    """State checkpoint for recovery."""

    id: str = Field(default_factory=lambda: str(ULID()))
    state: LifecycleState
    tasks: list[Task]
    current_task_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""

        use_enum_values = True


class LLMRequest(BaseModel):
    """LLM API request record."""

    id: str = Field(default_factory=lambda: str(ULID()))
    task_id: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    temperature: float = 0.1
    max_tokens: int = 4000
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM API response."""

    request_id: str
    content: str
    finish_reason: str
    cached: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
