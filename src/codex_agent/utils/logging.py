"""Logging and observability configuration."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class CodexLogger:
    """
    Centralized logging configuration for Codex Agent.

    Provides structured logging with file rotation and rich console output.
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        log_level: str = "INFO",
        verbose: bool = False,
    ) -> None:
        """
        Initialize logging configuration.

        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            verbose: Enable verbose logging
        """
        self.log_dir = log_dir or Path(".codex/logs")
        self.log_level = logging.DEBUG if verbose else getattr(logging, log_level.upper())
        self.verbose = verbose

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        self._configure_root_logger()

    def _configure_root_logger(self) -> None:
        """Configure the root logger with handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler with Rich
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=self.verbose,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=self.verbose,
        )
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter("%(message)s", datefmt="[%X]")
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler for all logs
        log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler
        error_log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_errors.log"
        error_file_handler = logging.FileHandler(error_log_file, encoding="utf-8")
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_file_handler)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Logger name (usually __name__)

        Returns:
            Logger instance
        """
        return logging.getLogger(name)


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    verbose: bool = False,
) -> CodexLogger:
    """
    Set up logging for the application.

    Args:
        log_dir: Directory for log files
        log_level: Logging level
        verbose: Enable verbose logging

    Returns:
        Configured CodexLogger instance
    """
    return CodexLogger(log_dir=log_dir, log_level=log_level, verbose=verbose)


class AuditLogger:
    """
    Audit logger for compliance and security events.

    Separate from operational logging, with longer retention.
    """

    def __init__(self, audit_file: Path) -> None:
        """
        Initialize audit logger.

        Args:
            audit_file: Path to audit log file
        """
        self.audit_file = audit_file
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure audit logger
        self.logger = logging.getLogger("codex.audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # File handler for audit events
        handler = logging.FileHandler(audit_file, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s - AUDIT - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, event_type: str, details: dict) -> None:
        """
        Log an audit event.

        Args:
            event_type: Type of event (e.g., 'state_change', 'deployment')
            details: Event details as dictionary
        """
        import json

        message = f"{event_type}: {json.dumps(details, default=str)}"
        self.logger.info(message)


class MetricsCollector:
    """
    Simple metrics collector for tracking agent performance.

    In production, this could be replaced with Prometheus or similar.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.metrics: dict[str, list[float]] = {}
        self.counters: dict[str, int] = {}

    def record_duration(self, metric_name: str, duration_ms: float) -> None:
        """Record a duration metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(duration_ms)

    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[counter_name] = self.counters.get(counter_name, 0) + value

    def get_stats(self, metric_name: str) -> dict[str, float]:
        """Get statistics for a metric."""
        if metric_name not in self.metrics:
            return {}

        values = self.metrics[metric_name]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    def get_counter(self, counter_name: str) -> int:
        """Get counter value."""
        return self.counters.get(counter_name, 0)

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.counters.clear()


# Global metrics instance
metrics = MetricsCollector()
