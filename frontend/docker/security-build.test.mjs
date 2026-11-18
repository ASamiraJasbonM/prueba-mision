import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const scripts = dirname(fileURLToPath(import.meta.url));
function isolated(check) {
  const root = mkdtempSync(join(tmpdir(), 'datapulse-security-'));
  try {
    mkdirSync(join(root, 'src/environments'), { recursive: true });
    mkdirSync(join(root, 'docker'));
    mkdirSync(join(root, 'dist/datapulse/browser'), { recursive: true });
    writeFileSync(join(root, 'dist/datapulse/browser/index.html'), '<html><head></head><body><app-root></app-root></body></html>');
    check(root);
  } finally {
    assert.equal(dirname(resolve(root)), resolve(tmpdir()));
    assert.ok(basename(root).startsWith('datapulse-security-'));
    rmSync(root, { recursive: true, force: true });
  }
}
const run = (root, script, ...args) => spawnSync(process.execPath, [join(scripts, script), ...args], { cwd: root, encoding: 'utf8' });
test('meta fallback and HTTP policy agree on the exact configured API origin', () => isolated((root) => {
  assert.equal(run(root, 'configure-build.mjs', 'https://api.example.test/api/').status, 0);
  assert.equal(run(root, 'finalize-index.mjs').status, 0);
  const html = readFileSync(join(root, 'dist/datapulse/browser/index.html'), 'utf8');
  assert.match(html, /http-equiv="Content-Security-Policy"/);
  assert.match(html, /connect-src 'self' https:\/\/api.example.test;/);
  assert.ok(!html.includes('frame-ancestors'));
  assert.ok(!html.includes('unsafe-eval'));
  const headers = readFileSync(join(root, 'docker/security-headers.conf'), 'utf8');
  assert.match(headers, /frame-ancestors 'none'/);
  assert.match(headers, /Cross-Origin-Resource-Policy "same-origin"/);
  assert.equal(run(root, 'check-production.mjs').status, 0);
}));
test('production gate rejects an accidentally published source map', () => isolated((root) => {
  run(root, 'finalize-index.mjs');
  writeFileSync(join(root, 'dist/datapulse/browser/main.js.map'), '{}');
  assert.notEqual(run(root, 'check-production.mjs').status, 0);
}));
test('source guard rejects a new unsafe DOM sink or verbose log in application code', () => isolated((root) => {
  writeFileSync(join(root, 'src/view.ts'), 'node.textContent = value;');
  assert.equal(run(root, 'check-source-security.mjs').status, 0);
  for (const source of ['node.innerHTML = value;', 'console.log(response);', 'new Function(input);']) {
    writeFileSync(join(root, 'src/view.ts'), source);
    assert.notEqual(run(root, 'check-source-security.mjs').status, 0);
  }
}));
