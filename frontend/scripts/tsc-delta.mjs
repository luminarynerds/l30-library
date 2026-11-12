#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * tsc-delta.mjs — compare current `tsc --noEmit` output to a baseline.
 * Exits 1 if NEW error signatures appear vs baseline. Exits 0 if existing
 * errors persist or were fixed (fixes don't auto-shrink the baseline;
 * run --rebaseline deliberately after intentional cleanup, same convention
 * as knip-delta.mjs).
 *
 * Signature = "file::code" (line/col deliberately excluded — unrelated
 * edits shift line numbers and would otherwise false-positive as "new").
 *
 * Modes:
 *   --warn        Report new signatures without failing; checker failures remain fatal.
 *   --rebaseline  Write current signatures to .tsc-baseline.json and exit 0.
 */
import { spawnSync } from 'node:child_process'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendDir = resolve(__dirname, '..')
const baselinePath = resolve(frontendDir, '.tsc-baseline.json')

const args = new Set(process.argv.slice(2))
const WARN = args.has('--warn')
const REBASE = args.has('--rebaseline')

const ERROR_RE = /^(.+?)\((\d+),(\d+)\): error (TS\d+):/

export function runTsc(run = spawnSync) {
  const result = run(process.execPath, [
    resolve(frontendDir, 'node_modules/typescript/bin/tsc'),
    '--noEmit', '-p', 'tsconfig.json', '--pretty', 'false',
  ], { cwd: frontendDir, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
  if (result.stderr) process.stderr.write(result.stderr)
  if (result.error || result.signal || ![0, 1, 2].includes(result.status)) {
    throw new Error(`TypeScript checker failed: ${result.error || result.signal || result.status}; ${result.stderr || ''}`)
  }
  const output = result.stdout || ''
  const malformed = output.split('\n').some(line => /error TS\d+:/.test(line) && !ERROR_RE.test(line))
  if (malformed || (result.status !== 0 && parseSignatures(output).size === 0)) {
    throw new Error(`Unrecognized TypeScript failure output: ${output}`)
  }
  return output
}

function parseSignatures(output) {
  const sigs = new Set()
  for (const line of output.split('\n')) {
    const m = ERROR_RE.exec(line)
    if (m) sigs.add(`${m[1]}::${m[4]}`)
  }
  return sigs
}

export function main(check = runTsc, { warn = WARN, rebaseline = REBASE, baselineFile = baselinePath } = {}) {
  let current
  try {
    current = parseSignatures(check())
  } catch (error) {
    console.error(`tsc-delta: ${error.message}`)
    return 2
  }

  if (rebaseline) {
    writeFileSync(baselineFile, JSON.stringify([...current].sort(), null, 2) + '\n')
    console.log(`tsc-delta: baseline written to ${baselineFile} (${current.size} known errors)`)
    return 0
  }

  if (!existsSync(baselineFile)) {
    console.error(`tsc-delta: baseline missing at ${baselineFile}; run with --rebaseline first.`)
    return 2
  }

  const baseline = new Set(JSON.parse(readFileSync(baselineFile, 'utf8')))
  const added = [...current].filter((s) => !baseline.has(s))

  if (added.length > 0) {
    console.error(`tsc-delta: ${added.length} NEW type error(s) not in baseline:`)
    for (const s of added) console.error(`  ${s}`)
    if (!warn) return 1
  }
  console.log(`tsc-delta: ${current.size} total signatures, ${added.length} new vs baseline` + (added.length ? ` (warn-only, ${added.length} ignored)` : ''))
  return 0
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main())
}
