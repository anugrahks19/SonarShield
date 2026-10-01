import http from 'node:http';
import handler from '../api/analyze.js';

http.createServer((req, res) => {
  if (req.url !== '/api/analyze') { res.writeHead(404); res.end(); return; }
  // The Vite browser origin is fixed for local development; no credential is returned.
  process.env.APP_ORIGIN ||= 'http://localhost:5173';
  void handler(req, res);
}).listen(8787, '127.0.0.1', () => process.stdout.write('Local inference gateway: http://127.0.0.1:8787\n'));
