#!/usr/bin/env node
/**
 * Request-body drift checker: compares each @/lib/api-client fetchApi call's body
 * field set against the backend OpenAPI request schema.
 *
 * Usage:
 *   node scripts/check-api-request-bodies.mjs --openapi ../backend/openapi.json
 *   node scripts/check-api-request-bodies.mjs --openapi ../backend/openapi.json --update-baseline
 *
 * Baseline ratchet: known drift is recorded in api-request-body-drift-baseline.json.
 * The check exits 1 only on NEW drift (not in the baseline), so regressions fail CI
 * while the existing backlog is burned down. Run with --update-baseline to re-record.
 *
 * Note: ts-morph type resolution loads referenced files on demand; on a low-memory
 * box run with: node --max-old-space-size=4096 scripts/...
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { buildOracle, normalizePath } from './lib/openapi-oracle.mjs'

const API_BASE = '/api/v1'

/** Pure comparison — unit-tested without ts-morph or disk. */
export function compareCallsToOracle(calls, oracle) {
  const errors = []
  const warnings = []
  for (const c of calls) {
    if (c.status !== 'resolved') continue
    // c.path is wrapper-relative (e.g. /acquisition/...); the oracle keys on the full
    // spec path, so prefix API_BASE before matching. A call that hardcodes the full
    // /api/v1/... path would miss here and surface as endpoint-not-in-spec (warned, not dropped).
    const key = `${c.method} ${normalizePath(API_BASE + c.path)}`
    const entry = oracle.get(key)
    if (!entry) {
      warnings.push({ kind: 'endpoint-not-in-spec', ...c })
      continue
    }
    if (!entry.hasJsonBody) continue
    for (const f of c.bodyFields) {
      if (!entry.properties.has(f.name) && entry.strict) {
        errors.push({ kind: 'extra-field', field: f.name, schemaName: entry.schemaName, ...c })
      }
    }
    const sent = new Set(c.bodyFields.filter((f) => !f.optional).map((f) => f.name))
    for (const req of entry.required) {
      if (!sent.has(req)) warnings.push({ kind: 'missing-required', field: req, schemaName: entry.schemaName, ...c })
    }
  }
  return { errors, warnings }
}

/** Stable identity for an error — independent of file/line so it survives refactors. */
export function errorKey(e) {
  return `${e.kind}|${e.schemaName}|${e.field}|${e.method}|${e.path}`
}

/** Partition errors against a baseline of known keys. Pure. */
export function diffAgainstBaseline(errors, baselineKeys) {
  const baseline = new Set(baselineKeys)
  const seen = new Set()
  const newErrors = []
  const knownErrors = []
  for (const e of errors) {
    const k = errorKey(e)
    seen.add(k)
    if (baseline.has(k)) knownErrors.push(e)
    else newErrors.push(e)
  }
  const staleKeys = [...baseline].filter((k) => !seen.has(k))
  return { newErrors, knownErrors, staleKeys }
}

function loadOracle(argv) {
  const i = argv.indexOf('--openapi')
  if (i < 0) throw new Error('Missing --openapi <file>')
  const p = path.isAbsolute(argv[i + 1]) ? argv[i + 1] : path.resolve(process.cwd(), argv[i + 1])
  return buildOracle(JSON.parse(fs.readFileSync(p, 'utf8')))
}

async function main() {
  const argv = process.argv
  const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
  const baselinePath = path.join(frontendRoot, 'scripts', 'api-request-body-drift-baseline.json')
  const oracle = loadOracle(argv)

  const { Project } = await import('ts-morph')
  const { scanWrappers } = await import('./lib/wrapper-scan.mjs')
  const project = new Project({
    tsConfigFilePath: path.join(frontendRoot, 'tsconfig.json'),
    skipAddingFilesFromTsConfig: true,
  })
  // SCOPE: only the src/api/ wrapper layer is scanned. Mutating @/lib/api-client calls
  // made directly from components/pages (outside src/api/) are NOT checked — a known
  // blind spot, kept narrow to bound ts-morph memory on the VPS. Follow-up: widen the
  // glob to src/** (regenerating the baseline) if direct call sites proliferate.
  project.addSourceFilesAtPaths(path.join(frontendRoot, 'src/api/**/*.ts'))
  const calls = scanWrappers(project)
  const { errors, warnings } = compareCallsToOracle(calls, oracle)
  const counts = calls.reduce((a, c) => ((a[c.status] = (a[c.status] || 0) + 1), a), {})

  if (argv.includes('--update-baseline')) {
    const keys = [...new Set(errors.map(errorKey))].sort()
    fs.writeFileSync(baselinePath, JSON.stringify(keys, null, 2) + '\n')
    console.log(`Wrote baseline: ${keys.length} known drift keys → ${path.relative(frontendRoot, baselinePath)}`)
    return
  }

  let baselineKeys = []
  try { baselineKeys = JSON.parse(fs.readFileSync(baselinePath, 'utf8')) } catch { baselineKeys = [] }
  const { newErrors, knownErrors, staleKeys } = diffAgainstBaseline(errors, baselineKeys)

  for (const e of newErrors) {
    console.error(`NEW ERROR ${e.kind}: '${e.field}' not allowed on ${e.schemaName} (${e.method} ${e.path}) — ${path.relative(frontendRoot, e.file)}:${e.line}`)
  }
  for (const w of warnings) {
    console.warn(`WARN ${w.kind}: ${w.field ?? ''} (${w.method} ${w.path}) — ${path.relative(frontendRoot, w.file)}:${w.line}`)
  }
  if (staleKeys.length) {
    console.warn(`\nWARN: ${staleKeys.length} baseline entries no longer drift — prune with: npm run api:check-bodies -- --update-baseline`)
  }
  console.log(`\nchecked: resolved=${counts.resolved || 0} unresolved-path=${counts['unresolved-path'] || 0} unresolved-body=${counts['unresolved-body'] || 0}`)
  console.log(`errors: new=${newErrors.length} known(baseline)=${knownErrors.length} warnings=${warnings.length}`)
  if (newErrors.length > 0) process.exit(1)
}

// Run main() only as a CLI, not when imported by tests.
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((err) => { console.error(err); process.exit(2) })
}
