import { defineConfig } from '@playwright/test';

const baseURL = 'http://127.0.0.1:18120';
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env['CI'],
  retries: 0,
  timeout: 45000,
  globalTimeout: 600000,
  expect: { timeout: 10000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1920, height: 1080 } } },
    { name: 'tablet', use: { browserName: 'chromium', viewport: { width: 768, height: 1024 } } },
  ],
  webServer: {
    command: 'node e2e/start-server.mjs',
    url: `${baseURL}/api/health/`,
    reuseExistingServer: false,
    timeout: 90000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
