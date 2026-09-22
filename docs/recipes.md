# Recipes: from an actual task to one CLI call

[简体中文](recipes.zh-CN.md)

Choose a recipe, write the contract, and replace only the collector or input path.
The agent should see the resulting packet—not the full input before filtering.

## 1. Custom command output

Create `analysis.json`:

```json
{
  "mode": "filter",
  "context": {
    "scope": "Current request attempts only",
    "success": "Keep establishment failures that have not recovered",
    "exclusions": "Past failures followed by a successful current attempt"
  },
  "required_context": ["scope", "success", "exclusions"],
  "requirements": [
    {"id":"network","statement":"The current request fails during DNS, TCP or TLS establishment.","expected":true},
    {"id":"response","statement":"The current request received HTTP response headers.","expected":false}
  ],
  "fields": ["source_id", "text", "answers", "source"]
}
```

Your collector should emit records like this JSON array:

```json
[
  {"id":"req-17","text":"TLS verification failed before any HTTP response.","request_id":"req-17"},
  {"id":"req-18","text":"An earlier timeout recovered. Current request returned HTTP 200.","request_id":"req-18"}
]
```

Then run:

```sh
jev-filter exec --analysis analysis.json \
  --task 'Find current network establishment failures' \
  -- your-collector --json
```

`your-collector` is the command you already use; it is not shipped by this package.
For a runnable fixture, save the array as `records.json` and replace the command with
`cat records.json`. Add `--plan` before `--` to collect once without model inference.
`--plan` still executes the collector. For arbitrary text output use self-contained
paragraphs; split lines only when each line has enough context to stand alone.

## 2. Select with context

Reuse [choose.json](../examples/choose.json) with [candidates.json](../examples/candidates.json):

```sh
jev-filter query --input examples/candidates.json \
  --analysis examples/choose.json \
  --task 'Choose the JSON export belonging to project Beta'
```

The `context` distinguishes otherwise similar candidates. `required_record_fields`
prevents selection when a competitor's project/format is missing. Supply only observed
metadata; a field existing is not proof that its value is correct.

## 3. Search whole code symbols

```sh
jev-filter code-search 'retry|backoff' --root ./src \
  --task 'Find the implementation that retries transient network failures'
```

The lexical search narrows candidates; the collector expands hits to full functions
or methods for semantic judgment. Python works out of the box; native npm bundles
also include JS/TS/Go parsers. A lexical shortlist is not a complete semantic index.
Use native `rg` directly if you already know the exact symbol.

## 4. Find a browser control

Use an existing local Camofox server and observed session/tab IDs:

```sh
jev-filter locate --session YOUR_SESSION --tab YOUR_TAB \
  --origin https://example.com \
  --task 'Select the enabled Continue control in the checkout form'
```

The locator only observes and verifies a candidate. It never navigates, clicks or
submits. Keep the returned selector with its freshness information and reverify
before action. Duplicate or changed targets require review. Domain-specific session
restrictions remain the responsibility of your installed workflow.

## 5. Triage correlated events

```sh
jev-filter triage --input examples/events.jsonl \
  --analysis examples/triage.json \
  --task 'Find current network establishment failures'
```

Grouping preserves event order within a request. A historical timeout followed by a
current success should not become a new unresolved incident. Malformed rows and
incomplete evidence remain visible. A label does not establish live recovery.

## Output customization

Use `questions` for typed Choice/Noul/Score decisions and `output` for a nested
projection. With an `intent` Choice question, this returns your own field names:

```json
{"output":{"record":"source_id","classification":"answers.intent.choice"}}
```

This is a fragment to combine with a complete question contract, not a standalone
analysis file. See the [context contract](context-contract.md) for required fields,
filter/review rules and the JSON schema.
