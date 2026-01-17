"""Policy Engine - Security, quality, and safety validation."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..core.config import Config
from ..core.models import PolicySeverity, PolicyType, PolicyViolation

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Policy engine for validating actions against security, quality, and safety rules.

    Enforces policies at various checkpoints in the lifecycle.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the policy engine.

        Args:
            config: Configuration object
        """
        self.config = config
        self._secret_patterns = [
            re.compile(pattern) for pattern in config.policies.security.secret_patterns
        ]

    def validate_all(self, context: dict[str, Any]) -> list[PolicyViolation]:
        """
        Run all policy validations.

        Args:
            context: Validation context (files, diffs, etc.)

        Returns:
            List of policy violations
        """
        violations: list[PolicyViolation] = []

        violations.extend(self.validate_security(context))
        violations.extend(self.validate_quality(context))
        violations.extend(self.validate_safety(context))

        return violations

    def validate_security(self, context: dict[str, Any]) -> list[PolicyViolation]:
        """
        Validate security policies.

        Args:
            context: Validation context

        Returns:
            List of security violations
        """
        violations: list[PolicyViolation] = []

        # Secret scanning
        if self.config.policies.security.secret_scanning:
            violations.extend(self._scan_for_secrets(context))

        return violations

    def validate_quality(self, context: dict[str, Any]) -> list[PolicyViolation]:
        """
        Validate quality policies.

        Args:
            context: Validation context

        Returns:
            List of quality violations
        """
        violations: list[PolicyViolation] = []

        # Test coverage
        if self.config.policies.quality.test_coverage_enabled:
            coverage = context.get("test_coverage", 0)
            min_coverage = self.config.policies.quality.minimum_coverage_percent

            if coverage < min_coverage:
                violations.append(
                    PolicyViolation(
                        policy_type=PolicyType.QUALITY,
                        policy_name="test_coverage",
                        severity=PolicySeverity.WARNING
                        if not self.config.policies.quality.coverage_blocking
                        else PolicySeverity.ERROR,
                        message=f"Test coverage {coverage}% is below minimum {min_coverage}%",
                        blocking=self.config.policies.quality.coverage_blocking,
                        context={"coverage": coverage, "minimum": min_coverage},
                    )
                )

        return violations

    def validate_safety(self, context: dict[str, Any]) -> list[PolicyViolation]:
        """
        Validate safety policies.

        Args:
            context: Validation context

        Returns:
            List of safety violations
        """
        violations: list[PolicyViolation] = []

        # File count limit
        modified_files = context.get("modified_files", [])
        max_files = self.config.policies.safety.max_files_per_task

        if len(modified_files) > max_files:
            violations.append(
                PolicyViolation(
                    policy_type=PolicyType.SAFETY,
                    policy_name="max_files_per_task",
                    severity=PolicySeverity.ERROR,
                    message=f"Task modifies {len(modified_files)} files, exceeds limit of {max_files}",
                    blocking=True,
                    context={"file_count": len(modified_files), "max": max_files},
                )
            )

        # Diff size limit
        diff_lines = context.get("diff_lines", 0)
        max_diff = self.config.policies.safety.max_diff_lines

        if diff_lines > max_diff:
            violations.append(
                PolicyViolation(
                    policy_type=PolicyType.SAFETY,
                    policy_name="max_diff_lines",
                    severity=PolicySeverity.ERROR,
                    message=f"Diff has {diff_lines} lines, exceeds limit of {max_diff}",
                    blocking=True,
                    context={"diff_lines": diff_lines, "max": max_diff},
                )
            )

        # Prohibited paths
        for file_path in modified_files:
            if self._is_prohibited_path(file_path):
                violations.append(
                    PolicyViolation(
                        policy_type=PolicyType.SAFETY,
                        policy_name="prohibited_paths",
                        severity=PolicySeverity.CRITICAL,
                        message=f"Attempted to modify prohibited path: {file_path}",
                        blocking=True,
                        context={"file": file_path},
                    )
                )

        return violations

    def _scan_for_secrets(self, context: dict[str, Any]) -> list[PolicyViolation]:
        """
        Scan for potential secrets in code.

        Args:
            context: Validation context

        Returns:
            List of secret violations
        """
        violations: list[PolicyViolation] = []
        files_content = context.get("files_content", {})

        for file_path, content in files_content.items():
            for pattern in self._secret_patterns:
                matches = pattern.finditer(content)
                for match in matches:
                    violations.append(
                        PolicyViolation(
                            policy_type=PolicyType.SECURITY,
                            policy_name="secret_scanning",
                            severity=PolicySeverity.CRITICAL,
                            message=f"Potential secret detected in {file_path}: {match.group()}",
                            blocking=True,
                            context={
                                "file": file_path,
                                "pattern": pattern.pattern,
                                "match": match.group(),
                            },
                        )
                    )

        return violations

    def _is_prohibited_path(self, file_path: str) -> bool:
        """
        Check if a file path is prohibited.

        Args:
            file_path: File path to check

        Returns:
            True if prohibited
        """
        path = Path(file_path)

        for pattern in self.config.policies.safety.prohibited_paths:
            # Simple glob matching
            if "*" in pattern:
                if path.match(pattern):
                    return True
            elif pattern in str(path):
                return True

        return False

    def is_blocking(self, violations: list[PolicyViolation]) -> bool:
        """
        Check if any violations are blocking.

        Args:
            violations: List of violations

        Returns:
            True if any violation is blocking
        """
        return any(v.blocking for v in violations)

    def get_by_severity(
        self, violations: list[PolicyViolation], min_severity: PolicySeverity
    ) -> list[PolicyViolation]:
        """
        Filter violations by minimum severity.

        Args:
            violations: All violations
            min_severity: Minimum severity level

        Returns:
            Filtered violations
        """
        severity_order = {
            PolicySeverity.INFO: 0,
            PolicySeverity.WARNING: 1,
            PolicySeverity.ERROR: 2,
            PolicySeverity.CRITICAL: 3,
        }

        min_level = severity_order[min_severity]
        return [v for v in violations if severity_order[v.severity] >= min_level]

    def format_violations(self, violations: list[PolicyViolation]) -> str:
        """
        Format violations as human-readable text.

        Args:
            violations: List of violations

        Returns:
            Formatted string
        """
        if not violations:
            return "No policy violations found."

        lines = ["Policy Violations:", ""]

        for v in violations:
            icon = "🔴" if v.blocking else "⚠️"
            lines.append(f"{icon} [{v.severity.upper()}] {v.policy_type.upper()}/{v.policy_name}")
            lines.append(f"   {v.message}")
            if v.context:
                lines.append(f"   Context: {v.context}")
            lines.append("")

        return "\n".join(lines)
