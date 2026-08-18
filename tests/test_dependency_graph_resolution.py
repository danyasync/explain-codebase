from __future__ import annotations

import pytest

from explain_codebase.graph.dependency_graph import DependencyGraphBuilder
from explain_codebase.models.file_info import FileInfo


@pytest.mark.parametrize(
    "files",
    [
        [
            FileInfo(path="main.py", language="python", imports=["service"]),
            FileInfo(path="service.ts", language="typescript"),
            FileInfo(path="service.js", language="javascript"),
            FileInfo(path="service.py", language="python"),
        ],
        [
            FileInfo(path="service.py", language="python"),
            FileInfo(path="service.js", language="javascript"),
            FileInfo(path="service.ts", language="typescript"),
            FileInfo(path="main.py", language="python", imports=["service"]),
        ],
    ],
)
def test_python_resolution_is_language_specific_and_order_independent(files: list[FileInfo]) -> None:
    graph = DependencyGraphBuilder().build(files)

    assert set(graph.successors("main.py")) == {"service.py"}


def test_python_does_not_fall_back_to_another_language() -> None:
    files = [
        FileInfo(path="main.py", language="python", imports=["service"]),
        FileInfo(path="service.js", language="javascript"),
        FileInfo(path="service.ts", language="typescript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert list(graph.successors("main.py")) == []


def test_python_src_layout_supports_package_imports() -> None:
    files = [
        FileInfo(path="src/app/main.py", language="python", imports=["app.service"]),
        FileInfo(path="src/app/service.py", language="python"),
        FileInfo(path="app/service.js", language="javascript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert set(graph.successors("src/app/main.py")) == {"src/app/service.py"}


def test_javascript_resolution_stays_in_javascript_family() -> None:
    files = [
        FileInfo(path="src/main.js", language="javascript", imports=["./service"]),
        FileInfo(path="src/service.py", language="python"),
        FileInfo(path="src/service.ts", language="typescript"),
        FileInfo(path="src/service.js", language="javascript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert set(graph.successors("src/main.js")) == {"src/service.js"}


def test_typescript_prefers_typescript_before_javascript_fallback() -> None:
    files = [
        FileInfo(path="src/main.ts", language="typescript", imports=["./service"]),
        FileInfo(path="src/service.py", language="python"),
        FileInfo(path="src/service.js", language="javascript"),
        FileInfo(path="src/service.ts", language="typescript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert set(graph.successors("src/main.ts")) == {"src/service.ts"}


def test_typescript_can_reference_javascript_in_a_mixed_project() -> None:
    files = [
        FileInfo(path="src/main.ts", language="typescript", imports=["./legacy"]),
        FileInfo(path="src/legacy.js", language="javascript"),
        FileInfo(path="src/legacy.py", language="python"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert set(graph.successors("src/main.ts")) == {"src/legacy.js"}


def test_explicit_extension_is_resolved_exactly() -> None:
    files = [
        FileInfo(path="src/main.ts", language="typescript", imports=["./service.js"]),
        FileInfo(path="src/browser.js", language="javascript", imports=["./service.ts"]),
        FileInfo(path="src/service.js", language="javascript"),
        FileInfo(path="src/service.ts", language="typescript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert set(graph.successors("src/main.ts")) == {"src/service.js"}
    assert list(graph.successors("src/browser.js")) == []


@pytest.mark.parametrize("language, suffix", [("javascript", ".js"), ("typescript", ".ts")])
def test_bare_javascript_and_typescript_packages_remain_external(language: str, suffix: str) -> None:
    files = [
        FileInfo(path=f"src/main{suffix}", language=language, imports=["vendor"]),
        FileInfo(path=f"vendor/index{suffix}", language=language),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert list(graph.successors(f"src/main{suffix}")) == []


def test_unresolved_import_count_includes_local_references_but_not_external_packages() -> None:
    files = [
        FileInfo(
            path="src/app/main.py",
            language="python",
            imports=["app.service", "app.missing", "requests"],
        ),
        FileInfo(path="src/app/service.py", language="python"),
        FileInfo(path="web/main.js", language="javascript", imports=["./missing", "react"]),
    ]
    builder = DependencyGraphBuilder()

    builder.build(files)

    assert builder.unresolved_imports == 2

    builder.build([FileInfo(path="standalone.py", language="python")])
    assert builder.unresolved_imports == 0


def test_unresolved_import_count_does_not_count_members_of_the_same_module() -> None:
    files = [
        FileInfo(
            path="src/app/main.py",
            language="python",
            imports=["app.service", "app.service.VALUE", "app.missing", "app.missing.VALUE"],
            import_groups=[
                ["app.service", "app.service.VALUE"],
                ["app.missing", "app.missing.VALUE"],
            ],
        ),
        FileInfo(path="src/app/service.py", language="python"),
    ]
    builder = DependencyGraphBuilder()

    builder.build(files)

    assert builder.unresolved_imports == 1


def test_independent_child_import_is_not_covered_by_resolved_parent() -> None:
    files = [
        FileInfo(path="src/main.js", language="javascript", imports=["./foo", "./foo/bar"]),
        FileInfo(path="src/foo.js", language="javascript"),
        FileInfo(path="app/main.py", language="python", imports=["app", "app.missing"]),
        FileInfo(path="app/__init__.py", language="python"),
    ]
    builder = DependencyGraphBuilder()

    builder.build(files)

    assert builder.unresolved_imports == 2
