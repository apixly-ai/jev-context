# Local statistics and dashboard

[简体中文](statistics.zh-CN.md)

Jev Filter can record a numeric-only local ledger and show it in a read-only browser dashboard.
Recording is opt-in. It does not change selection, cache inference, or run the primary model.

```sh
# Example rates only; replace with your verified USD per million token prices.
jev-filter stats configure --model YOUR_MODEL --counter bytes \
  --input-rate 10 --jev-input-rate 0.042 --jev-output-rate 0 \
  --price-source "your verified price source" --price-date 2026-09-23
jev-filter stats report
jev-filter stats dashboard
# Or export a new self-contained snapshot (does not overwrite):
jev-filter stats dashboard --html usage.html
```

The dashboard prints a token-protected `127.0.0.1` URL, remains running until Ctrl-C,
and refreshes on demand. It opens the URL in your default browser; use `--no-open` for headless/CI use. If no browser can be opened, the printed URL and server remain available. Without `--port`, it tries 8765 and automatically selects a free port if occupied. An explicitly busy port returns `PortInUse`; `--port 0` always selects an available port. It needs no frontend build, external scripts or hosted service.
Model, UTC date and counting-method filters apply to cards, charts, details and JSON export.
The table shows the newest 100 filtered events; exports include all filtered events.

## What the numbers mean

- **Input tokens avoided (estimate):** token count of normalized collected-record JSON minus
  the full rendered return packet, including metadata and trailing newline, counted once.
  This baseline is explicit: it is not the original shell byte stream or proof that an
  unfiltered agent would actually have read all records. It excludes whole-conversation
  overhead, subsequent rereads/retries and output changes.
- **Gross input value:** avoided tokens × the configured input USD/MTok rate.
- **Jev cost:** reported Jev input/output usage × configured Jev rates. Incomplete usage
  is unknown, never zero. These are estimates under the configured pricing, not invoices.
- **Net value:** gross input value minus Jev cost. Negative values remain visible.
  The full net total is unknown if any included row cannot be priced/compared. Known
  subtotals remain separately visible; failed/incomplete calls cannot create positive savings.
- **Uncompared:** typed `batch` logs Jev usage only. It has no reliable final primary-model
  output baseline. Passthrough and incomplete results do not count toward avoided tokens.

The configured model is a pricing/counting target, **not auto-detected Codex or Claude Code
identity**. Configure it when changing your target model. Each event stores its own price
snapshot/date/source; later configuration changes do not reprice history. Provider prompt
cache discounts, output cost differences, taxes and subscription quotas are not modeled.

## Counting modes

| Mode | Behavior |
|---|---|
| `bytes` | Offline UTF-8 bytes / 4, rounded up. Coarse estimate, not model tokenization. |
| `tiktoken` | Local text counts under a supported model mapping; requires Python `.[stats]` or a native build with the stats dependency. |
| `openai` | Opt-in official input-count API; sends both compared texts to OpenAI with `OPENAI_API_KEY`. |
| `anthropic` | Opt-in official message-count API; sends both compared texts to Anthropic with `ANTHROPIC_API_KEY`. |

For local tokenizer counts:

```sh
python -m pip install 'jev-filter[stats]'
jev-filter stats configure --model gpt-5.4 --counter tiktoken --input-rate YOUR_RATE
```

An unknown model mapping fails configuration rather than silently selecting another
model's encoding. `--encoding o200k_base` explicitly chooses an **encoding proxy estimate**;
this does not prove the target model uses that encoding. Tiktoken may download public
encoding data on first use; subsequent counts use the local encoding data. This is not a
semantic-result cache. Native bundles include the tokenizer dependency.

Official counters make two sequential requests per compared invocation, do not generate
answers, follow redirects or retry automatically, and add network latency. Missing keys,
provider errors and unknown counts remain visible as unknown; the original CLI operation
still returns normally. No API key is stored in the statistics configuration. Configure
these modes only for content you permit the corresponding provider to receive.

Official API results count the texts as isolated messages, not the full agent request.
Claude documents small differences between preflight counts and actual usage. A real
whole-operation saving still requires a paired baseline and actual primary-model usage.
See [OpenAI counting](https://developers.openai.com/api/docs/guides/token-counting) and
[Claude counting](https://platform.claude.com/docs/en/build-with-claude/token-counting).

## Coverage and storage

After configuration, the installed CLI automatically records `search`, `query`, `exec`,
`code-search`, `locate`, `triage` and the CLI `batch` entrypoint. Pure Python helper calls,
`read`/`list`, planning-only calls and errors before the recording boundary are not tracked.
There is no retrospective import or inference of historical savings.

The default directory is `~/.local/share/jev-filter/stats`; override with `JEV_STATS_DIR`.
SQLite stores only numeric measurements, model/tool names, status and price metadata—not
source text, queries, customer messages, archive paths or credentials. Writes are
transactional, files are private, and statistics failures never retry the underlying tool.
Exported HTML/JSON contains these statistics and should be treated as private.

```sh
jev-filter stats report --model YOUR_MODEL --since 2026-09-01 --until 2026-09-30
jev-filter stats disable                 # retain history, stop future recording
JEV_STATS_DISABLED=1 jev-filter ...      # skip this invocation
```

Optional `tiktoken`, remote counters and dashboard rendering are covered by isolated tests.
The default regression suite never uses the developer's ledger or counter credentials.
