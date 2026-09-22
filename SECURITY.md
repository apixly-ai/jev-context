# Security policy

## Reporting

Use GitHub's **Report a vulnerability** button at
https://github.com/apixly-ai/jev-filter/security/advisories/new . Do not put sensitive
proofs or credentials in public issues. Reports are handled on a best-effort basis;
there is no contractual response-time guarantee.

## Supported versions

Security fixes target the latest 0.1.x release. Older prereleases should be upgraded.
See CHANGELOG.md and GitHub Releases for fixes.

## Trust boundaries

- `exec` runs exactly the caller's argv with the caller's OS permissions. It is not
  a sandbox, permission broker, or safe way to run untrusted commands.
- Jev is a remote service. Task context, selected source state and question definitions
  are sent to TypeSafe. No telemetry is sent elsewhere by this package.
- Credentials go only to the fixed HTTPS TypeSafe endpoint. Redirects are rejected;
  environment proxy/TLS settings are honored by HTTPX.
- Raw evidence receipts are local files created with mode 0600 and are not result
  caches. Their lifetime follows the OS temp directory unless a path is supplied.
- Redaction handles common patterns, not every possible secret format. Use a trusted
  sanitizer before supplying sensitive production data.
- A model decision is fallible. Required-context checks validate presence, not truth.
  Validate identities, source freshness, permissions and outcomes in the executor.
- Public PR CI has no model keys. Live benchmarks are explicit local operations.
