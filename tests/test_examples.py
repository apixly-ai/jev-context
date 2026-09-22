"""Published examples and newly portable symbol collection stay executable."""

import json
from pathlib import Path

from jev_context import analysis
from jev_context.symbols import parse_symbols

ROOT = Path(__file__).resolve().parents[1]


def test_contract_examples():
    for name in ("choose", "triage"):
        analysis.validate(json.loads((ROOT / "examples" / f"{name}.json").read_text()))


def test_go_receiver_and_function():
    text = "package example\ntype Client struct {}\nfunc (c *Client) Send() bool { return true }\nfunc Open() {}\n"
    found = parse_symbols("example.go", text)
    assert [x["symbol"] for x in found] == ["Client.Send", "Open"]
    assert found[0]["line"] == 3


def test_markdown_relative_links_exist():
    import re

    for p in [*ROOT.glob("*.md"), *ROOT.glob("docs/*.md"), *ROOT.glob("skills/**/*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            assert (p.parent / target.split("#")[0]).exists(), (p, target)
