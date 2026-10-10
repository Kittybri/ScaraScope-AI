"""Guardrails that prevent the project from regressing to a monolithic bot."""
import ast
from pathlib import Path

import scarascope
from scarascope.api import app, get_settings
from scarascope.core.config import Settings
from scarascope.discord_bot import main as discord_main


ROOT = Path(scarascope.__file__).resolve().parent


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_core_is_independent_of_external_interfaces():
    """Financial math, SEC parsing, AI providers, and services must not import UI frameworks."""
    for directory in ("core", "finance", "data", "ai", "services", "storage"):
        for path in (ROOT / directory).rglob("*.py"):
            disallowed = _imports(path).intersection({"discord", "fastapi"})
            assert not disallowed, f"{path.relative_to(ROOT)} imports UI framework(s): {disallowed}"


def test_launch_entrypoints_remain_available():
    assert app.title == "ScaraScope AI"
    assert isinstance(get_settings(), Settings)
    assert callable(discord_main)
    launcher = ROOT / "discord_bot.py"
    assert len(launcher.read_text(encoding="utf-8").splitlines()) < 20


def test_no_flat_monolithic_feature_modules():
    """New feature code belongs in packages, not scarascope/bot.py or scarascope/service.py."""
    assert not (ROOT / "bot.py").exists()
    assert not (ROOT / "service.py").exists()
    assert not (ROOT / "providers.py").exists()
