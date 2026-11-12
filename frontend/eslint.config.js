/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import lscDesignTokens from './eslint-plugins/lsc-design-tokens.js';

export default tseslint.config(
  { ignores: ['dist', 'src/api/generated/'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'jsx-a11y': jsxA11y,
      'lsc-design-tokens': lscDesignTokens,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // eslint-plugin-react-hooks v7 (the React Compiler ruleset) flags many
      // pre-existing, working patterns as errors. Keep them visible as warnings
      // instead of blocking the gate on a large mechanical refactor. NOTE:
      // react-hooks/rules-of-hooks deliberately stays an error -- it catches
      // real conditional-hook bugs (e.g. hooks declared after an early return).
      'react-hooks/refs': 'warn',
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-hooks/static-components': 'warn',
      'react-hooks/purity': 'warn',
      'react-hooks/globals': 'warn',
      // ~47 pre-existing `any` usages; surface as warnings pending cleanup.
      '@typescript-eslint/no-explicit-any': 'warn',
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_', destructuredArrayIgnorePattern: '^_' }],
      'no-restricted-imports': ['error', {
        patterns: [{
          group: ['@/services/auth-api', '@/services/events-api', '@/services/legal-api', '**/services/auth-api', '**/services/events-api', '**/services/legal-api'],
          message: 'Use the canonical API modules under @/api/* (services/* is deprecated compatibility only).',
        }],
      }],
      // Outside src/api/, no caller should call raw fetch(). fetchApi() in
      // @/api/fetchApi attaches the JWT Bearer token and parses JSON.
      // Bypassing it caused the 2026-05-15 library-visits 401 outage.
      //
      // The rule targets the call site (CallExpression where callee is the
      // identifier `fetch`), not the import of API_BASE, because legitimate
      // uses of the URL constant (WebSocket bases, useQuery wrappers, hard
      // navs, test mocks) don't bypass fetchApi and shouldn't be flagged.
      //
      // Edge cases that legitimately need raw fetch (binary downloads where
      // fetchApi's JSON contract doesn't fit; custom Content-Type like
      // SPARQL POST) get an inline eslint-disable-next-line.
      //
      // Warning, not error, because ~36 raw-fetch callsites still need
      // migration; bump to 'error' once the backlog is gone. The src/api/**
      // and __tests__/** overrides below carve out the legitimate homes.
      'no-restricted-syntax': ['error', {
        selector: "CallExpression[callee.type='Identifier'][callee.name='fetch']",
        message: 'Do not call fetch() directly outside src/api/. Use fetchApi() from @/api/fetchApi - it attaches the Authorization header. For binary downloads or custom Content-Type, add // eslint-disable-next-line no-restricted-syntax with a one-line reason.',
      }],
      // Design token enforcement — see tailwind.config.js
      'lsc-design-tokens/no-banned-tokens': 'error',
      'lsc-design-tokens/no-low-contrast-text': 'warn',
      'lsc-design-tokens/no-hardcoded-page-width': 'error',
      // A class whose token/shade doesn't exist emits NO CSS; when it's a
      // dark: override the light class beside it stays applied in dark mode.
      'lsc-design-tokens/no-unresolvable-color-token': 'error',
      // bg/text pair on one element whose computed contrast fails AA. Catches
      // the dark-mode pairs no-low-contrast-text skips by design.
      // WARN, not error: this surfaced ~120 PRE-EXISTING failures on first
      // run (verified real, e.g. monitoring-api.ts:364 puts dark:text-earth-100
      // on an undarkened bg-earth-100 -- identical colours, invisible in dark
      // mode). Erroring would block every commit until all 120 are triaged,
      // and many are design calls rather than typos. Raise to 'error' once
      // the backlog is cleared.
      'lsc-design-tokens/no-low-contrast-pair': 'warn',
      // Accessibility rules - enforce best practices
      'jsx-a11y/alt-text': 'warn',
      'jsx-a11y/anchor-has-content': 'warn',
      'jsx-a11y/anchor-is-valid': 'warn',
      'jsx-a11y/aria-props': 'warn',
      'jsx-a11y/aria-role': 'warn',
      'jsx-a11y/click-events-have-key-events': 'warn',
      'jsx-a11y/heading-has-content': 'warn',
      'jsx-a11y/label-has-associated-control': 'off', // Disabled: eslint-plugin-jsx-a11y@6.10.2 crashes with ESLint 9 (minimatch compat issue)
      'jsx-a11y/no-autofocus': 'off', // Allow autofocus for modals
      'jsx-a11y/no-noninteractive-element-interactions': 'off',
      // Guardrails against new page-level monoliths
      complexity: ['warn', 40],
      'max-lines': ['warn', { max: 1200, skipBlankLines: true, skipComments: true }],
    },
  },
  {
    files: ['src/pages/**/*.tsx'],
    rules: {
      complexity: ['warn', 40],
      'max-lines': ['warn', { max: 1200, skipBlankLines: true, skipComments: true }],
    },
  },
  {
    // The API layer (and the two adapter files that bridge to it) are the
    // legitimate homes for raw fetch(). fetchApi itself lives in src/api/.
    // Test mocks intercept fetch via MSW and need the bare global too.
    files: [
      'src/api/**/*.{ts,tsx}',
      'src/constants/api.ts',
      'src/lib/api-client.ts',
      'src/__tests__/**/*.{ts,tsx}',
      'src/**/__tests__/**/*.{ts,tsx}',
    ],
    rules: {
      'no-restricted-syntax': 'off',
    },
  }
);
