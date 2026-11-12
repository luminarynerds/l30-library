/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import { compression, defineAlgorithm } from 'vite-plugin-compression2'
import { constants as zlibConstants } from 'node:zlib'
import path from 'path'

// Pre-compress JS/CSS/HTML/SVG/JSON assets at build time so nginx can serve
// them via brotli_static / gzip_static with zero per-request CPU cost.
const COMPRESSION_EXCLUDE = /\.(br|gz|webp|avif|jpe?g|png|gif|mp3|mp4|webm|woff2?)$/i

// Public Cloudflare Turnstile site key for l30.org. Site keys are public (they
// ship in client HTML), so this is safe to commit -- the same value is already
// pinned as the Dockerfile.prod ARG default. It lives here so a `vite build` from
// ANY working tree or fresh clone inherits it: the real key file
// (frontend/.env.production) is gitignored and exists only in the main checkout,
// so a build run from a git worktree used to silently fall back to the
// `dev-bypass` token and break all auth (2026-06 incident). A real
// VITE_TURNSTILE_SITE_KEY (env var or .env.production) still overrides this.
const PUBLIC_TURNSTILE_SITE_KEY = '0x4AAAAAADScAwmbInNfrn7X'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, 'VITE_')
  const turnstileSiteKey =
    env.VITE_TURNSTILE_SITE_KEY || (mode === 'production' ? PUBLIC_TURNSTILE_SITE_KEY : '')

  // Fail closed: never emit a production bundle that falls back to the dev-bypass
  // token. With the committed default above this only trips if that default is
  // removed or explicitly blanked -- a loud build error beats a silent auth outage.
  if (mode === 'production' && !turnstileSiteKey) {
    throw new Error(
      '[vite] VITE_TURNSTILE_SITE_KEY resolved empty for a production build; refusing to emit a dev-bypass auth bundle.',
    )
  }

  return {
    // Drive the site key through the resolved value above so every tree gets a
    // correct prod key without relying on the gitignored .env.production.
    define: {
      'import.meta.env.VITE_TURNSTILE_SITE_KEY': JSON.stringify(turnstileSiteKey),
    },
    plugins: [
      react(),
      compression({
        algorithms: [
          defineAlgorithm('brotliCompress', {
            params: {
              [zlibConstants.BROTLI_PARAM_QUALITY]: 11,
            },
          }),
          defineAlgorithm('gzip', { level: 9 }),
        ],
        // Wider than the plugin default (adds txt/ico) so robots.txt etc. get
        // twins too. Binary types are filtered out by `exclude`.
        include: /\.(html|xml|css|json|js|mjs|svg|yaml|yml|toml|txt|ico)$/i,
        exclude: COMPRESSION_EXCLUDE,
        threshold: 1024,
        deleteOriginalAssets: false,
        skipIfLargerOrEqual: true,
      }),
      process.env.ANALYZE && visualizer({
        filename: 'bundle-stats.html',
        gzipSize: true,
        brotliSize: true,
      }),
    ].filter(Boolean),
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true,
          passes: 2,
          pure_funcs: ['console.log', 'console.debug', 'console.info'],
        },
        mangle: {
          safari10: true,
        },
      },
      cssCodeSplit: true,
      chunkSizeWarningLimit: 250,
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            // Only chunk node_modules into vendor chunks
            // Avoid manual chunking of application code to prevent circular dependencies

            // React core - cached long-term, rarely changes
            if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
              return 'vendor-react'
            }
            // Router - separate from React core for independent caching
            if (id.includes('node_modules/react-router-dom') || id.includes('node_modules/react-router/') || id.includes('node_modules/@remix-run/')) {
              return 'vendor-router'
            }
            // React Query - state management, updates more frequently
            if (id.includes('node_modules/@tanstack/react-query')) {
              return 'vendor-query'
            }
            // Virtual list - only loaded by catalog/list pages
            if (id.includes('node_modules/@tanstack/react-virtual')) {
              return 'vendor-virtual'
            }
            // D3 internals - heavy, only loaded transitively by recharts for analytics pages
            // Note: recharts itself is left to auto-chunking to avoid circular deps with React
            if (id.includes('node_modules/d3-')) {
              return 'vendor-d3'
            }
            // Lucide icons - tree-shaken but still significant
            if (id.includes('node_modules/lucide-react')) {
              return 'vendor-icons'
            }
            // Date utilities
            if (id.includes('node_modules/date-fns')) {
              return 'vendor-date'
            }
            // Small utility libs - clsx, dompurify
            if (id.includes('node_modules/clsx') || id.includes('node_modules/dompurify')) {
              return 'vendor-utils'
            }
            // Toast notifications
            if (id.includes('node_modules/react-hot-toast')) {
              return 'vendor-toast'
            }
            // Note: focus-trap-react left to auto-chunking to avoid circular deps with React
          },
          // Optimize chunk generation
          chunkFileNames: 'assets/[name]-[hash].js',
          entryFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash].[ext]',
        },
      },
    },
  }
})
