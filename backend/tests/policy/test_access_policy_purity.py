"""El modulo de politica debe ser puro: sin fastapi ni sqlalchemy (PR-03.1).

Se comprueba sobre el AST del fichero fuente, sin importarlo.
"""

import ast
from pathlib import Path

import pytest

ACCESS_POLICY_PATH = Path(__file__).resolve().parents[2] / "access_policy.py"


def _imported_root_modules(source: str) -> set[str]:
    tree = ast.parse(source, filename=str(ACCESS_POLICY_PATH))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("forbidden", ["fastapi", "sqlalchemy"])
def test_access_policy_source_does_not_import_forbidden_framework(forbidden):
    assert ACCESS_POLICY_PATH.exists(), f"No existe {ACCESS_POLICY_PATH}"
    source = ACCESS_POLICY_PATH.read_text(encoding="utf-8")

    imported = _imported_root_modules(source)

    assert forbidden not in imported, (
        f"access_policy.py importa '{forbidden}' y debe ser un modulo puro"
    )
