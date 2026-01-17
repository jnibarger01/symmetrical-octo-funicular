"""Base provider interfaces and protocols."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class HealthStatus(str, Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Health check result."""

    status: HealthStatus
    latency_ms: int
    message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class Provider(ABC):
    """Base provider interface."""

    @abstractmethod
    async def health_check(self) -> HealthCheck:
        """Check provider health."""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the provider."""
        pass


# Git Provider Types


@dataclass
class Repo:
    """Repository representation."""

    name: str
    owner: str
    url: str
    default_branch: str = "main"
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize metadata."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Branch:
    """Branch representation."""

    name: str
    sha: str
    repo: Repo


@dataclass
class PullRequest:
    """Pull request specification."""

    title: str
    body: str
    head_branch: str
    base_branch: str
    draft: bool = False


@dataclass
class PR:
    """Created pull request."""

    number: int
    url: str
    title: str
    state: str
    created_at: datetime


@dataclass
class MergeResult:
    """Merge operation result."""

    success: bool
    sha: Optional[str] = None
    message: Optional[str] = None


class GitProvider(Provider):
    """Git hosting provider interface."""

    @abstractmethod
    async def create_repo(self, name: str, **config: Any) -> Repo:
        """Create a new repository."""
        pass

    @abstractmethod
    async def create_branch(self, repo: Repo, name: str, from_branch: str = "main") -> Branch:
        """Create a new branch."""
        pass

    @abstractmethod
    async def create_pr(self, repo: Repo, pr: PullRequest) -> PR:
        """Create a pull request."""
        pass

    @abstractmethod
    async def merge_pr(self, repo: Repo, pr_number: int) -> MergeResult:
        """Merge a pull request."""
        pass

    @abstractmethod
    async def get_pr_status(self, repo: Repo, pr_number: int) -> str:
        """Get PR status."""
        pass


# CI Provider Types


@dataclass
class Build:
    """CI build representation."""

    id: str
    number: int
    status: str
    url: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BuildStatus(str, Enum):
    """Build status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class CIProvider(Provider):
    """CI/CD provider interface."""

    @abstractmethod
    async def trigger_build(self, repo: Repo, ref: str, **params: Any) -> Build:
        """Trigger a CI build."""
        pass

    @abstractmethod
    async def get_build_status(self, build_id: str) -> BuildStatus:
        """Get build status."""
        pass

    @abstractmethod
    async def get_build_logs(self, build_id: str) -> str:
        """Get build logs."""
        pass

    @abstractmethod
    async def cancel_build(self, build_id: str) -> bool:
        """Cancel a running build."""
        pass


# Hosting Provider Types


@dataclass
class Artifact:
    """Build artifact."""

    name: str
    path: str
    size_bytes: int
    hash: str


@dataclass
class Environment:
    """Deployment environment."""

    name: str
    url: Optional[str] = None
    config: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize config."""
        if self.config is None:
            self.config = {}


@dataclass
class Deployment:
    """Deployment representation."""

    id: str
    environment: str
    status: str
    url: Optional[str] = None
    deployed_at: Optional[datetime] = None


class DeploymentStatus(str, Enum):
    """Deployment status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    ROLLED_BACK = "rolled_back"


class HostingProvider(Provider):
    """Hosting provider interface."""

    @abstractmethod
    async def deploy(self, artifact: Artifact, env: Environment, **params: Any) -> Deployment:
        """Deploy an artifact."""
        pass

    @abstractmethod
    async def rollback(self, deployment_id: str) -> Deployment:
        """Rollback a deployment."""
        pass

    @abstractmethod
    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        """Get deployment status."""
        pass

    @abstractmethod
    async def get_logs(self, deployment_id: str, lines: int = 100) -> str:
        """Get deployment logs."""
        pass


# Secrets Provider


@dataclass
class Secret:
    """Secret representation."""

    key: str
    value: str
    created_at: datetime
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize metadata."""
        if self.metadata is None:
            self.metadata = {}


class SecretsProvider(Provider):
    """Secrets management provider interface."""

    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value."""
        pass

    @abstractmethod
    async def set_secret(self, key: str, value: str) -> None:
        """Set a secret value."""
        pass

    @abstractmethod
    async def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        pass

    @abstractmethod
    async def list_secrets(self) -> list[str]:
        """List secret keys."""
        pass
