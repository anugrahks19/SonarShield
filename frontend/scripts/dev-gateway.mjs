import http from 'node:http';
import handler from '../api/analyze.js';
import records from '../api/records.js';
import maintenance from '../api/maintenance.js';

http.createServer((req, res) => {
  const selected = req.url === '/api/analyze' ? handler : req.url === '/api/records' ? records : req.url === '/api/maintenance' ? maintenance : null;
  if (!selected) { res.writeHead(404); res.end(); return; }
  // The Vite browser origin is fixed for local development; no credential is returned.
  process.env.APP_ORIGIN ||= 'http://localhost:5173';
  void selected(req, res);
}).listen(8787, '127.0.0.1', () => process.stdout.write('Local inference gateway: http://127.0.0.1:8787\n'));
