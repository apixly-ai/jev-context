# Agent integration

Copy `skills/jev-context/` into your agent's supported skill directory. For Codex,
that can be `~/.codex/skills/jev-context`; other agents may use their own locations.
The skill is portable and contains no maintainer-specific paths or business policy.

Recommended routing:

- Exact paths, selectors, field checks, arithmetic, short/latency-sensitive results:
  use native tools/code.
- Many independent records needing clear semantic judgment: use Jev Context.
- Open-ended reasoning or code generation: use the primary model.
- A maintained workflow already using Jev: consume its packet, do not wrap it again.

Prepare the task/spec once. Keep object-specific evidence isolated. For
`complete=true` with no unresolved IDs, consume the typed result for that predicate;
review only unresolved evidence, retaining already settled results. This is fallible
judgment, not permission or execution proof. Use a host shell wait around 30 seconds
when supported and poll only an actual running command.

Python callers can import `jev_context.analysis` (`plan`, `evaluate`, `summarize`)
or `jev_context.batch.run` for existing native typed request contracts. Credentials
are loaded by the provider. There is no need to spawn another agent just to call the
library. Public receipts/projections can be consumed by any shell-capable harness.
