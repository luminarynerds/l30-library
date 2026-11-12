#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Catch undefined-name usage that escapes the noisy `tsc --noEmit` output.
 *
 * Why this exists
 * ---------------
 * 2026-05-20: `BannedBooksPage.tsx` shipped to prod calling
 * `nextBannedBooksWeek()` without importing it. Vite/esbuild emitted the
 * bare-global reference; the browser threw `ReferenceError` at render and
 * the error boundary swallowed it. The page was broken for three days.
 *
 * `tsc --noEmit -p .` actually flags this (TS2552: "Cannot find name X.
 * Did you mean Y?"; TS2304: "Cannot find name X."). The reason the bug
 * shipped is that `npm run typecheck` already exits non-zero on a handful
 * of unrelated pre-existing errors, so humans tune it out and a new
 * TS2552 lands as line N of N+3 noise.
 *
 * This script runs tsc and filters output to TS2304/TS2552 only. A clean
 * exit means "no undefined-name usage." Anything else is a hard fail.
 *
 * Future-proofing: if a legitimate TS2304/TS2552 ever lands intentionally
 * (e.g. ambient global pending a .d.ts), add it to ALLOWED_PATTERNS below.
 */
import { spawnSync } from 'node:child_process'

// Lines we recognise as "use of an undefined name."
const UNDEFINED_NAME_CODES = /\berror TS(2304|2552):/

// Escape hatch for known-intentional cases. Keep this list short and
// reviewed; each entry should link to context.
const ALLOWED_PATTERNS = [
  // e.g. /src/some/ambient-shim\.ts/,
]

const res = spawnSync('npx', ['tsc', '--noEmit', '-p', '.'], {
  encoding: 'utf8',
  maxBuffer: 64 * 1024 * 1024,
})

const lines = (res.stdout || '').split('\n')
const offenders = lines.filter(
  (l) => UNDEFINED_NAME_CODES.test(l) && !ALLOWED_PATTERNS.some((p) => p.test(l)),
)

if (offenders.length === 0) {
  console.log('check-undefined-imports: OK (no TS2304/TS2552 hits)')
  process.exit(0)
}

console.error('check-undefined-imports: undefined-name usage detected')
console.error('  TS2304/TS2552 means a name is referenced without being')
console.error('  imported, declared, or in scope. Add the missing import')
console.error('  or fix the typo. See script header for context.\n')
for (const l of offenders) console.error('  ' + l)
console.error(`\n${offenders.length} offender(s).`)
process.exit(1)
