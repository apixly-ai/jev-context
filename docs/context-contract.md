# Context and decision contract

Jev cannot see the calling agent's chat history. Supply the information that can
change the decision: precise goal, intended scope, verified facts with references,
exclusions, success criteria and expected output. Do not paste the entire chat or
turn an assumption into a fact.

Shared rules belong in `context`; per-customer/page/request facts belong in that
record's metadata. The collector supplies current observations and revisions.

```json
{
  "mode": "choose",
  "context": {"scope": {"project": "Beta"}, "format": "JSON"},
  "required_context": ["scope.project", "format"],
  "required_record_fields": ["source.project", "source.format"]
}
```

This requires a collector that actually emits project/format metadata. Missing,
null or empty required caller values stop before collection/inference. False and
zero are valid. Missing per-record context holds that record for review; unique
selection waits when any competitor lacks required context. Presence is not proof
of truth. Sources, identity and freshness still need independent verification.

For compound logic, supply positive atomic `requirements` with boolean `expected`.
Jev returns SUPPORTED/CONTRADICTED/UNKNOWN for each; code excludes any known mismatch,
otherwise retains unknowns, otherwise matches. No arbitrary generated text is used
as executable logic.

Custom `questions` support Choice, Noul and Score. A `filter`/`review` uses a question
and `in`, `min` or `max`; `order` supports category `values` or numeric `descending`.
`fields` projects row fields; `output` maps custom nested keys to dictionary paths
such as `answers.intent.choice`. No template eval. Default answer display is compact;
full distributions stay in the receipt. Decision/source identity cannot be hidden.

The machine-readable input schema is in `schemas/analysis.schema.json`. Runtime
validation and required-context admission remain authoritative. A schema does not
prove that a chosen predicate captures the real business question.
