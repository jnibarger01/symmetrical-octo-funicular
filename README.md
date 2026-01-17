# Codex Lifecycle Agent

An AI-powered agent for managing the complete software development lifecycle, from planning to deployment and maintenance.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

Codex Lifecycle Agent is a CLI tool that automates software development workflows using Large Language Models (LLMs). It manages the entire lifecycle of a software project through a state machine-driven architecture:

- **Planning**: Ingest PRDs and generate implementation plans
- **Scaffolding**: Create project structure and boilerplate
- **Building**: Execute implementation tasks with AI assistance
- **Verifying**: Run tests and quality checks
- **Deploying**: Deploy to staging and production environments
- **Observing**: Monitor application health and metrics
- **Maintaining**: Handle updates, patches, and refactoring

## Features

- **State Machine Architecture**: Deterministic lifecycle management with checkpoints
- **Task DAG Engine**: Intelligent dependency management and execution ordering
- **LLM-Powered Code Generation**: OpenAI integration for automated implementation
- **Policy Engine**: Security, quality, and safety validation
- **Multi-Provider Support**: GitHub, GitHub Actions, Railway/Fly.io integrations
- **Repository Analysis**: Automatic codebase indexing and context extraction
- **Audit Logging**: Complete history of all operations
- **Rich CLI**: Beautiful terminal UI with progress tracking

## Architecture

The agent is built on a modular architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Codex Lifecycle Agent                    │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   CLI    │─▶│Orchestr. │─▶│ Policy   │  │Task DAG  │   │
│  │Interface │  │ (Core)   │  │ Engine   │  │ Engine   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                      │                                      │
│       ┌──────────────┼──────────────┐                       │
│       ▼              ▼              ▼                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  Codex   │  │   Repo   │  │Provider  │                 │
│  │Executor  │  │Inspector │  │ Gateway  │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

See [Architecture Documentation](docs/architecture.md) for details.

## Installation

### Prerequisites

- Python 3.11 or higher
- Git
- OpenAI API key

### Install from Source

```bash
git clone https://github.com/jnibarger01/symmetrical-octo-funicular.git
cd symmetrical-octo-funicular

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Verify Installation

```bash
codex --version
```

## Quick Start

### 1. Initialize a Project

```bash
codex init my-awesome-app --stack python-postgres
```

This creates a `.codex` directory with:
- Configuration file
- State database
- Task tracking
- Logs and cache

### 2. Configure API Keys

Edit `.codex/config.yaml` or set environment variables:

```bash
export CODEX_LLM__API_KEY="your-openai-api-key"
export CODEX_GIT__TOKEN="your-github-token"
```

### 3. Check Status

```bash
codex status
```

### 4. Generate a Plan (Coming Soon)

```bash
codex plan generate --prd my-prd.md
codex plan show
codex plan approve
```

## CLI Commands

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize agent in current directory | `codex init my-app` |
| `status` | Show current state and progress | `codex status` |
| `plan` | PRD ingestion and planning | `codex plan generate --prd prd.md` |
| `scaffold` | Create project structure | `codex scaffold` |
| `build` | Execute implementation tasks | `codex build next` |
| `verify` | Run tests and validation | `codex verify run` |
| `deploy` | Deploy to environments | `codex deploy staging` |
| `observe` | Monitor running application | `codex observe status` |
| `maintain` | Maintenance operations | `codex maintain upgrade` |
| `history` | Show audit log | `codex history --limit 20` |

### Configuration Commands

```bash
codex config show              # Display current config
codex config set llm.model gpt-4  # Update a setting
codex config validate          # Validate configuration
```

### Global Options

- `--verbose`, `-v`: Enable verbose output
- `--quiet`, `-q`: Suppress non-essential output
- `--dry-run`: Show what would happen without executing
- `--config <path>`: Use alternate config file
- `--json`: Output in JSON format

## Configuration

The agent uses a hierarchical configuration system:

1. Built-in defaults
2. Global config (`~/.codex/config.yaml`)
3. Project config (`.codex/config.yaml`)
4. Environment variables (`CODEX_*`)
5. CLI flags

### Example Configuration

```yaml
version: 1

project:
  name: my-app
  stack: python-postgres

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
  security:
    secret_scanning: true
  quality:
    minimum_coverage_percent: 80
  safety:
    max_files_per_task: 10

preferences:
  auto_fix_lint: true
  require_tests: true
  verbose_logging: false
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=codex_agent --cov-report=html

# Run specific test file
pytest tests/unit/test_orchestrator.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
codex-lifecycle-agent/
├── src/codex_agent/
│   ├── cli/              # CLI interface
│   ├── core/             # Core orchestrator and models
│   ├── dag/              # Task DAG engine
│   ├── executor/         # LLM executor
│   ├── inspector/        # Repository inspector
│   ├── persistence/      # State storage
│   ├── policy/           # Policy engine
│   ├── providers/        # External service providers
│   └── utils/            # Utilities
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docs/                 # Documentation
└── pyproject.toml        # Project configuration
```

## State Machine

The agent operates through a state machine with the following states:

```
IDLE → PLANNING → SCAFFOLDING → BUILDING → VERIFYING →
DEPLOYING → OBSERVING → MAINTAINING → IDLE
                    ↓
                 FAILED → IDLE (reset)
```

Each state has:
- Entry/exit conditions
- Allowed actions
- State transitions
- Timeout limits

## Security

The agent includes multiple security layers:

- **Secret Scanning**: Prevents committing sensitive data
- **Dependency Auditing**: Checks for vulnerable dependencies
- **Policy Enforcement**: Validates all operations
- **Encrypted Storage**: Secrets are encrypted at rest
- **Audit Logging**: Complete history of operations

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linting
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

- [x] Core architecture implementation
- [x] State machine orchestrator
- [x] Task DAG engine
- [x] CLI interface
- [x] Policy engine
- [x] Persistence layer
- [ ] Complete PRD parsing
- [ ] Full LLM integration
- [ ] CI/CD provider implementations
- [ ] Hosting provider implementations
- [ ] Multi-language support
- [ ] Web dashboard
- [ ] Plugin system

## Support

- Documentation: [docs/architecture.md](docs/architecture.md)
- Issues: [GitHub Issues](https://github.com/jnibarger01/symmetrical-octo-funicular/issues)
- Discussions: [GitHub Discussions](https://github.com/jnibarger01/symmetrical-octo-funicular/discussions)

## Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [OpenAI](https://openai.com/) - LLM integration 
