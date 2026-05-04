from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = [
        check_feature_list,
        check_docs_links,
        run_tests,
        run_operator_smoke,
        run_cli_smoke,
    ]
    for check in checks:
        check()
    print("dev_check: ok")
    return 0


def check_feature_list() -> None:
    data = json.loads((ROOT / "docs/feature-list.json").read_text(encoding="utf-8"))
    assert isinstance(data, list), "feature-list.json must be a list"
    for item in data:
        assert {"id", "priority", "description", "acceptance_steps", "passes"} <= set(item), item


def check_docs_links() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for path in [
        "ARCHITECTURE.md",
        "docs/TESTING.md",
        "docs/QUALITY.md",
        "docs/ROADMAP.md",
        "docs/UI_STRATEGY.md",
        "docs/USAGE.md",
        "docs/exec-plans/active/mvp-platform-applications-agent.md",
        "docs/agent-progress.md",
        "docs/feature-list.json",
    ]:
        assert path in agents, f"AGENTS.md must reference {path}"


def run_tests() -> None:
    env = _env()
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, env=env, check=True)


def run_cli_smoke() -> None:
    env = _env()
    subprocess.run([sys.executable, "-m", "balance_fundraising.cli", "--help"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)


def run_operator_smoke() -> None:
    env = _env()
    subprocess.run([sys.executable, "scripts/smoke_operator_workflow.py"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


if __name__ == "__main__":
    raise SystemExit(main())
