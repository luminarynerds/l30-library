/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest" />
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    globals: true,
    // happy-dom is 2-3x faster than jsdom for most React tests
    environment: "happy-dom",
    setupFiles: ["./src/__tests__/setup.ts"],
    include: [
      "src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}",
      "scripts/**/*.{test,spec}.{js,mjs,cjs,ts,mts}",
    ],
    // Performance optimizations
    pool: "threads",
    threads: {
      // Balance between isolation and performance
      singleThread: false,
      isolate: false,
    },
    // Reduce module resolution overhead
    deps: {
      optimizer: {
        web: {
          include: ["vitest-canvas-mock"],
        },
      },
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/",
        "src/__tests__/",
        "**/*.d.ts",
      ],
      thresholds: {
        statements: 43,
        // branches/functions/lines deliberately not gated yet — only the
        // metric the maintainer's baseline (43.24%) was measured against. Add the
        // others once each has its own known-green baseline. This number
        // only ever goes up — bump it by hand when a PR provably raises
        // real coverage, never automatically, never down.
        autoUpdate: false,
      },
    },
  },
  cacheDir: "node_modules/.vitest",
})
