#!/usr/bin/env node
// Run the pinned agent-desktop CLI with a private state folder.
//   node ad.mjs <agent-desktop arguments...>
// Looks for the binary at, in order:
//   %WINOPS_AGENT_DESKTOP%                                   (full path to agent-desktop.exe)
//   %LOCALAPPDATA%/agent-desktop/<version>/bin/agent-desktop.exe
// State goes to %AGENT_DESKTOP_HOME% or %LOCALAPPDATA%/agent-desktop/state. The default ~/.agent-desktop
// can pick up extra permissions from the Codex sandbox, and agent-desktop then refuses to use it.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const VERSION = '1.3.1';
const SHA256 = '6ee4b1e078f4e78792e79f16e32e4a78b9919464aa3c55629b7e27ed53a08c13';
if (process.platform !== 'win32') { console.error('windows-ops: this launcher is for Windows only.'); process.exit(2); }
const base = join(process.env.LOCALAPPDATA || '', 'agent-desktop');
const exe = process.env.WINOPS_AGENT_DESKTOP || join(base, VERSION, 'bin', 'agent-desktop.exe');
if (!existsSync(exe)) {
  const dir = join(base, VERSION).replace(/\\/g, '/');
  const file = `agent-desktop-v${VERSION}-x86_64-pc-windows-msvc.tar.gz`;
  console.error(`agent-desktop ${VERSION} is not installed at ${exe}.
Ask the user before installing. It is an unsigned program from github.com/vercel-labs/agent-desktop (about 1.8 MB).
To install it (Git Bash):
  mkdir -p "${dir}/dl" "${dir}/bin" && cd "${dir}/dl" &&
  curl -fsSLO https://github.com/vercel-labs/agent-desktop/releases/download/v${VERSION}/${file} &&
  echo "${SHA256} *${file}" | sha256sum -c - &&
  cd ../bin && tar -xzf ../dl/${file}
Or set WINOPS_AGENT_DESKTOP to an agent-desktop.exe you already have.`);
  process.exit(2);
}
const home = process.env.AGENT_DESKTOP_HOME || join(base, 'state');
mkdirSync(home, { recursive: true });
const r = spawnSync(exe, process.argv.slice(2), { stdio: 'inherit', env: { ...process.env, AGENT_DESKTOP_HOME: home } });
if (r.error) { console.error('windows-ops: could not start agent-desktop: ' + r.error.message); process.exit(2); }
process.exit(r.status ?? 1);
