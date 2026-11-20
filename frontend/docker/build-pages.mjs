import { spawnSync } from 'node:child_process';
import { readFileSync, rmSync, writeFileSync } from 'node:fs';

const apiUrl = process.env.API_URL;
if (!apiUrl || new URL(apiUrl).protocol !== 'https:')
  throw new Error('Cloudflare Pages requires API_URL=https://YOUR-BACKEND.onrender.com/api/');

function run(command, args) {
  const result = spawnSync(command, args, { stdio: 'inherit', shell: false });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

run(process.execPath, ['docker/configure-build.mjs', apiUrl, 'production']);
run(process.execPath, ['node_modules/@angular/cli/bin/ng.js', 'build', '--configuration', 'production']);
run(process.execPath, ['docker/finalize-index.mjs']);
run(process.execPath, ['docker/check-production.mjs']);
// Pages provides native SPA fallback without a top-level 404.html. Its redirect
// validator rejects the catch-all /index.html rewrite as an infinite loop.
rmSync('dist/datapulse/browser/_redirects', { force: true });
const csp = JSON.parse(readFileSync('docker/csp-policy.json', 'utf8'));
writeFileSync('dist/datapulse/browser/_headers', [
  '/*',
  `  Content-Security-Policy: ${csp}`,
  '  X-Content-Type-Options: nosniff',
  '  X-Frame-Options: DENY',
  '  Referrer-Policy: strict-origin-when-cross-origin',
  '  Permissions-Policy: camera=(), microphone=(), geolocation=()',
  '  Cross-Origin-Opener-Policy: same-origin',
  '  Cross-Origin-Resource-Policy: same-origin',
  '',
].join('\n'));
