// Infrastructure fixture for proxy checks only; never copied into the runtime image.
import { createServer } from 'node:http';
createServer(async (request, response) => {
  response.setHeader('Content-Type', 'application/json');
  if (request.url === '/api/health/') {
    response.end('{}');
    return;
  }
  if (request.url === '/api/export/pdf/') {
    response.setHeader('Content-Type', 'application/pdf');
    response.setHeader('Content-Disposition', 'attachment; filename="verification.pdf"');
    response.end('%PDF-1.4\nfixture\n%%EOF');
    return;
  }
  if (request.url?.startsWith('/api/echo/')) {
    const parts = [];
    for await (const part of request) parts.push(part);
    response.setHeader('ETag', '"7"');
    response.end(
      JSON.stringify({
        method: request.method,
        uri: request.url,
        authorization: request.headers.authorization ?? null,
        ifMatch: request.headers['if-match'] ?? null,
        body: Buffer.concat(parts).toString(),
      }),
    );
    return;
  }
  response.writeHead(404);
  response.end(
    JSON.stringify({
      error: { code: 'not_found', message: 'Fixture route not found.', details: {} },
    }),
  );
}).listen(8000, '0.0.0.0', () => console.log('Infrastructure API fixture listening on 8000'));
