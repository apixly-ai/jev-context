# Development, releases and reproducibility

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[code,dev]'
./scripts/check.sh
```

CI checks Linux/Python versions, macOS, lint/format, >=80% line coverage, package
build/install, public-content hygiene, offline benchmark planning, documentation examples. Live model tests are opt-in and never run on fork PRs.

Release procedure:

1. Prepare a PR updating pyproject version and CHANGELOG; include relevant A/B evidence.
2. Merge only after required checks pass. Tag `v<version>` on the reviewed commit.
3. The release workflow verifies the tag, builds wheel/sdist, validates the package (CI also installs the wheel in a
   clean environment), produces checksums and dependency inventory, and attaches
   artifacts plus build provenance to a GitHub Release.
4. Verify installation from the release artifact. Never replace a published tag;
   use a new patch version for a correction.

GitHub Releases are the distribution channel. PyPI publishing is not configured.
A future PyPI release requires a matching project and trusted publisher configuration.

Dependency updates arrive through Dependabot and must pass CI. Security reports use
private vulnerability reporting. A release is not a promise of an enterprise SLA.

## Repository protection

The hosted repository requires a PR, up-to-date required CI/security checks and
resolved conversations before merging to `main`. Administrators follow the same
branch protection. Force pushes and deletions are blocked; linear history is required.
As a single-maintainer bootstrap, the required approval count is zero; CODEOWNERS
identifies JIA-ss, and independent review should be required when another maintainer
is available. Passing checks is not an independent human review.

Release tags `v*` cannot be updated or deleted, including by an administrator under
the active ruleset. A separate creation rule limits release tags to the maintainer.
Default workflow tokens are read-only and cannot approve PRs; release/CodeQL jobs
request only their necessary additional permissions. Secret scanning, push protection,
Dependabot alerts/updates and private vulnerability reports are enabled.

See [npm/native distribution](distribution.md) for build and publication order.
