const api = process.env.VITE_API_BASE_URL?.trim();
const errors = [];

if (!api) {
  errors.push('VITE_API_BASE_URL must name the deployed F8 API origin.');
} else {
  try {
    const url = new URL(api);
    if (url.protocol !== 'https:') errors.push('VITE_API_BASE_URL must use HTTPS for a release build.');
    if (url.username || url.password) errors.push('VITE_API_BASE_URL must not contain credentials.');
    if (url.pathname !== '/' || url.search || url.hash) errors.push('VITE_API_BASE_URL must be an origin without a path, query, or fragment.');
    if (['localhost', '127.0.0.1', '0.0.0.0'].includes(url.hostname)) errors.push('VITE_API_BASE_URL must not point to a local development server.');
  } catch { errors.push('VITE_API_BASE_URL is not a valid URL.'); }
}

if (process.env.VITE_DEMO_MODE === 'true') errors.push('VITE_DEMO_MODE must be false for a release build.');
if (process.env.VITE_USE_MOCK_DATA === 'true') errors.push('VITE_USE_MOCK_DATA must be false for a release build.');

if (errors.length) {
  for (const error of errors) process.stderr.write(`Release configuration: ${error}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write('Release environment configuration verified.\n');
}
