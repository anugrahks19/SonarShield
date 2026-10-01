const spaceId = process.env.VITE_GRADIO_SPACE_ID?.trim() || 'mrintrovert19/sonar-shield-api';
const errors = [];
if (Object.keys(process.env).some(key => /^VITE_.*(?:HF_TOKEN|HUGGINGFACE_TOKEN)$/i.test(key) && process.env[key])) errors.push('Hugging Face tokens must be server-only HF_TOKEN variables, never VITE_* variables.');

if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(spaceId)) errors.push('VITE_GRADIO_SPACE_ID must be a public owner/space identifier.');

if (process.env.VITE_DEMO_MODE === 'true') errors.push('VITE_DEMO_MODE must be false for a release build.');
if (process.env.VITE_USE_MOCK_DATA === 'true') errors.push('VITE_USE_MOCK_DATA must be false for a release build.');

if (errors.length) {
  for (const error of errors) process.stderr.write(`Release configuration: ${error}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write('Release environment configuration verified.\n');
}
