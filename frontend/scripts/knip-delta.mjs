#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * knip-delta.mjs — compare current knip JSON output to baseline.
 * Exits 1 if NEW orphans (files/exports/types/deps) appear vs baseline.
 * Exits 0 if existing orphans persist or were removed.
 *
 * Modes:
 *   --warn      Print delta, always exit 0 (used in pre-commit rollout phase).
 *   --rebaseline Write current output to .knip-baseline.json and exit 0.
 */
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(__dirname, '..');
const baselinePath = resolve(frontendDir, '.knip-baseline.json');

const args = new Set(process.argv.slice(2));
const WARN = args.has('--warn');
const REBASE = args.has('--rebaseline');

function runKnip() {
  try {
    const out = execSync('npx knip --reporter json', {
      cwd: frontendDir,
      encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'inherit'],
    });
    return out;
  } catch (e) {
    // knip exits non-zero when issues exist; that's fine, we want stdout.
    if (e.stdout) return e.stdout.toString();
    throw e;
  }
}

function flatten(report) {
  const sets = {
    files: new Set(),
    exports: new Set(),
    types: new Set(),
    dependencies: new Set(),
    devDependencies: new Set(),
  };
  for (const row of report.issues || []) {
    for (const f of row.files || []) sets.files.add(f.name || row.file);
    for (const ex of row.exports || []) sets.exports.add(`${row.file}::${ex.name || ex.symbol || ex}`);
    for (const t of row.types || []) sets.types.add(`${row.file}::${t.name || t.symbol || t}`);
    for (const d of row.dependencies || []) sets.dependencies.add(d.name || d);
    for (const d of row.devDependencies || []) sets.devDependencies.add(d.name || d);
  }
  return sets;
}

function diff(curr, base) {
  const added = {};
  let total = 0;
  for (const k of Object.keys(curr)) {
    added[k] = [...curr[k]].filter((x) => !base[k].has(x));
    total += added[k].length;
  }
  return { added, total };
}

const raw = runKnip();
const current = JSON.parse(raw);

if (REBASE) {
  writeFileSync(baselinePath, JSON.stringify(current, null, 2) + '\n');
  console.log(`knip: baseline written to ${baselinePath}`);
  process.exit(0);
}

if (!existsSync(baselinePath)) {
  console.error(`knip-delta: baseline missing at ${baselinePath}; run with --rebaseline first.`);
  process.exit(2);
}

const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
const currSets = flatten(current);
const baseSets = flatten(baseline);
const { added, total } = diff(currSets, baseSets);

if (total === 0) {
  console.log('knip-delta: no new orphans vs baseline.');
  process.exit(0);
}

console.error(`knip-delta: ${total} NEW orphan(s) introduced vs baseline:`);
for (const [k, list] of Object.entries(added)) {
  if (list.length === 0) continue;
  console.error(`  ${k} (+${list.length}):`);
  for (const item of list.slice(0, 25)) console.error(`    ${item}`);
  if (list.length > 25) console.error(`    ... and ${list.length - 25} more`);
}
console.error('');
console.error('Either remove the new orphan(s), or — if intentionally added — run:');
console.error('  npm run knip:rebaseline');

if (WARN) {
  console.error('(warn mode: not failing)');
  process.exit(0);
}
process.exit(1);
