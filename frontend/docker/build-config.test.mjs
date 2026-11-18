import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const scripts = dirname(fileURLToPath(import.meta.url));
function isolated(check) {
  const root = mkdtempSync(join(tmpdir(), 'datapulse-config-'));
  try {
    mkdirSync(join(root, 'src/environments'), { recursive: true });
    mkdirSync(join(root, 'docker'));
    mkdirSync(join(root, 'dist/datapulse/browser'), { recursive: true });
    check(root);
  } finally {
    assert.equal(dirname(resolve(root)), resolve(tmpdir()));
    assert.ok(basename(root).startsWith('datapulse-config-'));
    rmSync(root, { recursive: true, force: true });
  }
}
function run(root, script, ...args) {
  return spawnSync(process.execPath, [join(scripts, script), ...args], {
    cwd: root,
    encoding: 'utf8',
  });
}
test('API URL is compiled and only its origin is allowed by CSP', () =>
  isolated((root) => {
    assert.equal(
      run(root, 'configure-build.mjs', 'https://api.example.test/gateway/api/', 'production')
        .status,
      0,
    );
    const source = readFileSync(join(root, 'src/environments/environment.prod.ts'), 'utf8');
    const env = JSON.parse(source.match(/= (.+);/)[1]);
    assert.equal(env.apiUrl, 'https://api.example.test/gateway/api/');
    const csp = readFileSync(join(root, 'docker/security-headers.conf'), 'utf8');
    assert.match(csp, /connect-src 'self' https:\/\/api\.example\.test;/);
    assert.match(csp, /script-src 'self';/);
  }));
test('URL credentials, queries, script schemes and unknown relative proxies are rejected', () =>
  isolated((root) => {
    for (const url of [
      'javascript:alert(1)',
      'https://user:password@example.test/api/',
      'https://example.test/api/?token=fixture',
      'https://example.test/api/#fragment',
      '//example.test/api/',
      '/other/',
    ])
      assert.notEqual(run(root, 'configure-build.mjs', url, 'production').status, 0, url);
    assert.notEqual(run(root, 'configure-build.mjs', '/api/', 'development').status, 0);
  }));
test('same-origin API is retained without a wildcard connect source', () =>
  isolated((root) => {
    assert.equal(run(root, 'configure-build.mjs', '/api/', 'production').status, 0);
    assert.match(
      readFileSync(join(root, 'docker/security-headers.conf'), 'utf8'),
      /connect-src 'self';/,
    );
  }));
test('generated stylesheet loads without inline event handlers', () =>
  isolated((root) => {
    const file = join(root, 'dist/datapulse/browser/index.html');
    writeFileSync(
      file,
      `<app-root></app-root><link rel="stylesheet" href="styles-ABCDEFGH.css" media="print" onload="this.media='all'"><script src="main-ABCDEFGH.js" type="module"></script>`,
    );
    assert.equal(run(root, 'finalize-index.mjs').status, 0);
    const html = readFileSync(file, 'utf8');
    assert.match(html, /media="all"/);
    assert.doesNotMatch(html, /onload=/);
  }));
test('unexpected generated scripts and handlers fail the build', () =>
  isolated((root) => {
    const file = join(root, 'dist/datapulse/browser/index.html');
    for (const html of ['<button onclick="alert(1)"></button>', '<script>alert(1)</script>']) {
      writeFileSync(file, html);
      assert.notEqual(run(root, 'finalize-index.mjs').status, 0);
    }
  }));
