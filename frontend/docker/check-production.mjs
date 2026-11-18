import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const root = 'dist/datapulse/browser';
function inspect(path) {
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const file = join(path, entry.name);
    if (entry.isDirectory()) inspect(file);
    else assert.ok(!file.endsWith('.map'), `Public source map: ${file}`);
  }
}
inspect(root);
const html = readFileSync(join(root, 'index.html'), 'utf8');
assert.match(html, /http-equiv="Content-Security-Policy"/);
assert.match(html, /script-src 'self';/);
assert.ok(!html.includes('unsafe-eval'));
assert.ok(!/\son[a-z]+=/i.test(html));
console.log('Production artifact: CSP present, no source maps or inline handlers.');
