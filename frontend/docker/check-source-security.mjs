import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const forbidden = /\b(?:innerHTML|outerHTML|bypassSecurityTrust\w*)\b|\bdocument\.write\s*\(|\beval\s*\(|\bnew\s+Function\s*\(|\bconsole\.(?:log|debug|info|warn)\s*\(/;
function inspect(path) {
  for (const item of readdirSync(path, { withFileTypes: true })) {
    const file = join(path, item.name);
    if (item.isDirectory()) inspect(file);
    else if (/\.(?:ts|html)$/.test(file) && !file.endsWith('.spec.ts')) {
      assert.ok(!forbidden.test(readFileSync(file, 'utf8')), `Review forbidden DOM/logging primitive in ${file}`);
    }
  }
}
inspect(process.argv[2] ?? 'src');
console.log('Application source: no HTML bypass, executable strings or verbose console logging.');
