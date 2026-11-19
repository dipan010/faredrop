import { defineConfig, devices } from '@playwright/test';

// Tests run against the built site (dist/), served as Pages serves it.
export default defineConfig({
  testDir: 'tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: { baseURL: 'http://127.0.0.1:4321', ...devices['Desktop Chrome'] },
  webServer: {
    command: 'npm run build && node scripts/serve.mjs 4321',
    url: 'http://127.0.0.1:4321/dev/components/',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: { ASTRO_TELEMETRY_DISABLED: '1' },
  },
});
