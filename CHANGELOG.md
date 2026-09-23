# Changelog

The format follows Keep a Changelog; versions follow SemVer within the limitations
of a 0.x API (minor releases may make documented breaking changes).

## [0.2.1] - 2026-09-23

### Fixed
- Dashboard startup automatically chooses a free loopback port if the default 8765 is occupied.
- Explicit busy ports return an actionable `PortInUse` error; `--port 0` selects an available port. Invalid port values are rejected before binding.
- Dashboard instances never share a listening port, including on Python versions with reusable-port defaults.

## [0.2.0] - 2026-09-23

### Added
- Opt-in, private SQLite usage ledger for CLI collection/filtering and typed-batch costs.
- Per-call input-token reduction and USD input-value estimates, Jev cost, price snapshots and explicit unknown/negative results.
- Local byte estimates, optional tiktoken text counts and opt-in official OpenAI/Anthropic counters.
- Read-only localhost dashboard with model/date/method filters, daily/tool breakdowns and filtered JSON/self-contained HTML exports.
- Isolated arithmetic, privacy, failure, API-adapter, concurrent-write and rendered desktop/mobile tests.

### Scope
- Statistics estimate normalized candidate JSON versus the returned packet once; they do not claim whole-agent or subscription invoice savings.
- No change to semantic predicates, inference planning, authorization or result-cache policy.

## [0.1.0] - 2026-09-22

### Added
- Portable packaged CLI and Python API with no private workspace dependencies.
- Context admission, typed selection/filtering, scoped evidence and failure retention.
- Code-search, browser locator, grouped JSON/JSONL triage, and caller-command wrapper.
- HTTPX connection reuse, bounded retries, up to 30 workers and no result cache.
- Optional Python-packaged JS/TS/Go grammar support; Python AST support is built in.
- English/Chinese documentation, agent skill, reproducible benchmarks and release CI.

[0.1.0]: https://github.com/JIA-ss/jev-filter/releases

- Native npm distribution for macOS and Linux x64/ARM64, including interpreter, parsers and pinned ripgrep.
- Visual bilingual README, data-derived charts, runnable recipes and agent integration instructions.
- Repository moved to Apixly; immutable release tags and restricted workflow permissions.
