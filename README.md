# Explain Codebase

CLI tool for quickly mapping the architecture of an unfamiliar repository.

`explain-codebase` is a heuristic static-analysis CLI that helps developers find likely entrypoints, central modules, side-effect files, and risky areas in a codebase.

It is designed for onboarding and architecture review. It works with local folders and public GitHub repositories, and it aims to give you a useful architectural map quickly rather than perfectly understand every code path.

## Why

When you open a new repository, the first questions are usually:

- where execution starts
- which modules are central
- which files touch the database, network, filesystem, or cache
- what files are risky to change
- where to begin onboarding

`explain-codebase` scans the project, builds a dependency graph, and turns those signals into a compact CLI summary.

## Changelog

### v0.1.2

This release improves repository scanning by making the analyzer Git-aware.

What's new:

- supports `.gitignore`-aware scanning
- analyzes only files tracked by Git when the target is a Git repository
- ignores common noise directories such as `.venv`, `node_modules`, `dist`, `build`, `coverage`, and `__pycache__`
- produces cleaner dependency graphs and more accurate architecture summaries
- prevents generated and local-only files from polluting graph and report outputs

This makes the tool much more useful on real-world repositories by excluding ignored, temporary, and untracked files from the analysis.

### v0.1.4

Improved dependency graph visualization.

What’s new:

- Redesigned dependency graph with a cleaner, more readable layout
- Improved node spacing and reduced visual noise
- Better handling of large repositories
- Smoother interactions and graph rendering

The graph is now easier to read and better represents the structure of real-world codebases.

## Installation

### Requirements

- Python 3.10+
- Git, if you want to analyze remote GitHub repositories
- Best current support: Python, JavaScript, and TypeScript repositories

### Install from PyPI

```bash
pip install explain-codebase
```

### For local development

```bash
pip install -e .[dev]
```

## Commands

### Overview

Use this when you want a quick architectural snapshot of a repository:

```bash
explain-codebase .
```

### Detailed analysis

Use verbose mode when you want to inspect the likely architecture structure in more detail:

```bash
explain-codebase . --verbose
```

Use deep mode when you want to focus on architectural risks and potential maintenance problems:

```bash
explain-codebase . --deep
```

### File explanation

Use this when you want to understand one specific file in project context:

```bash
explain-codebase file src/services/api_server.py
```

### Onboarding path

Use this when a new developer needs a suggested reading order:

```bash
explain-codebase onboarding .
```

### Graph and report

Generate an interactive dependency graph:

```bash
explain-codebase . --graph
```

Generate a full HTML architecture report:

```bash
explain-codebase . --report
```

### CI mode

Use this in CI when you want architecture issues to fail the build:

```bash
explain-codebase . --ci
```

## Example Output

### Default output

Default output is intentionally compact:

```text
Explain Codebase
--------------------------------

Repository

  Path        C:\Projects\checkout-service
  Type        Python backend service
  Language    python
  Files       7

Architecture

  Entrypoints        1
  Core modules       5
  Side effects       4

Suggested starting point

  api_server.py

Run with --verbose to see full architecture
```

### Verbose output

Verbose mode adds more structure, including a likely execution path:

```text
Execution flow

api_server.py
|- routes/order_routes.py
|- services/order_service.py
|  |- repositories/order_repository.py
|  \- clients/warehouse_client.py
\- middleware/auth_guard.py
```

This output is heuristic. It reflects likely structure based on static signals such as imports, naming conventions, and folder layout. It should be treated as a high-value map, not as guaranteed truth.

## Features

- analyzes local folders and public GitHub repositories
- detects project language and project type
- attempts to detect likely entrypoints automatically
- ranks central modules by dependency usage
- surfaces likely execution paths
- highlights modules that interact with database, network, filesystem, or cache
- detects common architecture folders such as `services`, `repositories`, `routes`, and `models`
- flags large modules and highly coupled files
- highlights potential architecture issues such as circular dependencies
- generates dependency graph visualizations
- generates HTML architecture reports
- explains a single file in project context
- suggests onboarding reading paths
- supports CI mode for architecture checks

## Remote Repositories

You can analyze a public GitHub repository directly:

```bash
explain-codebase https://github.com/user/repo
```

For remote repositories, the tool:

- supports public GitHub repository URLs
- clones the repository into a temporary workspace
- cleans up that workspace after analysis

## How It Works

At a high level, the tool:

- scans source files in the target repository
- detects language and likely project type
- parses imports and builds a dependency graph
- scores central modules using graph signals
- surfaces likely entrypoints, side effects, hotspots, and onboarding hints
- renders the result in CLI, JSON, and optional HTML outputs

## Limitations

- the analysis is heuristic, not full semantic understanding
- best results come from Python, JavaScript, and TypeScript projects with conventional layouts
- dynamic imports, reflection-heavy code, and runtime dependency injection may reduce accuracy
- generated, vendored, or mirrored code can reduce signal quality
- large monorepos may need path scoping or `--max-files` to keep output focused

## CI Behavior

CI mode is intended for lightweight architectural checks:

```bash
explain-codebase . --ci
```

Current behavior:

- exit code `0` when no architecture issues are detected
- exit code `1` when architecture issues are found
- current issue types include circular dependencies and utility-style god modules
- thresholds are currently built into the tool and are not yet configurable through CLI flags

## JSON Output

Use JSON output when you want to integrate the tool into scripts or pipelines:

```bash
explain-codebase . --json
```

The JSON output includes fields such as:

- `project_type`
- `entrypoints`
- `core_modules`
- `core_module_rankings`
- `side_effect_modules`
- `architecture_modules`
- `large_files`
- `hotspots`
- `dangerous_files`
- `architecture_issues`
- `execution_flow`
- `dependency_graph_output`
- `html_report_output`

## Tests

```bash
pytest
```
