#!/usr/bin/env node
'use strict';
const path = require('node:path');
const { spawn } = require('node:child_process');

function platformPackage(platform = process.platform, arch = process.arch) {
  if (platform === 'win32') throw new Error('Use WSL: native Windows is not supported yet.');
  if (!['linux', 'darwin'].includes(platform) || !['x64', 'arm64'].includes(arch)) {
    throw new Error(`Unsupported platform: ${platform}/${arch}. See the Python installation guide.`);
  }
  return `@apixly/jev-context-${platform}-${arch}`;
}

function launch(args, deps = {}) {
  const name = platformPackage(deps.platform, deps.arch);
  let manifest;
  try { manifest = (deps.resolve || require.resolve)(`${name}/package.json`); }
  catch { throw new Error(`Missing ${name}. Reinstall without --omit=optional; platform binaries are optional dependencies.`); }
  const binary = path.join(path.dirname(manifest), 'bin', 'jev-context');
  const owner = deps.process || process;
  const child = (deps.spawn || spawn)(binary, args, { stdio: 'inherit', shell: false });
  const handlers = new Map();
  for (const signal of ['SIGINT', 'SIGTERM']) {
    const handler = () => child.kill(signal);
    handlers.set(signal, handler);
    owner.on(signal, handler);
  }
  const cleanup = () => {
    for (const [signal, handler] of handlers) owner.removeListener(signal, handler);
  };
  child.on('error', error => {
    cleanup();
    console.error(`jev-context: native executable could not start (${error.code || 'unknown'}). Reinstall the package.`);
    owner.exitCode = 1;
  });
  child.on('exit', (code, signal) => {
    cleanup();
    owner.exitCode = code ?? (signal === 'SIGINT' ? 130 : signal === 'SIGTERM' ? 143 : 1);
  });
  return child;
}

module.exports = { platformPackage, launch };
if (require.main === module) {
  try { launch(process.argv.slice(2)); }
  catch (error) { console.error(`jev-context: ${error.message}`); process.exitCode = 1; }
}
