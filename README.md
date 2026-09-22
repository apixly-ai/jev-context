# jev-context

[English](README.md) | [简体中文](README.zh-CN.md)

[![CI](https://github.com/JIA-ss/jev-context/actions/workflows/ci.yml/badge.svg)](https://github.com/JIA-ss/jev-context/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Give your agent the relevant evidence, without putting every raw tool result in its context.**

`jev-context` captures command output, search candidates, browser controls or event records inside a program. Jev performs bounded semantic judgments using the agent's task and context. The agent receives selected evidence, unresolved IDs and a private receipt for original records.

It supports caller-defined instructions, typed questions and output projection; automatic request packing; up to **30** concurrent requests; **no result cache**. It is an independent project maintained by JIA-ss, not an official TypeSafe product.

## Why use it?

Use it when a large set of records needs repetitive semantic decisions. Prefer native tools for exact IDs, paths, selectors, calculations and short results. Keep planning, open reasoning and writing in the primary agent.

The extra model call has a cost and latency. Savings depend on the number of records removed, the primary model's price and the quality of supplied context. This is **not a universal speedup or cost reduction**.

Our [benchmark report](docs/benchmarks.md) separates fresh public measurements from historical prototype results, includes negative outcomes and provides the runnable fixtures. Context reduction is not end-to-end cost reduction.

## Install

Python 3.10+ on Linux/macOS (Windows users: WSL). Install ripgrep for search.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install 'jev-context[code] @ git+https://github.com/JIA-ss/jev-context.git@v0.1.0'
export TYPESAFE_API_KEY='your-key'
jev-context doctor
```

Alternatively install the wheel from [Releases](https://github.com/JIA-ss/jev-context/releases). This project is not currently published on PyPI. A Jev API key is required for inference. `doctor` and `--plan` work without one. Use `TYPESAFE_API_KEY_FILE` for an owner-only credential file instead of an environment variable.

## Use

```sh
# Inspect the supplied example contract and candidate records first.
jev-context query --input examples/candidates.json --analysis examples/choose.json --task 'Select the matching project' --plan

# Capture the command internally; raw records do not first enter the agent context.
jev-context exec --task 'Find unresolved network failures' --analysis examples/triage.json -- cat examples/records.json

# Group related events and preserve uncertainty.
jev-context triage --input examples/events.jsonl --task 'Find unresolved network failures' --analysis examples/triage.json
```

The CLI also provides `search`, `code-search`, `locate`, typed `batch`, and evidence `read`/`list`. See [CLI reference](docs/cli.md) and [getting started](docs/getting-started.md). `exec` executes the command you supply; it is not a sandbox.

## Agent integration

Install or copy [the portable skill](skills/jev-context/SKILL.md) into your agent's skill directory. Add the routing guidance in [agent integration](docs/agents.md) to its instructions. No automatic global configuration edits are performed by installation.

Supply the goal, scope, exclusions, success criteria and sourced known facts. Put record-specific history on each record. Declare `required_context` and `required_record_fields`; missing facts produce review instead of a guess. The agent controls analysis and output through a [context contract](docs/context-contract.md).

Raw input is retained locally with restricted permissions; selected input is sent to the fixed TypeSafe API for inference. Unknown, malformed and failed items remain visible. A semantic judgment never grants permission to execute an action. [Security and trust boundaries](SECURITY.md).

## Develop and verify

```sh
python -m pip install -e '.[code,dev]'
sh scripts/check.sh
# Optional, billable: two repetitions, alternating arm order, no cache.
python -m benchmarks.run --live --output local-results/my-live-run.json
```

Tests, package build checks, dependency audit and CodeQL run through GitHub Actions. Tagged releases produce wheels, source archives, checksums and provenance attestations. See [contributing](CONTRIBUTING.md), [development](docs/development.md), [governance](GOVERNANCE.md), [changelog](CHANGELOG.md) and [MIT license](LICENSE).

We use this tool in our own environment. Private workflow identities, production data and credentials are deliberately excluded from this repository. Integration acceptance is separate from public synthetic benchmark claims.
