// The component gallery in both page themes at the two canvas widths.
// Fails on any axe violation (WCAG 2.2 A/AA rules). Each panel inside the
// gallery is already pinned light or dark, so every run checks both; the
// page theme flips the chrome around them. Screenshots go to
// test-results/ for the side-by-side comparison with the canvas.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const WIDTHS = [390, 1440] as const;
const THEMES = ['light', 'dark'] as const;

for (const width of WIDTHS) {
  for (const theme of THEMES) {
    test(`gallery ${width}px ${theme}: no axe violations`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
      await page.addInitScript((t) => {
        try { localStorage.setItem('faredrop.theme', t); } catch {}
      }, theme);
      await page.goto('/dev/components/');
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      // Scroll through so every client:visible island hydrates, then wait.
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 20)); }
        window.scrollTo(0, 0);
      });
      await page.waitForFunction(() => document.querySelectorAll('astro-island[ssr]').length === 0, null, { timeout: 15_000 });

      // No horizontal page scroll at either width.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, 'horizontal overflow (px)').toBeLessThanOrEqual(0);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
        .exclude('.g-email') // emails are light-only HTML for mail clients (spec §3.3), checked below on their own
        .analyze();
      const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.help}\n  ` + v.nodes.slice(0, 5).map((n) => n.target.join(' ')).join('\n  '));
      await page.screenshot({ path: info.outputPath(`gallery-${width}-${theme}.png`), fullPage: true });
      expect(summary, 'axe violations').toEqual([]);
    });
  }
}

test('email shell: no axe violations (light only)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/dev/components/');
  const results = await new AxeBuilder({ page }).include('.g-email').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
});

test('theme switch cycles and persists', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/dev/components/');
  const btn = page.locator('.g-top .fd-theme-btn');
  await expect(btn).toHaveAttribute('aria-label', /same as device/);
  await btn.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await btn.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('.g-top .fd-theme-btn').click();
  await expect(page.locator('html')).not.toHaveAttribute('data-theme', /./);
});

test('booking sheet traps focus and closes on Escape', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto('/dev/components/#c21');
  const open = page.getByRole('button', { name: /Book for ₹25,218/ }).first();
  await open.scrollIntoViewIfNeeded();
  await expect(open.locator('xpath=ancestor::astro-island[1]')).not.toHaveAttribute('ssr', /.*/);
  await open.click();
  const dialog = page.getByRole('dialog', { name: 'Where to book' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused();
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate((d) => d.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(open).toBeFocused();
});
