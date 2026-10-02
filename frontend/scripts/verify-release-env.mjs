import { existsSync, readFileSync } from 'node:fs';
import { parseEnv } from 'node:util';
const releaseEnv = {};
for (const file of ['.env', '.env.local', '.env.production', '.env.production.local']) if (existsSync(file)) Object.assign(releaseEnv, parseEnv(readFileSync(file, 'utf8')));
Object.assign(releaseEnv, process.env);
const spaceId = releaseEnv.VITE_GRADIO_SPACE_ID?.trim() || 'mrintrovert19/sonar-shield-api';
const errors = [];
if (Object.keys(releaseEnv).some(key => /^VITE_.*(?:TOKEN|SECRET|PASSWORD|PRIVATE_KEY)/i.test(key) && releaseEnv[key])) errors.push('Credentials must remain server-only or be entered at runtime, never VITE_* variables.');

if (Object.entries(releaseEnv).some(([key,value]) => key.startsWith('VITE_') && /(?:hf_[A-Za-z0-9]{10,}|sb_secret_[A-Za-z0-9_-]{10,})/.test(value || ''))) errors.push('Public configuration contains a credential pattern.');

if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(spaceId)) errors.push('VITE_GRADIO_SPACE_ID must be a public owner/space identifier.');

if (releaseEnv.VITE_DEMO_MODE === 'true') errors.push('VITE_DEMO_MODE must be false for a release build.');
if (releaseEnv.VITE_USE_MOCK_DATA === 'true') errors.push('VITE_USE_MOCK_DATA must be false for a release build.');

if (errors.length) {
  for (const error of errors) process.stderr.write(`Release configuration: ${error}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write('Release environment configuration verified.\n');
}
