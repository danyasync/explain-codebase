# Explain Codebase

`explain-codebase` helps developers understand unfamiliar repositories faster. It scans source code, builds a dependency graph, detects architecture signals, and presents the results through a compact CLI, JSON output, and optional HTML artifacts.

## Features

- Detect project language and likely project type
- Analyze local folders and public GitHub repositories
- Show numbered pipeline stages during execution
- Support compact default output, `--verbose`, and `--deep`
- Detect entrypoints automatically
- Rank core modules by incoming imports
- Infer likely execution flow
- Detect side-effect modules that touch database, network, filesystem, or cache
- Detect architecture folders such as `services/`, `repositories/`, `routes/`, and `models/`
- Detect large files over 800 LOC
- Detect hotspots by coupling score
- Detect risky files to modify
- Detect architecture smells such as circular dependencies and utility god modules
- Generate `dependency_graph.html`
- Generate `codebase_report.html`
- Explain a single file in project context
- Generate an onboarding reading path
- Support CI mode with non-zero exit code when architecture issues are found

## Installation

```bash
pip install explain-codebase
```

For local development:

```bash
pip install -e .[dev]
```

## Usage

Repository analysis:

```bash
explain-codebase .
explain-codebase ./repo
explain-codebase C:\projects\repo
explain-codebase . --verbose
explain-codebase . --deep
explain-codebase . --json
```

Other modes:

```bash
explain-codebase onboarding .
explain-codebase file src/services/user_service.ts
explain-codebase . --graph
explain-codebase . --report
explain-codebase . --ci
```

Remote GitHub repositories:

```bash
explain-codebase https://github.com/user/repo
explain-codebase https://github.com/user/repo.git
```

## Help Style

The CLI help is intentionally minimal and follows a plain devtool style:

```text
Explain Codebase - understand any repository architecture

Usage
  explain-codebase [TARGET] [OPTIONS]

Arguments
  TARGET              Path to repository or GitHub repository URL

Options
  --verbose           Show full architecture output
  --deep              Show architecture issues
  --json              Output analysis as JSON
  --graph             Generate dependency_graph.html
  --report            Generate codebase_report.html
  --ci                Exit with code 1 when architecture issues are detected
  --max-files N       Limit scanned source files

Examples
  explain-codebase .
  explain-codebase https://github.com/user/repo
  explain-codebase . --verbose
```

## Execution Stages

The CLI prints short progress stages:

```text
[1/5] Resolving target...
[2/5] Preparing local repository...
[3/5] Scanning project files...
[4/5] Building dependency graph...
[5/5] Generating explanation...
```

For remote repositories, stage 2 becomes:

```text
[2/5] Cloning repository...
```

## Remote Repository Flow

Supported remote URL formats:

```text
https://github.com/<owner>/<repo>
https://github.com/<owner>/<repo>.git
```

When a GitHub repository URL is used, the tool:

1. Resolves the target
2. Verifies repository availability through the GitHub API
3. Asks for confirmation before cloning
4. Creates a temporary workspace
5. Clones the repository
6. Runs the analysis
7. Removes the temporary workspace

Example:

```text
[1/5] Resolving target...
Repository
  https://github.com/user/repo

Download repository into a temporary directory? (y/n): y
Temporary workspace
  C:\Users\User\AppData\Local\Temp\explain_codebase_ab12cd

[2/5] Cloning repository...
[3/5] Scanning project files...
[4/5] Building dependency graph...
[5/5] Generating explanation...
Cleaning temporary workspace...
Temporary workspace removed
```

Repository not found:

```text
[1/5] Resolving target...
Error: Repository not found
https://github.com/user/non-existing-repo
Make sure the repository exists and is publicly accessible.
```

Repository not accessible:

```text
[1/5] Resolving target...
Error: Repository is not accessible
https://github.com/user/private-repo
Only public repositories are supported.
```

## Output Modes

### Default Mode

```bash
explain-codebase .
```

Default mode stays compact and focuses on:

- What kind of project this is
- Where execution likely starts
- Which file to read first

Example:

```text
Explain Codebase
--------------------------------

Repository

  Path        C:\Users\User\Desktop\pip
  Type        Python backend service
  Language    python
  Files       7

Architecture

  Entrypoints        1
  Core modules       5
  Side effects       4

Suggested starting point

  bot.py

Run with --verbose to see full architecture
```

### Verbose Mode

```bash
explain-codebase . --verbose
```

Verbose mode shows the architecture view:

- Entrypoints
- Core modules
- Side-effect modules
- Execution flow as a tree
- File roles

Example:

```text
Explain Codebase
--------------------------------

Repository

  Path        C:\Users\User\Desktop\pip
  Type        Python backend service
  Language    python
  Files       7

Architecture summary

  Entrypoints        1
  Core modules       5
  Side effects       4

Suggested starting point

  bot.py

Entrypoints

  bot.py

Core modules

  config.py
  captcha_utils.py
  data/persona.py
  llm.py
  utils.py

Side-effect modules

  bot.py
  captcha_utils.py
  config.py
  llm.py

Execution flow

bot.py
├─ config.py
├─ captcha_utils.py
│  └─ config.py
└─ llm.py
   ├─ config.py
   └─ data/persona.py

File roles

  bot.py            entrypoint
  config.py         config
  llm.py            service
  captcha_utils.py  utility
  data/persona.py   utility
  utils.py          utility

Run with --deep to see architecture issues
```

### Deep Mode

```bash
explain-codebase . --deep
```

Deep mode focuses on architecture risks:

- Circular dependencies
- Utility god modules
- Large modules
- High coupling modules

Example:

```text
Explain Codebase
--------------------------------

Repository

  Path        C:\Users\User\Desktop\pip
  Type        Python backend service
  Language    python
  Files       7

Architecture summary

  Entrypoints        1
  Core modules       5
  Side effects       4

Suggested starting point

  bot.py

Architecture issues

Circular dependency
  user_service -> billing_service -> user_service

Large modules

  billing_service.py (980 LOC)

High coupling modules

  config.py
  utils.py
```

## Onboarding Mode

```bash
explain-codebase onboarding .
```

This mode suggests a reading order for a new developer.

Example:

```text
1. server.ts
2. router.ts
3. user_controller.ts
4. user_service.ts
5. user_repository.ts
```

## Explain Single File

```bash
explain-codebase file src/services/user_service.ts
```

Single-file mode reports:

- File role
- Which files use it
- Which files it depends on
- Likely responsibilities
- Import counts
- Side effects

## HTML Outputs

Dependency graph:

```bash
explain-codebase . --graph
```

Generates:

```text
dependency_graph.html
```

Architecture report:

```bash
explain-codebase . --report
```

Generates:

```text
codebase_report.html
```

## CI Mode

```bash
explain-codebase . --ci
```

If architecture issues are found, the tool exits with code `1`.

## JSON Output

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
