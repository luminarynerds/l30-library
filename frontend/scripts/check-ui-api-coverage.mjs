/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import fs from 'node:fs'
import path from 'node:path'

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..')
const srcRoot = path.join(repoRoot, 'src')
const apiRoot = path.join(srcRoot, 'api')

const apiExcludes = [
  `${path.sep}__tests__${path.sep}`,
  `${path.sep}types.ts`,
  `${path.sep}index.ts`,
  `${path.sep}client.ts`,
  `${path.sep}api-client.ts`,
  `${path.sep}MANIFEST.md`,
  `${path.sep}API_REORGANIZATION.md`,
]

const uiRoots = ['components', 'pages', 'routes', 'features', 'hooks', 'services'].map((p) => path.join(srcRoot, p))

function walkFiles(dir, extensions) {
  if (!fs.existsSync(dir)) return []
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  const out = []

  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      out.push(...walkFiles(full, extensions))
    } else if (extensions.some((ext) => entry.name.endsWith(ext))) {
      out.push(full)
    }
  }

  return out
}

function read(file) {
  return fs.readFileSync(file, 'utf8')
}

function getExportedFunctions(content) {
  const functions = []
  const regex = /export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(/g
  let match
  while ((match = regex.exec(content))) {
    functions.push({ name: match[1], index: match.index })
  }
  return functions
}

function extractEndpoints(content, functions) {
  const endpoints = []
  const regex = /fetchApi(?:<[^>]+>)?\(\s*(["'`])(\/[A-Za-z0-9_\-/:${}.?=&]+)\1/g
  let match

  while ((match = regex.exec(content))) {
    const endpoint = match[2]
    const callIndex = match.index
    let functionName = 'unknown'

    for (const fn of functions) {
      if (fn.index <= callIndex) functionName = fn.name
      else break
    }

    endpoints.push({ endpoint, functionName })
  }

  return endpoints
}

function toRelative(file) {
  return path.relative(repoRoot, file)
}

function getUiImportIdentifiers(content) {
  const ids = new Set()
  const re = /import\s+([^;]+?)\s+from\s+["'][^"']+["']/g
  let m
  while ((m = re.exec(content))) {
    const clause = m[1].trim()

    if (clause.startsWith('{')) {
      const names = clause
        .slice(1, -1)
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      for (const raw of names) {
        const local = raw.includes(' as ') ? raw.split(' as ')[1].trim() : raw
        if (local) ids.add(local)
      }
      continue
    }

    if (clause.includes('{')) {
      const parts = clause.split(',').map((s) => s.trim())
      if (parts[0]) ids.add(parts[0])
      const named = parts.find((p) => p.startsWith('{'))
      if (named) {
        const names = named
          .slice(1, -1)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
        for (const raw of names) {
          const local = raw.includes(' as ') ? raw.split(' as ')[1].trim() : raw
          if (local) ids.add(local)
        }
      }
      continue
    }

    if (clause && !clause.startsWith('*')) ids.add(clause)
  }

  return ids
}

function confidenceFromEvidence(evidence) {
  if (evidence.some((e) => e.type === 'endpoint_literal')) return 'high'
  if (evidence.some((e) => e.type === 'api_function_call' || e.type === 'imported_api_symbol')) return 'medium'
  return 'low'
}

const apiFiles = walkFiles(apiRoot, ['.ts', '.tsx']).filter((file) => !apiExcludes.some((fragment) => file.includes(fragment)))
const uiFiles = uiRoots.flatMap((dir) => walkFiles(dir, ['.ts', '.tsx']))
const uiSources = uiFiles.map((file) => ({ file, content: read(file), importIds: getUiImportIdentifiers(read(file)) }))

const endpoints = new Map()

for (const apiFile of apiFiles) {
  const content = read(apiFile)
  const functions = getExportedFunctions(content)

  for (const row of extractEndpoints(content, functions)) {
    if (!endpoints.has(row.endpoint)) {
      endpoints.set(row.endpoint, {
        endpoint: row.endpoint,
        sources: [],
        functionNames: new Set(),
        uiReferences: new Set(),
        evidence: [],
      })
    }

    const entry = endpoints.get(row.endpoint)
    entry.sources.push(toRelative(apiFile))
    entry.functionNames.add(row.functionName)
  }
}

for (const entry of endpoints.values()) {
  const fnPatterns = [...entry.functionNames].map((fn) => ({ fn, pattern: new RegExp(`\\b${fn}\\b`) }))
  const endpointEscaped = entry.endpoint.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const endpointPattern = new RegExp(endpointEscaped)

  for (const { file, content, importIds } of uiSources) {
    const rel = toRelative(file)

    if (endpointPattern.test(content)) {
      entry.uiReferences.add(rel)
      entry.evidence.push({ file: rel, type: 'endpoint_literal', detail: entry.endpoint })
      continue
    }

    for (const { fn, pattern } of fnPatterns) {
      if (pattern.test(content)) {
        entry.uiReferences.add(rel)
        const type = importIds.has(fn) ? 'imported_api_symbol' : 'api_function_call'
        entry.evidence.push({ file: rel, type, detail: fn })
      }
    }
  }
}

const rows = [...endpoints.values()]
  .map((entry) => {
    const evidence = entry.evidence
      .map((e) => `${e.type}:${e.detail} @ ${e.file}`)
      .slice(0, 10)

    return {
      endpoint: entry.endpoint,
      sourceFiles: [...new Set(entry.sources)].sort(),
      functionNames: [...entry.functionNames].sort(),
      uiReferences: [...entry.uiReferences].sort(),
      detection_confidence: confidenceFromEvidence(entry.evidence),
      evidence,
    }
  })
  .sort((a, b) => a.endpoint.localeCompare(b.endpoint))

const covered = rows.filter((r) => r.uiReferences.length > 0)
const uncovered = rows.filter((r) => r.uiReferences.length === 0)

const report = {
  generatedAt: new Date().toISOString(),
  totalApiFilesScanned: apiFiles.length,
  uniqueEndpointsDiscovered: rows.length,
  endpointsWithUiReferences: covered.length,
  endpointsWithoutUiReferences: uncovered.length,
  endpointCoveragePct: rows.length ? Number(((covered.length / rows.length) * 100).toFixed(2)) : 0,
  uncovered,
}

const reportDir = path.join(repoRoot, 'reports')
fs.mkdirSync(reportDir, { recursive: true })
fs.writeFileSync(path.join(reportDir, 'ui-api-coverage.json'), JSON.stringify(report, null, 2))

const md = [
  '# UI Component Coverage for API Endpoints',
  '',
  `Generated: ${report.generatedAt}`,
  '',
  `- API files scanned: **${report.totalApiFilesScanned}**`,
  `- Unique endpoints discovered via fetchApi(...): **${report.uniqueEndpointsDiscovered}**`,
  `- Endpoints with at least one UI-layer reference: **${report.endpointsWithUiReferences}**`,
  `- Endpoints with no UI-layer reference found: **${report.endpointsWithoutUiReferences}**`,
  `- Coverage: **${report.endpointCoveragePct}%**`,
  '',
  'UI layer includes: `src/components`, `src/pages`, `src/routes`, `src/features`, `src/hooks`, `src/services`.',
  '',
  '## Endpoints missing UI references',
  '',
  '| Endpoint | API Function(s) | API Source File(s) | Confidence |',
  '| --- | --- | --- | --- |',
  ...uncovered.map(
    (r) =>
      `| \`${r.endpoint}\` | \`${r.functionNames.join(', ') || 'unknown'}\` | \`${r.sourceFiles.join(', ')}\` | \`${r.detection_confidence}\` |`
  ),
  '',
  '> Static analysis note: this checks endpoint literals, API symbol imports/usages, and direct API function-name references in UI-layer files. Dynamic indirection can still require manual verification.',
  '',
]

fs.writeFileSync(path.join(reportDir, 'ui-api-coverage.md'), md.join('\n'))

console.log(`Wrote ${toRelative(path.join(reportDir, 'ui-api-coverage.json'))}`)
console.log(`Wrote ${toRelative(path.join(reportDir, 'ui-api-coverage.md'))}`)
console.log(`Coverage: ${report.endpointCoveragePct}% (${report.endpointsWithUiReferences}/${report.uniqueEndpointsDiscovered})`)
