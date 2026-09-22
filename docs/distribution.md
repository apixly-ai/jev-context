# npm and native distribution

[简体中文](distribution.zh-CN.md)

The primary installation is `npm install -g @apixly/jev-filter`. Python users keep
the release wheel/library interface. Both call the same semantic core.

## Design

A small Node launcher chooses a platform package through `optionalDependencies`.
The platform package contains an executable plus its private interpreter/libraries,
code parsers and a pinned ripgrep binary. No user Python environment is modified;
there are no postinstall scripts. This follows the distribution pattern used by
[Codex](https://github.com/openai/codex/blob/main/codex-cli/scripts/build_npm_package.py)
and [esbuild](https://github.com/evanw/esbuild/blob/main/npm/esbuild/package.json),
with platform packages on npm and mirrored tarballs on GitHub Releases.

The launcher preserves argument boundaries, streams and exit status. It does not
pass user input through an implicit shell. Linux bundles require glibc; Alpine/musl
is not currently supported by the bundled Python runtime. macOS Intel/Apple Silicon
and Linux x64/ARM64 are built and smoke-tested separately. Windows uses WSL.

## What is verified

- Install actual npm tarballs with lifecycle scripts disabled.
- Remove system Python and ripgrep from PATH.
- Run `doctor` and a real code-search fixture using the bundled runtime/parser/rg.
- Run source tests independently on Python 3.10–3.14 and macOS.
- Verify ripgrep assets against checked-in upstream SHA-256 digests before packaging.
- Ship package licenses, Python license and bundled dependency notices.

Native distribution improves installation, not semantic quality. Startup, disk size
and install downloads are extra costs; no speedup is inferred from bundling.

## Release order

1. Merge the version PR after required source/security/native checks.
2. Create `v<version>` on that reviewed commit. Protected tags cannot be rewritten.
3. GitHub Actions rebuilds all four platform tarballs, wheel/sdist and the main npm
   package, checks them, then publishes checksums and provenance with the release.
4. Publish the four verified platform tarballs, then the main tarball with
   `npm publish --access public`. Never publish credentials or rewrite an existing
   npm version.
5. Verify a clean `npm install` from the registry and the installed CLI.

npm trusted publishing should use the repository's `publish-npm.yml` workflow after
the package-level trusted publisher is configured. It avoids a long-lived registry
secret; GitHub's OIDC provenance ties publication to the workflow/source.
The first package can be bootstrapped with an authenticated maintainer session.

Each platform package includes `BUILDINFO.json` with runtime versions and file hashes; installer-origin paths are removed and package contents checked before publication.
