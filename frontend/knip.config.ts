import type { KnipConfig } from 'knip';

const config: KnipConfig = {
  entry: [
    'src/main.tsx',
    'src/App.tsx',
    'index.html',
    'vite.config.ts',
    'vitest.config.ts',
    'playwright.config.ts',
    'playwright.ci.config.ts',
    'lighthouserc.js',
    'lighthouserc.mobile.cjs',
    'linkinator.config.json',
    'postcss.config.js',
    'tailwind.config.js',
    'eslint.config.js',
    'scripts/**/*.{js,mjs,cjs,ts}',
    'eslint-plugins/**/*.{js,mjs,cjs,ts}',
    'src/**/*.stories.{ts,tsx}',
    'src/**/*.test.{ts,tsx}',
    'src/**/__tests__/**/*.{ts,tsx}',
    'e2e/**/*.{ts,tsx}',
  ],
  project: ['src/**/*.{ts,tsx}'],
  ignore: [
    'src/api/generated/**',
    'dist/**',
    'public/**',
    'playwright-report/**',
    'node_modules/**',
  ],
  ignoreDependencies: [
    // Storybook + tooling pulled in dynamically
    'storybook',
    '@storybook/*',
  ],
  ignoreExportsUsedInFile: true,
  includeEntryExports: false,
};

export default config;
