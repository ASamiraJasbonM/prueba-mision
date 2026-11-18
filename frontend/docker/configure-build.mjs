import { writeFileSync } from 'node:fs';

const [input = '/api/', configuration = 'production'] = process.argv.slice(2);
if (configuration !== 'production')
  throw new Error('The runtime image requires CONFIGURATION=production (AOT and hashed assets).');
let apiUrl = input;
let connectOrigin = '';
if (input === '/api/') {
  // The local reverse proxy owns /api/. Other deployments use an absolute URL.
} else {
  const url = new URL(input);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !url.pathname.endsWith('/')
  ) {
    throw new Error(
      'API_URL must be /api/ or an HTTP(S) URL ending in /, without credentials, query or fragment.',
    );
  }
  apiUrl = url.href;
  connectOrigin = ' ' + url.origin;
}
writeFileSync(
  'src/environments/environment.prod.ts',
  `// Generated only inside the Docker builder. API_URL is public configuration.\nexport const environment = ${JSON.stringify({ production: true, apiUrl })};\n`,
);
const csp = `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'${connectOrigin}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; worker-src 'self' blob:`;
writeFileSync('docker/csp-policy.json', JSON.stringify(csp));
writeFileSync(
  'docker/security-headers.conf',
  [
    `add_header Content-Security-Policy "${csp}" always;`,
    'add_header X-Content-Type-Options "nosniff" always;',
    'add_header X-Frame-Options "DENY" always;',
    'add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
    'add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;',
    'add_header Cross-Origin-Opener-Policy "same-origin" always;',
    'add_header Cross-Origin-Resource-Policy "same-origin" always;',
  ].join('\n') + '\n',
);
