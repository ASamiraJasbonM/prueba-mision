import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const path = 'src/environments/environment.prod.ts';
const original = readFileSync(path);
try {
  for (const args of [
    ['docker/configure-build.mjs', '/api/', 'production'],
    ['node_modules/@angular/cli/bin/ng.js', 'build', '--configuration', 'production'],
    ['docker/finalize-index.mjs'],
    ['docker/check-production.mjs'],
  ]) {
    const result = spawnSync(process.execPath, args, { stdio: 'inherit' });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error('E2E production build failed.');
  }
} finally {
  writeFileSync(path, original);
}
