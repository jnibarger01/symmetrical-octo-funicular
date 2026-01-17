"""Configuration management for Codex Lifecycle Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration."""

    provider: str = Field(default="openai", description="LLM provider (openai, anthropic, etc.)")
    model: str = Field(default="gpt-4-turbo", description="Model identifier")
    api_key: Optional[str] = Field(default=None, description="API key for the provider")
    max_tokens_per_request: int = Field(default=8000, description="Maximum tokens per request")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
    timeout_seconds: int = Field(default=120, description="Request timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    model_config = SettingsConfigDict(env_prefix="CODEX_LLM_")


class GitProviderConfig(BaseSettings):
    """Git provider configuration."""

    type: str = Field(default="github", description="Provider type (github, gitlab, etc.)")
    owner: Optional[str] = Field(default=None, description="Repository owner/org")
    repo: Optional[str] = Field(default=None, description="Repository name")
    token: Optional[str] = Field(default=None, description="Access token")
    base_url: Optional[str] = Field(default=None, description="API base URL for self-hosted")

    model_config = SettingsConfigDict(env_prefix="CODEX_GIT_")


class CIProviderConfig(BaseSettings):
    """CI provider configuration."""

    type: str = Field(default="github-actions", description="CI provider type")
    config_path: str = Field(default=".github/workflows", description="CI config file path")

    model_config = SettingsConfigDict(env_prefix="CODEX_CI_")


class HostingProviderConfig(BaseSettings):
    """Hosting provider configuration."""

    type: str = Field(default="railway", description="Hosting provider (railway, fly.io, vercel)")
    api_key: Optional[str] = Field(default=None, description="Provider API key")
    project_id: Optional[str] = Field(default=None, description="Project identifier")

    model_config = SettingsConfigDict(env_prefix="CODEX_HOSTING_")


class SecurityPolicyConfig(BaseSettings):
    """Security policy configuration."""

    secret_scanning: bool = Field(default=True, description="Enable secret scanning")
    secret_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)api[_-]?key",
            r"(?i)password\s*=",
            r"(?i)secret\s*=",
            r"(?i)token\s*=",
        ],
        description="Regex patterns for secret detection",
    )
    dependency_audit: bool = Field(default=True, description="Enable dependency audit")
    fail_on_severity: str = Field(default="high", description="Minimum severity to fail (low, medium, high, critical)")


class QualityPolicyConfig(BaseSettings):
    """Quality policy configuration."""

    test_coverage_enabled: bool = Field(default=True, description="Enable coverage checks")
    minimum_coverage_percent: int = Field(default=80, ge=0, le=100, description="Minimum test coverage")
    coverage_blocking: bool = Field(default=False, description="Block on coverage failure")
    lint_enabled: bool = Field(default=True, description="Enable linting")
    lint_tools: list[str] = Field(default_factory=lambda: ["ruff"], description="Linters to run")
    lint_blocking: bool = Field(default=True, description="Block on lint failures")


class SafetyPolicyConfig(BaseSettings):
    """Safety policy configuration."""

    max_files_per_task: int = Field(default=10, description="Maximum files modified per task")
    max_diff_lines: int = Field(default=500, description="Maximum diff lines per commit")
    prohibited_paths: list[str] = Field(
        default_factory=lambda: [".env", "secrets/", "*.pem", "*.key"],
        description="Paths that cannot be modified",
    )


class PolicyConfig(BaseSettings):
    """Combined policy configuration."""

    security: SecurityPolicyConfig = Field(default_factory=SecurityPolicyConfig)
    quality: QualityPolicyConfig = Field(default_factory=QualityPolicyConfig)
    safety: SafetyPolicyConfig = Field(default_factory=SafetyPolicyConfig)


class PreferencesConfig(BaseSettings):
    """User preferences."""

    auto_fix_lint: bool = Field(default=True, description="Automatically fix lint issues")
    require_tests: bool = Field(default=True, description="Require tests for new features")
    verbose_logging: bool = Field(default=False, description="Enable verbose logging")
    auto_commit: bool = Field(default=False, description="Automatically commit changes")
    auto_deploy: bool = Field(default=False, description="Automatically deploy after verification")


class ProjectConfig(BaseSettings):
    """Project-specific configuration."""

    name: str = Field(..., description="Project name")
    stack: str = Field(..., description="Technology stack (node-postgres, python-postgres, etc.)")
    version: str = Field(default="1", description="Config version")

    model_config = SettingsConfigDict(env_prefix="CODEX_PROJECT_")


class Config(BaseSettings):
    """Main configuration."""

    project: ProjectConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    git: GitProviderConfig = Field(default_factory=GitProviderConfig)
    ci: CIProviderConfig = Field(default_factory=CIProviderConfig)
    hosting: HostingProviderConfig = Field(default_factory=HostingProviderConfig)
    policies: PolicyConfig = Field(default_factory=PolicyConfig)
    preferences: PreferencesConfig = Field(default_factory=PreferencesConfig)

    # Paths
    codex_dir: Path = Field(default=Path(".codex"), description="Codex state directory")
    log_dir: Path = Field(default=Path(".codex/logs"), description="Log directory")
    cache_dir: Path = Field(default=Path(".codex/cache"), description="Cache directory")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def load_from_file(cls, config_path: Path) -> Config:
        """Load configuration from YAML file."""
        import yaml

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        import yaml

        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = self.model_dump(exclude_none=True)

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.codex_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.codex_dir / "tasks").mkdir(exist_ok=True)
        (self.codex_dir / "checkpoints").mkdir(exist_ok=True)
        (self.codex_dir / "artifacts").mkdir(exist_ok=True)
