# Getting started

Requirements: Python 3.10+ on Linux or macOS. Install `ripgrep` for search. The `code`
extra supplies JS/TS/Go parsers; Python parsing uses the standard library.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install 'jev-context[code] @ git+https://github.com/JIA-ss/jev-context.git@v0.1.0'
export TYPESAFE_API_KEY='your-own-key'
jev-context doctor
```

`doctor` is offline by default. `doctor --live` makes one small, billable synthetic
request. Alternatively set `TYPESAFE_API_KEY_FILE` to a regular file owned by you,
mode 0600; the default is `$XDG_CONFIG_HOME/jev-context/api-key` (or
`~/.config/jev-context/api-key`). Keys never belong in command arguments or Git.
The CLI honors environment proxy/TLS settings and sends the key only to TypeSafe's
fixed HTTPS origin.

From a checkout, try:

```sh
jev-context query --input examples/records.json --task 'Find current establishment failures' --analysis examples/triage.json
jev-context query --input examples/candidates.json --task 'Choose the export matching the caller context' --analysis examples/choose.json
```

The first example deliberately contains unknown evidence, so exit 2 is expected:
read `selected_ids` and `review_ids`. A partial result is not discarded. Use `archive`
and `receipt` to inspect originals/diagnostics locally. Those files are private and
are not reused for inference caching.

No PyPI publication is assumed. Install from a GitHub tag or the wheel attached to
GitHub Releases. A registry publishing workflow is optional and documented separately.
