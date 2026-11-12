/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Build Output: Pre-compressed Asset Twins
 *
 * Asserts that `npm run build` emits `.br` (brotli) and `.gz` (gzip) twins
 * for every compressible asset over the 1 KB threshold. The twins are
 * required so nginx can serve them via `brotli_static` / `gzip_static`
 * without per-request runtime compression.
 *
 * This test reads from `dist/` and is skipped when `dist/` is not present
 * (e.g. unit-test runs before a build). To exercise it, run:
 *   npm run build && npx vitest run src/__tests__/build-output.test.ts
 */

import { describe, it, expect } from 'vitest';
import { existsSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const DIST_DIR = resolve(__dirname, '../../dist');
const COMPRESSIBLE_EXTS = new Set(['.js', '.css', '.svg', '.json', '.html', '.ico', '.txt', '.xml']);
const THRESHOLD_BYTES = 1024;

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(full));
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
  return out;
}

function isCompressibleOriginal(path: string): boolean {
  if (path.endsWith('.br') || path.endsWith('.gz')) return false;
  const dot = path.lastIndexOf('.');
  if (dot === -1) return false;
  const ext = path.slice(dot).toLowerCase();
  return COMPRESSIBLE_EXTS.has(ext);
}

const distExists = existsSync(DIST_DIR);

describe.skipIf(!distExists)('build output: pre-compressed twins', () => {
  const allFiles = distExists ? walk(DIST_DIR) : [];
  const originals = allFiles.filter(isCompressibleOriginal);
  const overThreshold = originals.filter((p) => statSync(p).size > THRESHOLD_BYTES);

  it('produces at least one compressible original over threshold', () => {
    // Sanity: if this fails, the dist tree is empty or thresholds are wrong.
    expect(overThreshold.length).toBeGreaterThan(0);
  });

  it('emits a .br twin for every compressible original over 1 KB', () => {
    const missing = overThreshold.filter((p) => !existsSync(`${p}.br`));
    expect(missing, `missing .br twins: ${missing.slice(0, 5).join(', ')}`).toEqual([]);
  });

  it('emits a .gz twin for every compressible original over 1 KB', () => {
    const missing = overThreshold.filter((p) => !existsSync(`${p}.gz`));
    expect(missing, `missing .gz twins: ${missing.slice(0, 5).join(', ')}`).toEqual([]);
  });

  it('each .br twin is smaller than its original', () => {
    const offenders: string[] = [];
    for (const p of overThreshold) {
      const brPath = `${p}.br`;
      if (!existsSync(brPath)) continue;
      const original = statSync(p).size;
      const br = statSync(brPath).size;
      if (br >= original) offenders.push(`${p} (orig=${original}, br=${br})`);
    }
    expect(offenders, `non-shrinking .br twins: ${offenders.slice(0, 3).join('; ')}`).toEqual([]);
  });

  it('each .gz twin is smaller than its original', () => {
    const offenders: string[] = [];
    for (const p of overThreshold) {
      const gzPath = `${p}.gz`;
      if (!existsSync(gzPath)) continue;
      const original = statSync(p).size;
      const gz = statSync(gzPath).size;
      if (gz >= original) offenders.push(`${p} (orig=${original}, gz=${gz})`);
    }
    expect(offenders, `non-shrinking .gz twins: ${offenders.slice(0, 3).join('; ')}`).toEqual([]);
  });
});
