import { existsSync, readFileSync, writeFileSync } from 'node:fs';
const file = 'dist/datapulse/browser/index.html';
const source = readFileSync(file, 'utf8');
// Angular critical-CSS output uses an inline onload handler. A normal stylesheet
// link works with script-src self and does not require unsafe-inline scripts.
let html = source.replace(/<link\b[^>]*>/gi, (link) => {
  if (!/\brel="stylesheet"/i.test(link)) return link;
  return link
    .replace(/\s+onload="this\.media='all'"/i, '')
    .replace(/\s+media="print"/i, ' media="all"');
});
if (/\son[a-z]+=/i.test(html))
  throw new Error('Unexpected inline event handler in generated HTML; review CSP.');
for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))
  if (match[1].trim()) throw new Error('Unexpected inline script in generated HTML; review CSP.');
// Meta is a fallback for static hosting. frame-ancestors is header-only.
const policy = existsSync('docker/csp-policy.json')
  ? JSON.parse(readFileSync('docker/csp-policy.json', 'utf8'))
  : "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; worker-src 'self' blob:";
const meta = `<meta http-equiv="Content-Security-Policy" content="${policy.replace(/;?\s*frame-ancestors[^;]*;?/g, ';').replaceAll('&', '&amp;').replaceAll('"', '&quot;')}">`;
html = html.replace(/<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*>/gi, '');
html = html.replace(/<head>/i, `<head>${meta}`);
writeFileSync(file, html);
