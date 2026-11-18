import assert from 'node:assert/strict';
const base = process.argv[2] ?? 'http://127.0.0.1:18080';
const security = [
  'content-security-policy',
  'x-content-type-options',
  'x-frame-options',
  'referrer-policy',
  'permissions-policy',
];
async function request(path, options = {}) {
  const response = await fetch(base + path, options);
  for (const header of security)
    assert.ok(response.headers.get(header), `${path}: missing ${header}`);
  return response;
}
const home = await request('/');
assert.equal(home.status, 200);
const html = await home.text();
assert.match(html, /<app-root/);
assert.doesNotMatch(html, /\son[a-z]+=/i, 'Generated HTML must work with script-src self');
assert.match(home.headers.get('cache-control'), /no-cache, no-store, must-revalidate/);
const deep = await request('/portafolios/123');
assert.equal(deep.status, 200);
assert.equal(await deep.text(), html);
assert.match(deep.headers.get('cache-control'), /no-store/);
const asset = html.match(/src="([^"]*main-[^"]+\.js)"/);
assert.ok(asset, 'Hashed Angular entry point');
const js = await request('/' + asset[1], { headers: { 'Accept-Encoding': 'gzip' } });
assert.equal(js.status, 200);
assert.match(js.headers.get('cache-control'), /max-age=31536000, immutable/);
assert.equal(js.headers.get('content-encoding'), 'gzip');
assert.match(js.headers.get('content-type'), /javascript/);
await js.arrayBuffer();
const geo = await request('/assets/geojson/latam.geojson');
assert.equal(geo.status, 200);
assert.match(geo.headers.get('cache-control'), /max-age=604800/);
assert.equal((await geo.json()).features.length, 10);
for (const icon of ['favicon.ico', 'favicon.svg']) {
  const r = await request('/' + icon);
  assert.equal(r.status, 200);
  assert.match(r.headers.get('cache-control'), /max-age=86400/);
}
const missing = await request('/missing-chunk.js');
assert.equal(missing.status, 404);
assert.equal(missing.headers.get('cache-control'), 'no-store');
assert.equal((await request('/api/health/')).status, 200);
const echo = await request('/api/echo/?query=kept', {
  method: 'PUT',
  headers: {
    Authorization: 'Bearer fixture-token',
    'If-Match': '"6"',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ version: 6, monto_inversion_usd: '1234.56' }),
});
assert.equal(echo.headers.get('etag'), '"7"');
assert.equal(echo.headers.get('cache-control'), 'no-store');
const data = await echo.json();
assert.equal(data.authorization, 'Bearer fixture-token');
assert.equal(data.ifMatch, '"6"');
assert.equal(data.uri, '/api/echo/?query=kept');
assert.equal(JSON.parse(data.body).monto_inversion_usd, '1234.56');
const deletion = await request('/api/echo/', { method: 'DELETE', headers: { 'If-Match': '"7"' } });
const deleted = await deletion.json();
assert.equal(deleted.method, 'DELETE');
assert.equal(deleted.body, '');
assert.equal(deleted.ifMatch, '"7"');
const api404 = await request('/api/not-found/');
assert.equal(api404.status, 404);
assert.ok((await api404.json()).error);
const pdf = await request('/api/export/pdf/');
assert.match(pdf.headers.get('content-disposition'), /attachment/);
assert.match(await pdf.text(), /^%PDF-/);
const csp = home.headers.get('content-security-policy');
assert.match(csp, /script-src 'self';/);
assert.doesNotMatch(csp, /unsafe-eval/);
console.log(
  'PASS: SPA routes, cache, gzip, security headers, missing assets, API proxy, JWT/If-Match, decimal body, DELETE, PDF.',
);
