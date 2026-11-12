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
]

function walkFiles(dir, extensions) {
  if (!fs.existsSync(dir)) return []
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  const out = []

  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walkFiles(full, extensions))
    else if (extensions.some((ext) => entry.name.endsWith(ext))) out.push(full)
  }

  return out
}

function read(file) {
  return fs.readFileSync(file, 'utf8')
}

function toRelative(file) {
  return path.relative(repoRoot, file)
}

function normalizePath(p) {
  return p
    .replace(/\$\{[^}]+\}/g, '{param}')
    .replace(/\{[^}]+\}/g, '{param}')
    .replace(/\?.*$/, '')
}

function extractFrontendEndpoints(content, file) {
  const hits = []
  const regex = /fetchApi(?:<[^>]+>)?\(\s*(["'`])(\/[A-Za-z0-9_\-/:${}.?=&]+)\1\s*(?:,\s*({[\s\S]*?}))?/g
  let m

  while ((m = regex.exec(content))) {
    const endpoint = m[2]
    const options = m[3] || ''
    const methodMatch = options.match(/method\s*:\s*(["'`])([A-Za-z]+)\1/i)
    const method = (methodMatch?.[2] || 'GET').toUpperCase()

    hits.push({ method, path: endpoint, normalizedPath: normalizePath(endpoint), file: toRelative(file) })
  }

  return hits
}

function loadOpenApi(input) {
  if (!input) throw new Error('Missing --openapi <file> argument')
  const resolved = path.isAbsolute(input) ? input : path.join(process.cwd(), input)
  const raw = fs.readFileSync(resolved, 'utf8')
  return JSON.parse(raw)
}

const openapiIndex = process.argv.indexOf('--openapi')
const openapiArg = openapiIndex >= 0 ? process.argv[openapiIndex + 1] : null
const openapi = loadOpenApi(openapiArg)

const apiFiles = walkFiles(apiRoot, ['.ts', '.tsx']).filter((file) => !apiExcludes.some((f) => file.includes(f)))

const frontendCalls = []
for (const apiFile of apiFiles) {
  frontendCalls.push(...extractFrontendEndpoints(read(apiFile), apiFile))
}

const frontendSet = new Map()
for (const call of frontendCalls) {
  const key = `${call.method} ${call.normalizedPath}`
  if (!frontendSet.has(key)) frontendSet.set(key, { ...call, files: new Set([call.file]) })
  else frontendSet.get(key).files.add(call.file)
}

const backendSet = new Map()
for (const [apiPath, methods] of Object.entries(openapi.paths || {})) {
  for (const [method] of Object.entries(methods || {})) {
    const m = method.toUpperCase()
    const key = `${m} ${normalizePath(apiPath)}`
    backendSet.set(key, { method: m, path: apiPath, normalizedPath: normalizePath(apiPath) })
  }
}

const frontendOnly = []
for (const [key, call] of frontendSet.entries()) {
  if (!backendSet.has(key)) {
    frontendOnly.push({ method: call.method, path: call.path, normalizedPath: call.normalizedPath, files: [...call.files].sort() })
  }
}

const backendOnly = []
for (const [key, route] of backendSet.entries()) {
  if (!frontendSet.has(key)) backendOnly.push(route)
}

const methodMismatch = []
const backendPathToMethods = new Map()
for (const route of backendSet.values()) {
  if (!backendPathToMethods.has(route.normalizedPath)) backendPathToMethods.set(route.normalizedPath, new Set())
  backendPathToMethods.get(route.normalizedPath).add(route.method)
}

for (const call of frontendSet.values()) {
  const backendMethods = backendPathToMethods.get(call.normalizedPath)
  if (backendMethods && !backendMethods.has(call.method)) {
    methodMismatch.push({
      path: call.path,
      normalizedPath: call.normalizedPath,
      frontendMethod: call.method,
      backendMethods: [...backendMethods].sort(),
      files: [...call.files].sort(),
    })
  }
}

const report = {
  generatedAt: new Date().toISOString(),
  totals: {
    frontendUniqueMethodPath: frontendSet.size,
    backendUniqueMethodPath: backendSet.size,
    frontendOnly: frontendOnly.length,
    backendOnly: backendOnly.length,
    methodMismatch: methodMismatch.length,
  },
  frontendOnly,
  backendOnly,
  methodMismatch,
}

const reportDir = path.join(repoRoot, 'reports')
fs.mkdirSync(reportDir, { recursive: true })
const outPath = path.join(reportDir, 'ui-backend-contract-diff.json')
fs.writeFileSync(outPath, JSON.stringify(report, null, 2))

console.log(`Wrote ${toRelative(outPath)}`)
console.log(`frontendOnly=${frontendOnly.length} backendOnly=${backendOnly.length} methodMismatch=${methodMismatch.length}`)
