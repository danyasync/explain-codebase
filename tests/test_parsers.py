from __future__ import annotations

from pathlib import Path

import pytest

from explain_codebase.detectors.language_detector import LanguageDetector
from explain_codebase.graph.dependency_graph import DependencyGraphBuilder
from explain_codebase.models.file_info import FileInfo
from explain_codebase.parsers.js_parser import JavaScriptParser
from explain_codebase.parsers.python_parser import PythonParser


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize("statement", ["from . import service", "from pkg import service"])
def test_python_from_import_resolves_submodule_edge(tmp_path: Path, statement: str) -> None:
    init_path = _write(tmp_path / "pkg" / "__init__.py", "")
    service_path = _write(tmp_path / "pkg" / "service.py", "VALUE = 1\n")
    consumer_path = _write(tmp_path / "pkg" / "consumer.py", f"{statement}\n")

    parser = PythonParser()
    files = [parser.parse(path, tmp_path) for path in [init_path, service_path, consumer_path]]
    graph = DependencyGraphBuilder().build(files)

    assert graph.has_edge("pkg/consumer.py", "pkg/service.py")


def test_javascript_parent_segments_are_normalized(tmp_path: Path) -> None:
    source_path = _write(
        tmp_path / "src" / "features" / "orders" / "controller.js",
        'import util from "../../shared/util";\n',
    )
    target_path = _write(tmp_path / "src" / "shared" / "util.js", "export default {};\n")

    parser = JavaScriptParser()
    files = [parser.parse(path, tmp_path) for path in [source_path, target_path]]
    graph = DependencyGraphBuilder().build(files)

    assert graph.has_edge("src/features/orders/controller.js", "src/shared/util.js")


def test_javascript_import_cannot_escape_project_root() -> None:
    files = [
        FileInfo(
            path="src/controller.js",
            language="javascript",
            imports=["../../outside"],
        ),
        FileInfo(path="outside.js", language="javascript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert not graph.has_edge("src/controller.js", "outside.js")


def test_python_relative_import_cannot_escape_top_level_package() -> None:
    files = [
        FileInfo(path="pkg/controller.py", language="python", imports=["..outside"]),
        FileInfo(path="outside.py", language="python"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert not graph.has_edge("pkg/controller.py", "outside.py")


def test_javascript_import_parser_handles_supported_static_forms(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "module.js",
        "\n".join(
            [
                'import value from "./value";',
                'import "./setup";',
                'const legacy = require ( "./legacy" );',
            ]
        ),
    )

    info = JavaScriptParser().parse(path, tmp_path)

    assert info.imports == ["./value", "./setup", "./legacy"]


def test_javascript_import_parser_handles_long_malformed_line_linearly(tmp_path: Path) -> None:
    malformed_import = "import " + (" " * 200_000) + "identifier"
    path = _write(tmp_path / "module.js", f"{malformed_import}\nconst ok = require('./ok');\n")

    info = JavaScriptParser().parse(path, tmp_path)

    assert info.imports == ["./ok"]


def test_javascript_function_parser_handles_long_malformed_line_linearly(tmp_path: Path) -> None:
    malformed_function = "const stuck = " + (" " * 200_000) + "value"
    path = _write(tmp_path / "module.js", f"{malformed_function}\nfunction ready() {{}}\n")

    info = JavaScriptParser().parse(path, tmp_path)

    assert info.functions == ["ready"]


def test_javascript_function_parser_handles_arrow_functions(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "module.js",
        "const first = value => value;\nconst second = (left, right) => left + right;\n",
    )

    info = JavaScriptParser().parse(path, tmp_path)

    assert info.functions == ["first", "second"]


def test_javascript_function_parser_handles_async_typed_and_multiline_arrows(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "module.ts",
        "\n".join(
            [
                "const handler = async (request) => request;",
                "const identity = async => async;",
                "const parse = (value: string): number => value.length;",
                "const combine = (",
                "  left: string,",
                "  right: string,",
                ") => left + right;",
            ]
        ),
    )

    info = JavaScriptParser().parse(path, tmp_path)

    assert info.functions == ["handler", "identity", "parse", "combine"]


def test_async_route_decorator_is_recorded(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "endpoints.py",
        '@router.get("/items")\nasync def list_items():\n    return []\n',
    )

    info = PythonParser().parse(path, tmp_path)

    assert info.functions == ["list_items"]
    assert info.decorators == ["router.get"]
    assert info.route_handlers == ["list_items"]


@pytest.mark.parametrize("decorator", ["api_route", "websocket", "websocket_route", "head", "options", "trace"])
def test_common_route_decorators_are_recorded(tmp_path: Path, decorator: str) -> None:
    path = _write(
        tmp_path / "endpoints.py",
        f'@router.{decorator}("/items")\ndef list_items():\n    return []\n',
    )

    info = PythonParser().parse(path, tmp_path)

    assert info.route_handlers == ["list_items"]


def test_non_route_decorator_name_is_not_misclassified(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "worker.py",
        "@target()\ndef run_job():\n    return None\n",
    )

    info = PythonParser().parse(path, tmp_path)

    assert info.decorators == ["target"]
    assert info.route_handlers == []


@pytest.mark.parametrize(
    "content",
    [
        'from pathlib import Path\nvalue = Path("settings.toml")\n',
        'import os\nvalue = os.path.join("one", "two")\n',
        "import shutil\n",
        "import tempfile\n",
    ],
)
def test_simple_filesystem_import_does_not_count_as_side_effect(tmp_path: Path, content: str) -> None:
    path = _write(tmp_path / "module.py", content)

    info = PythonParser().parse(path, tmp_path)

    assert not info.has_side_effects
    assert "filesystem" not in info.side_effects


def test_filesystem_operation_still_counts_as_side_effect(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "module.py",
        'from pathlib import Path\nvalue = Path("settings.toml").read_text()\n',
    )

    info = PythonParser().parse(path, tmp_path)

    assert info.has_side_effects
    assert "filesystem" in info.side_effects


def test_os_mutation_counts_as_filesystem_side_effect(tmp_path: Path) -> None:
    path = _write(tmp_path / "cleanup.py", 'import os\nos.remove("stale.txt")\n')

    info = PythonParser().parse(path, tmp_path)

    assert info.has_side_effects
    assert "filesystem" in info.side_effects


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        (".js", "javascript"),
        (".jsx", "javascript"),
        (".mjs", "javascript"),
        (".cjs", "javascript"),
        (".ts", "typescript"),
        (".tsx", "typescript"),
        (".mts", "typescript"),
        (".cts", "typescript"),
    ],
)
def test_language_detector_supports_javascript_and_typescript_variants(suffix: str, expected: str) -> None:
    assert LanguageDetector().detect(Path(f"module{suffix}")) == expected


def test_dependency_graph_resolves_typescript_variant(tmp_path: Path) -> None:
    files = [
        FileInfo(
            path="src/features/view.tsx",
            language="typescript",
            imports=["../shared/widget"],
        ),
        FileInfo(path="src/shared/widget.tsx", language="typescript"),
    ]

    graph = DependencyGraphBuilder().build(files)

    assert graph.has_edge("src/features/view.tsx", "src/shared/widget.tsx")
