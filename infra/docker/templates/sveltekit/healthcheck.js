// Health check endpoint for SvelteKit
// Required for compliance monitoring and orchestration
//
// NOTE: Your SvelteKit app must expose a /health endpoint.
// Add this to src/routes/health/+server.js:
//
// export async function GET() {
//   return new Response(JSON.stringify({ status: 'healthy' }), {
//     headers: { 'content-type': 'application/json' }
//   });
// }

const http = require('http');

const options = {
  host: 'localhost',
  port: process.env.PORT || 8080,
  path: '/health',
  timeout: 2000,
  method: 'GET'
};

const request = http.request(options, (res) => {
  console.log(`Health check status: ${res.statusCode}`);
  if (res.statusCode === 200) {
    process.exit(0);
  } else {
    process.exit(1);
  }
});

request.on('error', (err) => {
  console.log(`Health check failed: ${err.message}`);
  process.exit(1);
});

request.on('timeout', () => {
  console.log('Health check timeout');
  request.destroy();
  process.exit(1);
});

request.end();
