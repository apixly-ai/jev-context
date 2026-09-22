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
