// ==============================================================
// Sample Microservice for Local AI Agent Deployment Lab
// ==============================================================
import http from 'http';
import os from 'os';

const PORT = parseInt(process.env.PORT || '5050', 10);
const startTime = Date.now();

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (url.pathname === '/' || url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'UP',
      healthy: true,
      service: 'payment-mock-service',
      version: '1.0.0',
      uptime_seconds: Math.floor((Date.now() - startTime) / 1000),
      platform: os.platform(),
      hostname: os.hostname(),
      memory_rss_mb: Math.round(process.memoryUsage().rss / 1024 / 1024)
    }, null, 2));
    return;
  }

  if (url.pathname === '/metrics') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end(`
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total 42
# HELP app_uptime_seconds Application uptime
# TYPE app_uptime_seconds gauge
app_uptime_seconds ${Math.floor((Date.now() - startTime) / 1000)}
    `.trim());
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not Found' }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[SAMPLE APP] Server successfully running on http://127.0.0.1:${PORT}`);
});
