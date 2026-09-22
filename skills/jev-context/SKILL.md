---
name: jev-context
description: Use Jev Context for program-owned semantic filtering, candidate selection, code search and grouped log triage when many records need clear typed judgments. Prefer native tools for exact or short tasks; not a replacement for open-ended reasoning or action authorization.
---

# Jev Context

Requires an installed `jev-context` CLI and the user's TypeSafe credentials. Use
`jev-context doctor` for local readiness; `--live` is explicitly billable.

- Choose `code-search` for symbol-expanded source candidates, `locate` for an
  observed Camofox target, `triage` for correlated JSON/JSONL events, and `exec` or
  `query` for a custom collector. Use `--help` for exact flags.
- Keep collection and analysis in one program segment. Do not first read the whole
  raw output into the main model and then call a redundant classifier.
- Provide the precise goal, intended scope, confirmed facts with sources and success
  criteria. Declare necessary context fields. Shared policy belongs in `context`;
  object-specific history stays with that record. Never fill missing facts by guessing.
- Use positive atomic requirements for compound logic, or Choice for mutually
  exclusive intents. Questions, thresholds and output schema are caller-controlled.
- Allow automatic batching/connection reuse, up to 30 independent requests. No result
  cache. Dependent browser actions stay ordered.
- Consume complete typed results without reclassifying every settled row. Inspect
  only unresolved originals. Do not retry an uncertain external command.
- Preserve scope, source freshness, identity and authorization checks. A selected
  target is not proof of an executed action. The locator does not click.
- New semantic integrations need an A/B with fixed inputs, quality, failures, complete
  operation time and actual usage. Keep negative results; do not promise universal
  cost or latency improvement.

See [contract and examples](references/contract.md) for input/output details.
