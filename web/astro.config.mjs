// Static site for Cloudflare Pages. Preact is used for islands, and for
// shared components that islands also render (they ship no JS when an .astro
// page renders them without a client: directive).
import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

export default defineConfig({
  output: 'static',
  integrations: [preact()],
  vite: {
    // The sample fixture lives in ../docs/fixtures; let Vite read it.
    server: { fs: { allow: ['..'] } },
  },
});
