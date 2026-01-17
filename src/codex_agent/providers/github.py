"""GitHub provider implementation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from .base import (
    Branch,
    GitProvider,
    HealthCheck,
    HealthStatus,
    MergeResult,
    PR,
    PullRequest,
    Repo,
)

logger = logging.getLogger(__name__)


class GitHubProvider(GitProvider):
    """GitHub API provider implementation."""

    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        """
        Initialize GitHub provider.

        Args:
            token: GitHub personal access token
            base_url: API base URL (for GitHub Enterprise)
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def health_check(self) -> HealthCheck:
        """Check GitHub API health."""
        start = datetime.utcnow()

        try:
            response = await self.client.get(f"{self.base_url}/")
            latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

            if response.status_code == 200:
                return HealthCheck(
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency_ms,
                    message="GitHub API is healthy",
                )
            else:
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency_ms,
                    message=f"GitHub API returned {response.status_code}",
                )
        except Exception as e:
            latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=f"GitHub API error: {e}",
            )

    async def authenticate(self) -> bool:
        """Authenticate with GitHub."""
        try:
            response = await self.client.get(f"{self.base_url}/user")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}")
            return False

    async def create_repo(
        self,
        name: str,
        private: bool = True,
        description: Optional[str] = None,
        **config: Any,
    ) -> Repo:
        """Create a new GitHub repository."""
        payload = {"name": name, "private": private, "auto_init": True}

        if description:
            payload["description"] = description

        response = await self.client.post(f"{self.base_url}/user/repos", json=payload)
        response.raise_for_status()

        data = response.json()

        return Repo(
            name=data["name"],
            owner=data["owner"]["login"],
            url=data["html_url"],
            default_branch=data["default_branch"],
            metadata=data,
        )

    async def create_branch(self, repo: Repo, name: str, from_branch: str = "main") -> Branch:
        """Create a new branch."""
        # Get the SHA of the source branch
        ref_response = await self.client.get(
            f"{self.base_url}/repos/{repo.owner}/{repo.name}/git/refs/heads/{from_branch}"
        )
        ref_response.raise_for_status()
        sha = ref_response.json()["object"]["sha"]

        # Create new branch
        payload = {"ref": f"refs/heads/{name}", "sha": sha}

        response = await self.client.post(
            f"{self.base_url}/repos/{repo.owner}/{repo.name}/git/refs", json=payload
        )
        response.raise_for_status()

        return Branch(name=name, sha=sha, repo=repo)

    async def create_pr(self, repo: Repo, pr: PullRequest) -> PR:
        """Create a pull request."""
        payload = {
            "title": pr.title,
            "body": pr.body,
            "head": pr.head_branch,
            "base": pr.base_branch,
            "draft": pr.draft,
        }

        response = await self.client.post(
            f"{self.base_url}/repos/{repo.owner}/{repo.name}/pulls", json=payload
        )
        response.raise_for_status()

        data = response.json()

        return PR(
            number=data["number"],
            url=data["html_url"],
            title=data["title"],
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )

    async def merge_pr(self, repo: Repo, pr_number: int) -> MergeResult:
        """Merge a pull request."""
        try:
            response = await self.client.put(
                f"{self.base_url}/repos/{repo.owner}/{repo.name}/pulls/{pr_number}/merge"
            )
            response.raise_for_status()

            data = response.json()

            return MergeResult(
                success=data["merged"], sha=data.get("sha"), message=data.get("message")
            )
        except httpx.HTTPStatusError as e:
            return MergeResult(success=False, message=str(e))

    async def get_pr_status(self, repo: Repo, pr_number: int) -> str:
        """Get PR status."""
        response = await self.client.get(
            f"{self.base_url}/repos/{repo.owner}/{repo.name}/pulls/{pr_number}"
        )
        response.raise_for_status()

        return response.json()["state"]

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
