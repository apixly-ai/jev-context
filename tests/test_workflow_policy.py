"""Preserve release gates while avoiding redundant branch/PR validation runs."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.load(
        (ROOT / ".github/workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )


def test_ci_runs_once_for_pr_and_also_checks_main_and_tags():
    events = workflow("ci.yml")["on"]
    assert isinstance(events, dict)
    assert events["push"]["branches"] == ["main"]
    assert events["push"]["tags"] == ["v*"]
    assert "pull_request" in events and "workflow_dispatch" in events


def test_obsolete_validation_cancels_but_releases_are_not_interrupted():
    for filename in ["ci.yml", "docs.yml", "security.yml"]:
        assert workflow(filename)["concurrency"]["cancel-in-progress"] == "true"
    assert "pull_request" in workflow("native.yml")["concurrency"]["cancel-in-progress"]
    assert workflow("release.yml")["concurrency"]["cancel-in-progress"] == "false"
    assert workflow("publish-npm.yml")["concurrency"]["cancel-in-progress"] == "false"


def test_tokenizer_dependencies_are_in_security_audit_and_release_sbom():
    for filename, job in [("security.yml", "audit"), ("release.yml", "release")]:
        commands = "\n".join(
            step.get("run", "") for step in workflow(filename)["jobs"][job]["steps"]
        )
        installs = [
            line for line in commands.splitlines() if "pip install" in line and ".[" in line
        ]
        assert any("stats" in line for line in installs)
        assert "pip_audit" in commands
