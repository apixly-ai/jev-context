# Agent quickstart

[简体中文](agent-quickstart.zh-CN.md)

[Chinese](agent-quickstart.zh-CN.md) · [Full integration reference](agents.md)

**One tool call in; a compact evidence packet out.** Your agent supplies the task
and context. Jev Filter collects and judges internally. The agent handles planning,
open reasoning and unresolved evidence.

## 1. Install once

```sh
npm install -g @apixly/jev-filter
jev-filter doctor
```

Provide `TYPESAFE_API_KEY` or `TYPESAFE_API_KEY_FILE` in the agent tool environment.
Do not paste credentials into the prompt. Copy the supplied skill:

```sh
mkdir -p ~/.codex/skills
cp -R "$(npm root -g)/@apixly/jev-filter/skills/jev-filter" ~/.codex/skills/
```

For Claude Code, use `~/.claude/skills/`. Review existing local customizations before
replacing a skill. Installation does not automatically edit global instructions.

## 2. Make the routing choice

| Task | Route |
|---|---|
| Exact path, ID, field, selector or calculation | Native tool / deterministic code |
| Many records, clear repeated semantic judgment | Jev Filter |
| Planning, writing or open-ended reasoning | Primary model |
| Existing workflow already uses Jev | Call it directly; do not add another filter |

## 3. Pass a small context contract

Save as `analysis.json`:

```json
{
  "mode": "choose",
  "context": {"project": "Beta", "format": "JSON"},
  "required_context": ["project", "format"],
  "required_record_fields": ["source.project", "source.format"]
}
```

Then execute a complete, reproducible call:

```sh
jev-filter query --input - --analysis analysis.json \
  --task 'Choose the export matching the project and format in context' <<'JSON'
[
  {"id":"a","text":"Export records","project":"Alpha","format":"JSON"},
  {"id":"b","text":"Export records","project":"Beta","format":"JSON"},
  {"id":"c","text":"Export records","project":"Beta","format":"CSV"}
]
JSON
```

Expected: `selected_ids=["b"]`, `review_ids=[]`, `complete=true`. To use your real
collector, replace `query --input -` with `exec ... -- YOUR_COMMAND ARGS`; see the
[command recipe](recipes.md#1-custom-command-output). Keep raw collection inside
that call; do not dump it into the conversation first.

## 4. Consume, review, recover

- Use complete typed decisions for the stated predicate without repeating them.
- `review_ids` or `complete=false`: inspect only the necessary originals.
- Exit **2** still carries a parseable result; do not throw the packet away.
- Retrieve evidence with `jev-filter read ARCHIVE_PATH --id SOURCE_ID`.
- Keep permission, identity, freshness and execution verification in the host workflow.

Jev does not inherit your chat history. Supply relevant sourced facts and per-record
history; missing facts must remain unresolved. Automatic batching and up to 30 requests
are enabled; no result cache is used. [Context details](context-contract.md).

The legacy `jev-context` command and `jev_context` Python imports remain compatible.
For new Python integrations, use `from jev_filter.batch import run`.
