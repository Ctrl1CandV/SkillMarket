#!/usr/bin/env node
// Run the pinned local copy of Google's modern-web-guidance CLI with telemetry off.
//   node mwg.mjs search "<query>" --skill-version <v>
//   node mwg.mjs retrieve "<id>[,<id>...]"
//   node mwg.mjs list | legacy-scan <path> --json
// The package lives outside this repo (about 17 MB). Default location:
//   %LOCALAPPDATA%/modern-web-guidance/<version>/package   (Windows)
//   ~/.local/share/modern-web-guidance/<version>/package   (elsewhere)
// Override with MWG_HOME pointing at the extracted `package` folder.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const VERSION = '1.0.1';
const base = process.env.LOCALAPPDATA || join(homedir(), '.local', 'share');
const root = join(base, 'modern-web-guidance');
const pkg = process.env.MWG_HOME || join(root, VERSION, 'package');
const cli = join(pkg, 'skills', 'modern-web-guidance', 'modern-web.mjs');

if (!existsSync(cli)) {
  const dir = join(root, VERSION);
  console.error(`modern-web-guidance ${VERSION} is not installed at ${pkg}.
Ask the user before installing. Install (about 17 MB, no dependencies):
  mkdir -p "${dir}" && cd "${dir}" && curl -fsSL -o mwg.tgz https://registry.npmjs.org/modern-web-guidance/-/modern-web-guidance-${VERSION}.tgz && tar -xzf mwg.tgz
(Windows Git Bash may need: tar --force-local -xzf mwg.tgz)
Or set MWG_HOME to an extracted package folder.`);
  process.exit(2);
}

// Large retrieve output is written to a temp file; keep those files in one known folder.
const out = join(root, 'tmp');
mkdirSync(out, { recursive: true });
const env = { ...process.env, DISABLE_TELEMETRY: '1', TMP: out, TEMP: out, TMPDIR: out };
const r = spawnSync(process.execPath, [cli, ...process.argv.slice(2)], { stdio: 'inherit', env });
process.exit(r.status ?? 1);
