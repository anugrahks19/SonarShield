import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { parseEnv } from 'node:util';
const env = { ...process.env };
for (const file of ['.env', '.env.local', '.env.production', '.env.production.local', '.env.gateway.local']) if (existsSync(file)) Object.assign(env, parseEnv(readFileSync(file, 'utf8')));
const secrets = Object.entries(env).filter(([key,value]) => /(?:TOKEN|SECRET|PASSWORD|PRIVATE_KEY)/i.test(key) && typeof value==='string' && value.length>=12).map(([,value])=>value);
function files(directory) { return readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?files(join(directory,entry.name)):[join(directory,entry.name)]); }
for (const file of files('dist')) {
  if (!/\.(js|css|html|json)$/.test(file)) continue;
  const contents=readFileSync(file,'utf8');
  if (/(?:hf_[A-Za-z0-9]{10,}|sb_secret_[A-Za-z0-9_-]{10,})/.test(contents)||secrets.some(secret=>contents.includes(secret))) { process.stderr.write('Built asset credential scan failed. No credential value is printed.\n');process.exit(1); }
}
process.stdout.write('Built assets scanned: no known environment credentials or HF token patterns found.\n');
