# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-02

### Added

- Added support for `.jsx`, `.tsx`, `.mjs`, `.cjs`, `.mts`, and `.cts` source files alongside `.py`, `.js`, and `.ts`.
- Added an installed-version command and cross-version continuous integration checks.
- Added a tag-driven PyPI release workflow with version validation, package checks, artifact handoff, and Trusted Publishing.
- Added complete package metadata, project links, a dedicated changelog, and a security policy.

### Changed

- Hardened local scanning with repository-root containment, symlink rejection, an optional file-count limit, and a 1 MiB per-file limit.
- Limited public GitHub repository preparation to shallow single-branch clones without tags, added a clone timeout, and improved failure handling.
- Improved Python, JavaScript, and TypeScript import resolution across relative paths, package entry files, and supported extension variants.
- Made command-line validation, error handling, output-stream separation, and exit behavior more predictable.
- Expanded package, parser, scanner, remote-target, and command-line tests.
- Refreshed installation, usage, output, and limitation documentation.

### Fixed

- Declared `click` as a direct runtime dependency instead of relying on Typer's transitive dependency.
- Corrected Python package imports, multi-level JavaScript and TypeScript relative imports, async route detection, and project-root selection for file analysis.
- Prevented isolated files from being reported as high-coupling hotspots and rejected non-positive file limits.
- Kept ordinary filesystem-module imports from being reported as side effects until an actual filesystem operation is detected.

### Security

- Disabled repository-configured Git hooks and filesystem monitors, sanitized Git subprocess environments, and bounded Git operations with time limits.
- Pinned third-party workflow actions to immutable commit revisions.
- Rejected source-file links, Windows directory reparse points, paths outside the selected root, and source files larger than 1 MiB.
- Replaced the unbounded JavaScript import pattern with a line-bounded parser.
- Added atomic HTML output, enforced configured node limits for focused graph views, and added a content security policy plus integrity verification for the browser-side graph library.

## [0.1.4] - 2026-03-19

### Changed

- Redesigned the interactive dependency graph for clearer structure and navigation.
- Added architecture, entrypoint, risk, side-effect, and full file-level graph views.
- Updated graph embedding in HTML reports.

## [0.1.3] - 2026-03-17

### Changed

- Refined documentation, examples, and command descriptions.

## [0.1.2] - 2026-03-17

### Added

- Added Git-aware scanning, `.gitignore` filtering, and tracked-file selection.
- Added built-in filtering for common dependency, cache, build, coverage, and environment directories.

## [0.1.1] - 2026-03-17

### Changed

- Updated the package summary and release metadata.

## [0.1.0] - 2026-03-17

### Added

- Published the initial command-line release with repository analysis, dependency graphs, JSON output, HTML reports, onboarding paths, and architecture checks.

[Unreleased]: https://github.com/danyasync/explain-codebase/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/danyasync/explain-codebase/compare/63e1285083b2bdb06de2212aeddcdaebb18e2649...v0.2.0
[0.1.4]: https://pypi.org/project/explain-codebase/0.1.4/
[0.1.3]: https://pypi.org/project/explain-codebase/0.1.3/
[0.1.2]: https://pypi.org/project/explain-codebase/0.1.2/
[0.1.1]: https://pypi.org/project/explain-codebase/0.1.1/
[0.1.0]: https://pypi.org/project/explain-codebase/0.1.0/
