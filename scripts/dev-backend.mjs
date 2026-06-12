// Dev launcher for the backend: starts a Cloudflare quick tunnel, writes its
// public URL into backend/.env as APP_URL (so tracking pixels are reachable
// from the internet), then starts uvicorn. If the tunnel can't start, the
// backend still runs — only open/click tracking is unavailable.
import { spawn } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const backendDir = join(root, 'backend');
const envPath = join(backendDir, '.env');
const CLOUDFLARED = 'C:\\Program Files (x86)\\cloudflared\\cloudflared.exe';

let tunnelProc = null;

function updateEnvAppUrl(url) {
  const env = readFileSync(envPath, 'utf8');
  if (!/^APP_URL=.*$/m.test(env)) {
    writeFileSync(envPath, env + `\nAPP_URL=${url}\n`);
  } else {
    writeFileSync(envPath, env.replace(/^APP_URL=.*$/m, `APP_URL=${url}`));
  }
  console.log(`[tunnel] APP_URL set to ${url}`);
}

function startTunnel() {
  if (!existsSync(CLOUDFLARED)) {
    console.warn('[tunnel] cloudflared not installed - open/click tracking will not work this session');
    return Promise.resolve(null);
  }
  tunnelProc = spawn(CLOUDFLARED, ['tunnel', '--url', 'http://localhost:3001'], {
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      console.warn('[tunnel] timed out waiting for tunnel URL - continuing without tracking');
      resolve(null);
    }, 30000);
    const onData = (chunk) => {
      const match = String(chunk).match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
      if (match) {
        clearTimeout(timeout);
        resolve(match[0]);
      }
    };
    tunnelProc.stdout.on('data', onData);
    tunnelProc.stderr.on('data', onData);
    tunnelProc.on('exit', () => {
      clearTimeout(timeout);
      resolve(null);
    });
  });
}

const url = await startTunnel();
if (url) updateEnvAppUrl(url);

const python = join(backendDir, '.venv', 'Scripts', 'python.exe');
const server = spawn(python, ['-m', 'uvicorn', 'main:app', '--port', '3001', '--reload'], {
  cwd: backendDir,
  stdio: 'inherit',
});

const shutdown = () => {
  try { tunnelProc?.kill(); } catch { /* already dead */ }
  try { server.kill(); } catch { /* already dead */ }
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
process.on('exit', shutdown);
server.on('exit', (code) => {
  try { tunnelProc?.kill(); } catch { /* already dead */ }
  process.exit(code ?? 0);
});
