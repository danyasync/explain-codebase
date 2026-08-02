# Explain Codebase

[![PyPI version](https://img.shields.io/pypi/v/explain-codebase.svg)](https://pypi.org/project/explain-codebase/)
[![Python versions](https://img.shields.io/pypi/pyversions/explain-codebase.svg)](https://pypi.org/project/explain-codebase/)
[![CI](https://github.com/danyasync/explain-codebase/actions/workflows/ci.yml/badge.svg)](https://github.com/danyasync/explain-codebase/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/danyasync/explain-codebase/blob/main/LICENSE)

Static-analysis CLI for mapping repository architecture, dependencies, entry points, side effects, and change risk.

`explain-codebase` helps you find where execution starts, which files are central, how source files depend on one another, and where a change is likely to have the widest impact. It reads source files without importing or running the target project.

## Quick start

Install from PyPI and inspect the current directory:

```bash
python -m pip install explain-codebase
explain-codebase .
```

For an isolated command-line installation, use `pipx`:

```bash
pipx install explain-codebase
explain-codebase .
```

The default view is intentionally compact:

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

## What it shows

- likely application entry points
- central modules ranked by dependency usage
- relative and package import relationships
- probable execution paths
- files that interact with databases, networks, filesystems, or caches
- common architecture areas such as services, repositories, routes, and controllers
- large files, highly connected files, circular dependencies, and risky change points
- a suggested reading order for onboarding
- focused dependency graphs and an HTML architecture report

The results are heuristic signals intended to shorten initial investigation. They are not a substitute for reading critical code paths or running the target project's own checks.

## Installation

### Requirements

- Python 3.10 or newer
- Git when inspecting a public GitHub repository
- network access for remote repository checks and cloning

### From PyPI

```bash
python -m pip install explain-codebase
```

### Isolated CLI installation

```bash
pipx install explain-codebase
```

### Local development

```bash
python -m pip install -e ".[dev]"
```

## Usage

### Common commands

| Goal | Command |
| --- | --- |
| Inspect the current directory | `explain-codebase .` |
| Inspect another local directory | `explain-codebase path/to/repository` |
| Show the detailed architecture view | `explain-codebase . --verbose` |
| Focus on architecture risks | `explain-codebase . --deep` |
| Write JSON to stdout | `explain-codebase . --json` |
| Limit the number of scanned files | `explain-codebase . --max-files 500` |
| Suggest a reading order | `explain-codebase onboarding .` |
| Explain one file in repository context | `explain-codebase file src/services/orders.py` |
| Write an interactive dependency graph | `explain-codebase . --graph` |
| Write an HTML architecture report | `explain-codebase . --report` |
| Return a failing status for detected architecture issues | `explain-codebase . --ci` |
| Show the installed version | `explain-codebase --version` |

`--verbose` and `--deep` cannot be combined.

### Graph views

`--graph` writes `dependency_graph.html`. `--report` writes `codebase_report.html`. Both files are written to the current working directory.

| Flag | View |
| --- | --- |
| `--architecture` | Architecture-level relationships; this is the default graph view |
| `--full` | Full file-level dependency graph |
| `--entrypoint` | Paths starting from likely entry points |
| `--risk` | Highly connected and risky files |
| `--side-effects` | Files with probable external side effects |

Choose at most one graph-view flag. A graph-view flag requires `--graph` or `--report`.

Examples:

```bash
explain-codebase . --graph --architecture
explain-codebase . --graph --entrypoint
explain-codebase . --report --risk
explain-codebase . --graph --full
```

## Supported source formats

| Language | Extensions | Primary signals |
| --- | --- | --- |
| Python | `.py` | syntax tree, imports, definitions, calls, and side effects |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` | static imports, CommonJS imports, calls, and side effects |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` | static imports, calls, and side effects |

Import resolution accounts for relative paths, package entry files, and the supported extension variants where those relationships can be determined statically.

## Scanning behavior

For a local directory, the scanner:

- considers only the supported source extensions
- keeps resolved file paths inside the selected repository
- honors the optional file-count limit and a 1 MiB per-file size limit
- skips common dependency, cache, build, coverage, and environment directories
- respects the root `.gitignore` file
- limits a Git worktree to tracked files when Git metadata can be read, then falls back to filesystem scanning if Git is unavailable
- handles unreadable source files safely and skips unsupported or oversized files

Use `--max-files` to lower the file-count limit for a focused or faster scan.

## Public GitHub repositories

Pass a public repository URL in the canonical form:

```bash
explain-codebase https://github.com/owner/repository
```

The CLI checks public repository metadata, asks for confirmation, performs a limited clone in a temporary directory, analyzes the clone, and removes the temporary directory afterward. Private repositories, other hosting providers, and arbitrary Git URLs are not supported.

Remote inspection requires an interactive terminal, Git, and network access. Clone timeouts can stop remote preparation, and oversized source files are skipped during analysis.

## Output and automation

### Standard output and error output

Human-readable output and JSON are written to stdout. Progress stages, warnings, and errors are written to stderr. This keeps JSON suitable for redirection:

```bash
explain-codebase . --json > architecture.json
```

### CI mode

```bash
explain-codebase . --ci
```

CI mode exits with status `0` when no architecture issues are found and status `1` when an issue is detected. Current issue checks include circular dependencies and utility-style god modules. Thresholds are built into the CLI.

### JSON

JSON output includes repository information, entry points, central modules, side-effect files, architecture areas, large files, hotspots, risky files, architecture issues, execution paths, and paths to optional HTML outputs.

## How it works

At a high level, `explain-codebase`:

1. resolves and validates the target
2. selects supported source files within safety boundaries
3. parses static imports and source-level signals
4. resolves imports and builds a dependency graph
5. ranks central modules and identifies entry points, side effects, hotspots, and architecture issues
6. renders the selected CLI, JSON, graph, or report output

The target project's source code is not imported or executed during analysis.

## Limitations

- Dynamic imports, reflection, runtime dependency injection, and framework-specific wiring may not be visible.
- Custom path aliases and build-tool transformations may reduce import-resolution accuracy.
- Syntax that is valid only after a separate transform step may be skipped.
- Minified, vendored, mirrored, or highly repetitive code can reduce signal quality.
- Large monorepos should use `--max-files` or analyze a narrower directory.
- Remote analysis supports only public GitHub repositories.
- A shallow remote clone can still transfer large files because total repository download size is not capped.
- Interactive HTML views load a version-pinned, integrity-checked graph library from a public CDN and need network access when opened.

## Development

Install the development tools and run the checks:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
python -m twine check --strict dist/*
```

## Project information

- [Changelog](https://github.com/danyasync/explain-codebase/blob/main/CHANGELOG.md)
- [Security policy](https://github.com/danyasync/explain-codebase/blob/main/SECURITY.md)
- [Issue tracker](https://github.com/danyasync/explain-codebase/issues)
- [PyPI package](https://pypi.org/project/explain-codebase/)

## License

Licensed under the [MIT License](https://github.com/danyasync/explain-codebase/blob/main/LICENSE).
