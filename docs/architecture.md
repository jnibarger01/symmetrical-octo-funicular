# Codex Lifecycle Agent — Technical Architecture

> Version: 0.1.0-draft
> Status: In Progress
> Last Updated: 2025-01-17

-----

## Table of Contents

1. [Executive Summary](#1-executive-summary)
1. [System Context](#2-system-context)
1. [Architecture Principles](#3-architecture-principles)
1. [Component Architecture](#4-component-architecture)
1. [Orchestrator State Machine](#5-orchestrator-state-machine)
1. [Task DAG Engine](#6-task-dag-engine)
1. [Codex Execution Layer](#7-codex-execution-layer)
1. [Policy Engine](#8-policy-engine)
1. [Repository Inspector](#9-repository-inspector)
1. [Provider Integrations](#10-provider-integrations)
1. [CLI Interface Contract](#11-cli-interface-contract)
1. [Data Models](#12-data-models)
1. [Persistence & State Management](#13-persistence--state-management)
1. [Security Architecture](#14-security-architecture)
1. [Error Handling & Recovery](#15-error-handling--recovery)
1. [Observability & Audit](#16-observability--audit)
1. [Configuration Management](#17-configuration-management)
1. [Deployment Architecture](#18-deployment-architecture)
1. [Extension Points](#19-extension-points)
1. [Open Questions & Decisions](#20-open-questions--decisions)

-----

## 1. Executive Summary

### 1.1 Purpose

<!-- One paragraph: what this system does and why it exists -->

### 1.2 Scope

<!-- What's in v1, what's explicitly deferred -->

### 1.3 Key Architectural Decisions

<!-- Bulleted list of the 5-7 most consequential choices -->

-----

## 2. System Context

### 2.1 Context Diagram

<!-- C4 Level 1: System and its external actors/systems -->

```
┌─────────────────────────────────────────────────────────────────┐
│                        Solo Developer                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Codex Lifecycle Agent CLI                    │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │ GitHub │  │   CI   │  │ Codex  │  │ Hosting│  │ Secrets│
   │  API   │  │ Runner │  │  LLM   │  │Provider│  │ Vault  │
   └────────┘  └────────┘  └────────┘  └────────┘  └────────┘
```

### 2.2 External Dependencies

<!-- Table: dependency, purpose, failure impact, fallback -->

|Dependency      |Purpose                       |Failure Impact         |Fallback Strategy         |
|----------------|------------------------------|-----------------------|--------------------------|
|GitHub API      |Repo operations, PR management|Blocking               |Local git operations only |
|Codex/LLM API   |Code generation               |Blocking               |Queue and retry           |
|CI Provider     |Test execution                |Degraded (local tests) |Local test runner         |
|Hosting Provider|Deployment                    |Degraded (staging only)|Manual deploy instructions|
|Secrets Manager |Credential storage            |Blocking               |Local encrypted store     |

### 2.3 Trust Boundaries

<!-- Where do we trust input? Where do we validate? -->

-----

## 3. Architecture Principles

### 3.1 Core Principles

1. **CLI-First Execution**
- All code modifications flow through Codex CLI
- No direct file writes from orchestrator logic
- Auditable command history
1. **Deterministic Outputs**
- Same inputs produce same outputs (within LLM variance)
- Seeded randomness where applicable
- Reproducible builds and deployments
1. **Fail-Safe by Default**
- Operations are idempotent
- Explicit gates before destructive actions
- Automatic rollback on failure
1. **Minimal Privilege**
- Request only necessary permissions
- Scope tokens to specific operations
- No persistent credentials in memory
1. **Observable Everything**
- Every action logged with context
- Metrics for all operations
- Alerts on anomalies

### 3.2 Technology Choices

|Concern         |Choice                  |Rationale                                    |
|----------------|------------------------|---------------------------------------------|
|Primary Language|Python 3.11+            |Ecosystem, LLM tooling, developer familiarity|
|CLI Framework   |Typer + Rich            |Type safety, modern UX, minimal boilerplate  |
|State Storage   |SQLite + JSON files     |Zero-dependency, portable, inspectable       |
|LLM Integration |OpenAI API (Codex/GPT-4)|Best code generation, function calling       |
|Git Operations  |GitPython + subprocess  |Programmatic + escape hatch                  |
|Task Queue      |In-process (v1)         |Simplicity; Redis later if needed            |

-----

## 4. Component Architecture

### 4.1 Container Diagram

<!-- C4 Level 2: Major components and their relationships -->

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Codex Lifecycle Agent                           │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │     CLI      │───▶│ Orchestrator │───▶│   Policy     │              │
│  │   Interface  │    │    (Core)    │◀───│   Engine     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                       │
│         ▼                   ▼                   ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Task DAG    │    │    Codex     │    │    Repo      │              │
│  │   Engine     │    │   Executor   │    │  Inspector   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         └───────────────────┼───────────────────┘                       │
│                             ▼                                           │
│                    ┌──────────────┐                                     │
│                    │   Provider   │                                     │
│                    │   Gateway    │                                     │
│                    └──────────────┘                                     │
│                             │                                           │
└─────────────────────────────┼───────────────────────────────────────────┘
                              ▼
                    External Services
```

### 4.2 Component Responsibilities

|Component       |Responsibility                           |Owns                                 |
|----------------|-----------------------------------------|-------------------------------------|
|CLI Interface   |Parse commands, render output, handle I/O|User interaction contract            |
|Orchestrator    |Lifecycle state machine, coordination    |State transitions, checkpoints       |
|Policy Engine   |Validate actions against rules           |Security policies, quality gates     |
|Task DAG Engine |Plan decomposition, dependency management|Task graph, execution order          |
|Codex Executor  |LLM interaction, code generation         |Prompt construction, response parsing|
|Repo Inspector  |Codebase analysis, context extraction    |File index, dependency graph         |
|Provider Gateway|External service abstraction             |API clients, retry logic             |

### 4.3 Component Interfaces

<!-- Key interfaces between components - defined in detail later -->

-----

## 5. Orchestrator State Machine

### 5.1 State Definitions

```
┌─────────┐
│  IDLE   │◀──────────────────────────────────────────────┐
└────┬────┘                                               │
     │ init/plan                                          │
     ▼                                                    │
┌─────────┐    failure    ┌─────────┐                    │
│PLANNING │──────────────▶│ FAILED  │                    │
└────┬────┘               └────┬────┘                    │
     │ success                 │ reset                   │
     ▼                         │                         │
┌─────────────┐                │                         │
│ SCAFFOLDING │────────────────┤                         │
└──────┬──────┘                │                         │
       │ success               │                         │
       ▼                       │                         │
┌─────────────┐                │                         │
│  BUILDING   │◀───┐           │                         │
└──────┬──────┘    │           │                         │
       │ success   │ fix       │                         │
       ▼           │           │                         │
┌─────────────┐    │           │                         │
│  VERIFYING  │────┤           │                         │
└──────┬──────┘    │           │                         │
       │ pass      │ fail      │                         │
       ▼           │           │                         │
┌─────────────┐    │           │                         │
│  DEPLOYING  │────┴───────────┤                         │
└──────┬──────┘                │                         │
       │ success               │                         │
       ▼                       │                         │
┌─────────────┐                │                         │
│  OBSERVING  │────────────────┤                         │
└──────┬──────┘                │                         │
       │ issue detected        │                         │
       ▼                       │                         │
┌─────────────┐                │                         │
│ MAINTAINING │────────────────┴─────────────────────────┘
└─────────────┘
```

### 5.2 State Details

|State      |Entry Condition              |Exit Conditions            |Allowed Actions                  |Timeout   |
|-----------|-----------------------------|---------------------------|---------------------------------|----------|
|IDLE       |Initial state / reset        |`plan` command             |init, plan                       |None      |
|PLANNING   |`plan` invoked               |Plan approved or failed    |generate_plan, revise_plan       |30 min    |
|SCAFFOLDING|Plan approved                |Scaffold complete or failed|create_repo, setup_ci, init_tests|15 min    |
|BUILDING   |Scaffold complete / fix cycle|Build complete or failed   |execute_task, commit_changes     |Per-task  |
|VERIFYING  |Build complete               |Tests pass or fail         |run_ci, analyze_failures         |30 min    |
|DEPLOYING  |Verification passed          |Deploy success or failed   |deploy_staging, deploy_prod      |15 min    |
|OBSERVING  |Deploy success               |Issue detected or manual   |check_health, collect_metrics    |Continuous|
|MAINTAINING|Issue detected               |Resolution complete        |patch, upgrade, refactor         |Per-issue |
|FAILED     |Any unrecoverable error      |Manual reset               |diagnose, export_state           |None      |

### 5.3 State Transitions

<!-- Detailed transition rules with guards -->

```python
# Pseudocode for transition validation
TRANSITIONS = {
    "IDLE": ["PLANNING"],
    "PLANNING": ["SCAFFOLDING", "FAILED"],
    "SCAFFOLDING": ["BUILDING", "FAILED"],
    "BUILDING": ["VERIFYING", "FAILED"],
    "VERIFYING": ["DEPLOYING", "BUILDING", "FAILED"],  # Can loop back to BUILDING
    "DEPLOYING": ["OBSERVING", "FAILED"],
    "OBSERVING": ["MAINTAINING", "IDLE"],
    "MAINTAINING": ["BUILDING", "OBSERVING", "IDLE", "FAILED"],
    "FAILED": ["IDLE"],  # Only manual reset
}
```

### 5.4 Checkpoint & Recovery

<!-- How state is persisted, how to resume after crash -->

-----

## 6. Task DAG Engine

### 6.1 Task Model

```python
@dataclass
class Task:
    id: str                      # Unique identifier (ulid)
    type: TaskType               # scaffold, implement, test, deploy, etc.
    title: str                   # Human-readable description
    description: str             # Detailed specification
    dependencies: List[str]      # Task IDs that must complete first
    status: TaskStatus           # pending, running, completed, failed, blocked
    priority: int                # Execution priority (lower = higher priority)
    estimated_complexity: int    # 1-5 scale for scoping

    # Execution context
    target_files: List[str]      # Files this task may modify
    verification: Verification   # How to verify completion

    # Audit
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    attempts: int
    last_error: Optional[str]
```

### 6.2 DAG Construction

<!-- How PRD → Tasks → DAG -->

1. **PRD Parsing**: Extract features, requirements, constraints
1. **Feature Decomposition**: Break features into implementable units
1. **Dependency Analysis**: Identify task ordering constraints
1. **Complexity Estimation**: Size tasks for execution bounds
1. **DAG Validation**: Check for cycles, unreachable nodes

### 6.3 Execution Strategy

<!-- Topological sort, parallel execution potential, failure handling -->

### 6.4 Re-planning

<!-- When and how the DAG is modified mid-execution -->

-----

## 7. Codex Execution Layer

### 7.1 Execution Model

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Task      │────▶│   Context   │────▶│   Prompt    │────▶│    LLM      │
│  Selection  │     │  Assembly   │     │Construction │     │   Call      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐            │
│   Commit    │◀────│  Validation │◀────│   Response  │◀───────────┘
│   Changes   │     │   & Retry   │     │   Parsing   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 7.2 Context Assembly

<!-- How we build the context window for each task -->

|Context Element        |Source          |Priority   |Max Tokens|
|-----------------------|----------------|-----------|----------|
|System prompt          |Static template |Required   |500       |
|Task specification     |Task DAG        |Required   |1000      |
|Target file contents   |Repo Inspector  |Required   |4000      |
|Related file summaries |Repo Inspector  |Optional   |2000      |
|Test specifications    |Test files      |Optional   |1000      |
|Error context (retries)|Previous attempt|Conditional|500       |
|Style guide            |Config          |Optional   |500       |

### 7.3 Prompt Templates

<!-- Structure of prompts for different task types -->

### 7.4 Response Parsing

<!-- How LLM output is validated and extracted -->

### 7.5 Retry & Fallback Strategy

|Failure Type  |Retry Strategy      |Max Attempts|Fallback       |
|--------------|--------------------|------------|---------------|
|Rate limit    |Exponential backoff |5           |Queue for later|
|Invalid output|Re-prompt with error|3           |Split task     |
|Timeout       |Immediate retry     |2           |Reduce context |
|API error     |Exponential backoff |3           |Alert and pause|

### 7.6 Token Budget Management

<!-- How we stay within context limits -->

-----

## 8. Policy Engine

### 8.1 Policy Types

|Policy Type|Enforcement Point     |Blocking    |Examples                      |
|-----------|----------------------|------------|------------------------------|
|Security   |Pre-commit, Pre-deploy|Yes         |No secrets, dependency audit  |
|Quality    |Pre-commit, Pre-merge |Configurable|Coverage threshold, lint rules|
|Safety     |Pre-execution         |Yes         |File count limits, diff size  |
|Compliance |Pre-deploy            |Yes         |License checks, SBOM          |

### 8.2 Policy Definitions

```yaml
# Example policy configuration
policies:
  security:
    secret_scanning:
      enabled: true
      patterns:
        - "(?i)api[_-]?key"
        - "(?i)password\\s*="
        - "(?i)secret\\s*="
      block_on_match: true

    dependency_audit:
      enabled: true
      fail_on_severity: high
      ignored_cves: []

  quality:
    test_coverage:
      enabled: true
      minimum_percent: 80
      blocking: false  # Warn only in v1

    lint:
      enabled: true
      tools: [ruff, eslint]
      blocking: true

  safety:
    max_files_per_task: 10
    max_diff_lines: 500
    prohibited_paths:
      - ".env"
      - "secrets/"
      - "*.pem"
```

### 8.3 Policy Evaluation

<!-- How policies are checked, results aggregated, decisions made -->

### 8.4 Policy Overrides

<!-- How a developer can bypass policies with explicit approval -->

-----

## 9. Repository Inspector

### 9.1 Capabilities

- **File Indexing**: Map of all files with metadata
- **Dependency Graph**: Import/require relationships
- **Symbol Extraction**: Functions, classes, exports
- **Change Detection**: What changed since last run
- **Context Retrieval**: Get relevant files for a task

### 9.2 Index Schema

```python
@dataclass
class FileIndex:
    path: str
    language: str
    size_bytes: int
    hash: str  # Content hash for change detection
    symbols: List[Symbol]
    imports: List[str]
    exports: List[str]
    last_modified: datetime

@dataclass
class Symbol:
    name: str
    type: str  # function, class, variable, type
    line_start: int
    line_end: int
    signature: Optional[str]
```

### 9.3 Context Selection Algorithm

<!-- How we choose which files to include in LLM context -->

-----

## 10. Provider Integrations

### 10.1 Provider Interface

```python
class Provider(Protocol):
    """Base interface for all external service providers."""

    async def health_check(self) -> HealthStatus: ...
    async def authenticate(self) -> bool: ...

class GitProvider(Provider):
    """Git hosting operations."""
    async def create_repo(self, name: str, config: RepoConfig) -> Repo: ...
    async def create_branch(self, repo: Repo, name: str) -> Branch: ...
    async def create_pr(self, repo: Repo, pr: PullRequest) -> PR: ...
    async def merge_pr(self, pr: PR) -> MergeResult: ...

class CIProvider(Provider):
    """CI/CD operations."""
    async def trigger_build(self, repo: Repo, ref: str) -> Build: ...
    async def get_build_status(self, build: Build) -> BuildStatus: ...
    async def get_build_logs(self, build: Build) -> str: ...

class HostingProvider(Provider):
    """Deployment operations."""
    async def deploy(self, artifact: Artifact, env: Environment) -> Deployment: ...
    async def rollback(self, deployment: Deployment) -> Deployment: ...
    async def get_status(self, deployment: Deployment) -> DeploymentStatus: ...
```

### 10.2 Implemented Providers (v1)

|Provider Type|Implementation  |Configuration           |
|-------------|----------------|------------------------|
|Git          |GitHub          |`GITHUB_TOKEN`, org/user|
|CI           |GitHub Actions  |Workflow files          |
|Hosting      |Railway / Fly.io|Provider-specific       |
|Secrets      |Local encrypted |Master password         |

### 10.3 Provider Selection

<!-- How the agent chooses which provider to use -->

-----

## 11. CLI Interface Contract

### 11.1 Command Structure

```
codex <command> [subcommand] [options] [arguments]
```

### 11.2 Commands

|Command   |Subcommands                            |Description                          |
|----------|---------------------------------------|-------------------------------------|
|`init`    |—                                      |Initialize agent in current directory|
|`plan`    |`generate`, `show`, `approve`, `revise`|PRD ingestion and planning           |
|`scaffold`|—                                      |Create project structure             |
|`build`   |`next`, `task <id>`, `all`             |Execute implementation tasks         |
|`verify`  |`run`, `fix`, `report`                 |Run tests and validation             |
|`deploy`  |`staging`, `prod`                      |Deploy to environments               |
|`observe` |`status`, `logs`, `metrics`            |Monitor running application          |
|`maintain`|`upgrade`, `patch`, `refactor`         |Maintenance operations               |
|`status`  |—                                      |Show current state and progress      |
|`history` |—                                      |Show audit log                       |
|`config`  |`show`, `set`, `validate`              |Manage configuration                 |

### 11.3 Global Options

|Option           |Description                             |
|-----------------|----------------------------------------|
|`--verbose`, `-v`|Increase output verbosity               |
|`--quiet`, `-q`  |Suppress non-essential output           |
|`--dry-run`      |Show what would happen without executing|
|`--config <path>`|Use alternate config file               |
|`--no-color`     |Disable colored output                  |
|`--json`         |Output in JSON format                   |

### 11.4 Exit Codes

|Code|Meaning               |
|----|----------------------|
|0   |Success               |
|1   |General error         |
|2   |Invalid arguments     |
|3   |Policy violation      |
|4   |External service error|
|5   |State machine error   |

### 11.5 Output Contracts

<!-- JSON schemas for --json output -->

-----

## 12. Data Models

### 12.1 Core Entities

<!-- Full schema definitions for all domain objects -->

### 12.2 Events

<!-- Event types for audit logging -->

### 12.3 API Contracts

<!-- Internal API definitions between components -->

-----

## 13. Persistence & State Management

### 13.1 Storage Layout

```
.codex/
├── config.yaml          # User configuration
├── state.db             # SQLite state database
├── tasks/               # Task definitions and status
│   └── <task-id>.json
├── checkpoints/         # State snapshots for recovery
│   └── <timestamp>.json
├── logs/                # Execution logs
│   └── <date>/
│       └── <run-id>.log
├── cache/               # LLM response cache
│   └── <hash>.json
└── artifacts/           # Build artifacts, diffs
    └── <run-id>/
```

### 13.2 State Database Schema

```sql
-- Core state
CREATE TABLE lifecycle_state (
    id INTEGER PRIMARY KEY,
    current_state TEXT NOT NULL,
    previous_state TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task tracking
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    event_data JSON NOT NULL,
    actor TEXT NOT NULL  -- 'agent', 'user', 'system'
);

-- Checkpoints
CREATE TABLE checkpoints (
    id TEXT PRIMARY KEY,
    state_snapshot JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 13.3 Caching Strategy

<!-- What's cached, invalidation rules, cache limits -->

-----

## 14. Security Architecture

### 14.1 Threat Model

|Threat                  |Impact|Mitigation                                |
|------------------------|------|------------------------------------------|
|Secret in generated code|High  |Pre-commit scanning, pattern detection    |
|Malicious dependency    |High  |Lockfiles, audit on install               |
|LLM prompt injection    |Medium|Input sanitization, output validation     |
|Credential exposure     |High  |Never log secrets, encrypted storage      |
|Unauthorized deployment |High  |Production gate requires explicit approval|

### 14.2 Secret Management

<!-- How secrets are stored, accessed, and rotated -->

### 14.3 Audit Requirements

<!-- What must be logged for compliance -->

-----

## 15. Error Handling & Recovery

### 15.1 Error Categories

|Category   |Examples                        |Handling Strategy      |
|-----------|--------------------------------|-----------------------|
|Transient  |Network timeout, rate limit     |Retry with backoff     |
|Recoverable|Invalid LLM output, test failure|Retry with modification|
|Blocking   |Policy violation, auth failure  |Halt and alert         |
|Fatal      |Corrupted state, data loss      |Checkpoint restore     |

### 15.2 Recovery Procedures

<!-- Step-by-step recovery for each failure mode -->

### 15.3 Manual Intervention Points

<!-- When and how to involve the human -->

-----

## 16. Observability & Audit

### 16.1 Logging

|Log Level|Purpose                     |Retention|
|---------|----------------------------|---------|
|DEBUG    |Development troubleshooting |1 day    |
|INFO     |Operational events          |7 days   |
|WARN     |Potential issues            |30 days  |
|ERROR    |Failures requiring attention|90 days  |
|AUDIT    |Compliance events           |1 year   |

### 16.2 Metrics

|Metric                   |Type     |Purpose             |
|-------------------------|---------|--------------------|
|`task_duration_seconds`  |Histogram|Performance tracking|
|`llm_tokens_used`        |Counter  |Cost tracking       |
|`policy_violations_total`|Counter  |Security monitoring |
|`deployment_success_rate`|Gauge    |Reliability tracking|

### 16.3 Alerting

<!-- Alert conditions and notification channels -->

-----

## 17. Configuration Management

### 17.1 Configuration Hierarchy

```
1. Built-in defaults
2. Global config (~/.codex/config.yaml)
3. Project config (.codex/config.yaml)
4. Environment variables (CODEX_*)
5. CLI flags
```

### 17.2 Configuration Schema

```yaml
# .codex/config.yaml
version: 1

project:
  name: my-app
  stack: node-postgres  # or python-postgres

llm:
  provider: openai
  model: gpt-4-turbo
  max_tokens_per_request: 8000
  temperature: 0.1

providers:
  git:
    type: github
    owner: myuser
    repo: my-app
  ci:
    type: github-actions
  hosting:
    type: railway

policies:
  # Policy overrides...

preferences:
  auto_fix_lint: true
  require_tests: true
  verbose_logging: false
```

### 17.3 Validation

<!-- How config is validated on load -->

-----

## 18. Deployment Architecture

### 18.1 Agent Deployment

<!-- How the CLI itself is distributed and updated -->

### 18.2 Target Application Deployment

<!-- How the agent deploys the applications it builds -->

-----

## 19. Extension Points

### 19.1 Plugin Architecture

<!-- How to add new providers, policies, task types -->

### 19.2 Custom Policies

<!-- How to define organization-specific policies -->

### 19.3 Hooks

<!-- Pre/post hooks for lifecycle events -->

-----

## 20. Open Questions & Decisions

### 20.1 Pending Decisions

|ID  |Question                |Options                           |Recommendation      |Status  |
|----|------------------------|----------------------------------|--------------------|--------|
|D001|LLM provider abstraction|OpenAI only vs. multi-provider    |OpenAI only for v1  |Proposed|
|D002|State storage           |SQLite vs. JSON files             |SQLite + JSON hybrid|Proposed|
|D003|Parallel task execution |Sequential vs. parallel           |Sequential for v1   |Proposed|
|D004|Hosting provider        |Railway vs. Fly.io vs. Vercel     |TBD                 |Open    |
|D005|Secret management       |Local encrypted vs. external vault|Local for v1        |Proposed|

### 20.2 Technical Debt Backlog

<!-- Known shortcuts taken for v1 -->

### 20.3 Future Considerations

<!-- Ideas for v2 and beyond -->

-----

## Appendices

### A. Glossary

|Term      |Definition                                        |
|----------|--------------------------------------------------|
|DAG       |Directed Acyclic Graph — task dependency structure|
|Checkpoint|Snapshot of agent state for recovery              |
|Policy    |Rule that must be satisfied before an action      |
|Gate      |Decision point requiring explicit approval        |

### B. References

- [PRD: Codex Lifecycle Agent](./PRD.md)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [GitHub API Documentation](https://docs.github.com/en/rest)

### C. Change Log

|Version|Date      |Author|Changes                |
|-------|----------|------|-----------------------|
|0.1.0  |2025-01-17|—     |Initial draft structure|
