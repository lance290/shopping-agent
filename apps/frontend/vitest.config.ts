import { defineConfig } from 'vitest/config';

export default defineConfig({
  esbuild: {
    jsx: 'automatic',
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    exclude: ['**/node_modules/**', '**/e2e/**'],
    include: ['app/**/*.test.ts', 'app/**/*.test.tsx'],
  },
});
