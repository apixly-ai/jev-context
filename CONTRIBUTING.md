# Contributing

Thanks for helping make semantic tools measurable and inspectable.

1. Open an issue for a new feature or compatibility change; include the intended
   outcome and a minimal, synthetic example. Small documented fixes can go directly
   to a PR.
2. Fork/branch, create a virtual environment, and install `pip install -e '.[code,dev]'`.
3. Add a failing test, implement the change, and run `scripts/check.sh`.
4. Update both READMEs when user-facing behavior changes. Add a changelog entry.
5. Include A/B evidence for semantic/runtime changes. Keep all failures and identify
   offline planning checks versus billable model experiments.

PRs use Conventional Commit-style titles (`fix:`, `feat:`, `docs:`, `test:`, `chore:`).
CI must pass before merging. Main is protected; force pushes and branch deletion are
blocked. The initial solo-maintainer policy requires PRs and status checks, not an
unavailable second-person approval. External changes receive maintainer review.

Do not submit customer data, prompts from private work, tokens, browser state,
absolute home paths, or unsanitized model traces. Report security issues privately
using SECURITY.md. By contributing, you license your contribution under MIT.

Supported environments: Linux/macOS, Python 3.10+. Native Windows execution is not
supported in 0.1; use WSL. `rg` is required for search. Optional code grammars are
installed by the `code` extra. Browser verification uses a local Camofox-compatible
service; its test suite uses a controlled Playwright page.
