"""Guard the direct dependencies of the implemented domain and use-case layers."""

import ast
from pathlib import Path

import dota2forge_core

from scripts.check_governance import imported_modules


def test_domain_ports_and_use_cases_do_not_import_io_or_infrastructure():
    root = Path(dota2forge_core.__file__).parent
    forbidden = {
        "sqlite3",
        "urllib",
        "http",
        "httpx",
        "aiohttp",
        "requests",
        "os",
        "pathlib",
        "dotenv",
        "subprocess",
        "socket",
        "infrastructure",
    }
    for path in [*root.joinpath("domain").glob("*.py"), root / "ports.py", root / "use_cases.py"]:
        tree = ast.parse(path.read_text("utf-8"))
        for name in imported_modules(tree):
            assert not forbidden.intersection(name.split(".")), (path.name, name)
