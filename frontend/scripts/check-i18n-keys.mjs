#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Static i18n key-existence check.
 *
 * Three assertions:
 *   1. Every literal-key t() / getTranslation() call in frontend/src resolves
 *      to a string in src/i18n/translations/en.json.
 *   2. No translation file declares the same key twice inside one object.
 *      JSON.parse keeps the last one, so a duplicate silently deletes a whole
 *      block of copy and no other check can see it.
 *   3. Every key in en.json exists in each other locale file. Missing keys fall
 *      back to English at runtime without warning, so only a static check finds
 *      them.
 *
 * Dynamic calls (variable arg) are skipped. Lines with `// i18n-dynamic-ok`
 * are skipped entirely.
 *
 * Exit codes:
 *   0  clean (or warn-only mode)
 *   1  missing keys, duplicate keys, or untranslated keys (strict mode)
 *
 * Flags:
 *   --warn   report but exit 0
 *   --json   JSON output
 *   --staged scan only files staged for commit (pre-commit hook use)
 */
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { join, resolve, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = resolve(__dirname, '..')
const SRC_ROOT = join(FRONTEND_ROOT, 'src')
const TRANSLATIONS_DIR = join(FRONTEND_ROOT, 'src/i18n/translations')
const EN_JSON_PATH = join(TRANSLATIONS_DIR, 'en.json')

const args = new Set(process.argv.slice(2))
const WARN_ONLY = args.has('--warn')
const JSON_OUT = args.has('--json')
const STAGED = args.has('--staged')

// Match t('key.path') / t("key.path") / getTranslation('key', ...)
// Excludes template literals and variables. Allows optional whitespace.
const CALL_RE = /(?<![A-Za-z0-9_$.])(t|getTranslation)\s*\(\s*(['"])([A-Za-z_][A-Za-z0-9_.-]*)\2/g

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    const s = statSync(p)
    if (s.isDirectory()) {
      if (entry === 'node_modules' || entry === '__tests__' || entry === 'translations') continue
      walk(p, out)
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.(test|spec|stories)\.(ts|tsx)$/.test(entry) && !entry.endsWith('.d.ts')) {
      out.push(p)
    }
  }
  return out
}

function loadEn() {
  const raw = readFileSync(EN_JSON_PATH, 'utf8')
  return JSON.parse(raw)
}

function hasKey(obj, dotted) {
  const parts = dotted.split('.')
  let cur = obj
  for (const p of parts) {
    if (cur && typeof cur === 'object' && p in cur) {
      cur = cur[p]
    } else {
      return false
    }
  }
  return typeof cur === 'string'
}

function localeFiles() {
  return readdirSync(TRANSLATIONS_DIR)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => ({ name: f, path: join(TRANSLATIONS_DIR, f) }))
}

// JSON.parse silently drops all but the last of a repeated key, so duplicates
// have to be found in the raw text. Walks the source tracking one key set per
// open object; arrays push a null scope because they hold no keys.
function findDuplicateKeys(raw) {
  const dupes = []
  const stack = []
  let i = 0
  while (i < raw.length) {
    const ch = raw[i]
    if (ch === '{') {
      stack.push(new Set())
    } else if (ch === '[') {
      stack.push(null)
    } else if (ch === '}' || ch === ']') {
      stack.pop()
    } else if (ch === '"') {
      const start = i
      let text = ''
      i++
      while (i < raw.length && raw[i] !== '"') {
        if (raw[i] === '\\') {
          text += raw.slice(i, i + 2)
          i += 2
          continue
        }
        text += raw[i]
        i++
      }
      i++
      let j = i
      while (j < raw.length && /\s/.test(raw[j])) j++
      const scope = stack[stack.length - 1]
      if (raw[j] === ':' && scope) {
        if (scope.has(text)) {
          dupes.push({ key: text, line: raw.slice(0, start).split('\n').length })
        } else {
          scope.add(text)
        }
      }
      continue
    }
    i++
  }
  return dupes
}

function flatten(obj, prefix = '', out = new Map()) {
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      flatten(v, path, out)
    } else {
      out.set(path, v)
    }
  }
  return out
}

function fileList() {
  if (STAGED) {
    const out = execSync('git diff --cached --name-only --diff-filter=ACM', { cwd: FRONTEND_ROOT, encoding: 'utf8' })
    return out
      .split('\n')
      .filter(Boolean)
      .map((p) => resolve(FRONTEND_ROOT, '..', p))
      .filter((p) => p.startsWith(SRC_ROOT) && /\.(ts|tsx)$/.test(p) && !/\.(test|spec|stories|d)\.(ts|tsx)$/.test(p) && !/__tests__/.test(p))
      .filter(existsSync)
  }
  return walk(SRC_ROOT)
}

function main() {
  const en = loadEn()
  const files = fileList()
  const missing = []
  let totalCalls = 0

  for (const file of files) {
    const text = readFileSync(file, 'utf8')
    const lines = text.split('\n')
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      if (line.includes('i18n-dynamic-ok')) continue
      CALL_RE.lastIndex = 0
      let m
      while ((m = CALL_RE.exec(line)) !== null) {
        totalCalls++
        const key = m[3]
        if (!hasKey(en, key)) {
          missing.push({ file: relative(FRONTEND_ROOT, file), line: i + 1, key, fn: m[1] })
        }
      }
    }
  }

  const locales = localeFiles()
  const duplicates = []
  for (const locale of locales) {
    for (const d of findDuplicateKeys(readFileSync(locale.path, 'utf8'))) {
      duplicates.push({ file: locale.name, ...d })
    }
  }

  const enKeys = flatten(en)
  const untranslated = []
  for (const locale of locales) {
    if (locale.name === 'en.json') continue
    const theirs = flatten(JSON.parse(readFileSync(locale.path, 'utf8')))
    const gaps = [...enKeys.keys()].filter((k) => !theirs.has(k))
    if (gaps.length > 0) untranslated.push({ file: locale.name, keys: gaps.sort() })
  }

  if (JSON_OUT) {
    process.stdout.write(JSON.stringify({ totalCalls, missing, duplicates, untranslated }, null, 2) + '\n')
  } else {
    if (duplicates.length > 0) {
      console.log(`[lint:i18n] ${duplicates.length} duplicate key${duplicates.length === 1 ? '' : 's'} (JSON.parse keeps only the last, so the earlier block is dead):`)
      for (const d of duplicates) console.log(`  ${d.file}:${d.line}  ${d.key}`)
    }
    for (const u of untranslated) {
      console.log(`[lint:i18n] ${u.file} is missing ${u.keys.length} key${u.keys.length === 1 ? '' : 's'} present in en.json:`)
      for (const k of u.keys) console.log(`  ${k}`)
    }
    if (missing.length === 0) {
      if (duplicates.length === 0 && untranslated.length === 0) {
        console.log(`[lint:i18n] OK -- ${totalCalls} literal t()/getTranslation() calls, 0 missing keys, ${locales.length} locales in sync`)
      }
    } else {
      console.log(`[lint:i18n] ${missing.length} missing key${missing.length === 1 ? '' : 's'} across ${totalCalls} literal calls:`)
      const byKey = new Map()
      for (const r of missing) {
        if (!byKey.has(r.key)) byKey.set(r.key, [])
        byKey.get(r.key).push(`${r.file}:${r.line}`)
      }
      for (const [k, locs] of [...byKey.entries()].sort()) {
        console.log(`  ${k}`)
        for (const l of locs) console.log(`    ${l}`)
      }
    }
  }

  const failed = missing.length > 0 || duplicates.length > 0 || untranslated.length > 0
  if (failed && !WARN_ONLY) process.exit(1)
}

main()
