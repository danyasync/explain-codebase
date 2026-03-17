# Explain Codebase

CLI tool that analyzes any repository and explains its architecture, entrypoints, dependencies, and impact of changes.

`explain-codebase` analyzes a repository and helps developers understand unfamiliar projects faster by showing how the system is structured and where execution likely starts.

It works with both local folders and public GitHub repositories.

---

## Why

When opening a new repository, it is often unclear:

- where the application starts
- which modules are central
- which files interact with external systems
- what files are risky to modify

`explain-codebase` scans the project, builds a dependency graph, detects architectural signals, and produces a compact CLI overview that helps you understand the codebase faster.

---

## Installation

```bash
pip install explain-codebase
```

For local development:

```bash
pip install -e .[dev]
```

## Quick Start

Analyze the current repository:

```bash
explain-codebase .
```

Verbose architecture output:

```bash
explain-codebase . --verbose
```

Deep architecture analysis:

```bash
explain-codebase . --deep
```

Analyze a GitHub repository:

```bash
explain-codebase https://github.com/user/repo
```

## Example Output

```text
Explain Codebase
--------------------------------

Repository

  Path        C:\Projects\orders-api
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

Verbose mode provides a deeper architecture view:

```text
Execution flow

api_server.py
|- routes/order_routes.py
|- services/order_service.py
|  |- repositories/order_repository.py
|  \- clients/warehouse_client.py
\- middleware/auth_guard.py
```

## Features

- Analyze local folders and public GitHub repositories
- Detect project language and project type
- Detect entrypoints automatically
- Rank core modules by dependency usage
- Infer likely execution flow
- Detect modules that interact with database, network, filesystem, or cache
- Detect architecture folders such as `services`, `repositories`, `routes`, and `models`
- Detect large modules and highly coupled files
- Detect architecture smells such as circular dependencies
- Generate dependency graph visualizations
- Generate HTML architecture reports
- Explain a single file in project context
- Suggest onboarding reading paths
- Support CI mode for architecture checks

## Common Commands

Analyze a repository:

```bash
explain-codebase .
```

Verbose architecture output:

```bash
explain-codebase . --verbose
```

Deep architecture analysis:

```bash
explain-codebase . --deep
```

Suggest a reading order for a new developer:

```bash
explain-codebase onboarding .
```

Explain a single file:

```bash
explain-codebase file src/services/order_service.ts
```

Generate a dependency graph:

```bash
explain-codebase . --graph
```

Generate an HTML architecture report:

```bash
explain-codebase . --report
```

Run in CI mode:

```bash
explain-codebase . --ci
```

## Remote Repositories

You can analyze a public GitHub repository directly:

```bash
explain-codebase https://github.com/user/repo
```

The tool will:

1. Resolve the repository
2. Check that it exists and is publicly accessible
3. Ask for confirmation before cloning
4. Clone it into a temporary workspace
5. Run the analysis
6. Remove the temporary workspace automatically

## Output Modes

Default mode shows a compact overview:

```bash
explain-codebase .
```

Verbose mode shows the full architecture structure:

```bash
explain-codebase . --verbose
```

Deep mode focuses on architecture risks and potential issues:

```bash
explain-codebase . --deep
```
