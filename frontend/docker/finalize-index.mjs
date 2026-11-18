import { readFileSync, writeFileSync } from 'node:fs';
const file = 'dist/datapulse/browser/index.html';
const source = readFileSync(file, 'utf8');
// Angular critical-CSS output uses an inline onload handler. A normal stylesheet
// link works with script-src self and does not require unsafe-inline scripts.
const html = source.replace(/<link\b[^>]*>/gi, (link) => {
  if (!/\brel="stylesheet"/i.test(link)) return link;
  return link
    .replace(/\s+onload="this\.media='all'"/i, '')
    .replace(/\s+media="print"/i, ' media="all"');
});
if (/\son[a-z]+=/i.test(html))
  throw new Error('Unexpected inline event handler in generated HTML; review CSP.');
for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))
  if (match[1].trim()) throw new Error('Unexpected inline script in generated HTML; review CSP.');
writeFileSync(file, html);
