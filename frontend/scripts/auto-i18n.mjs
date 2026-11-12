#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Auto-i18n: Bulk-convert hardcoded English strings to t() calls
 *
 * Usage:
 *   node scripts/auto-i18n.mjs --dry-run     # Preview changes (default)
 *   node scripts/auto-i18n.mjs --apply        # Apply changes in-place
 *
 * Excludes: catalog/, test files, .stories.tsx
 * Generates translation keys and updates en.json
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

const DRY_RUN = !process.argv.includes('--apply');
const VERBOSE = process.argv.includes('--verbose');

const SCAN_DIRS = [
  path.join(ROOT, 'src', 'pages'),
  path.join(ROOT, 'src', 'components'),
];

const EN_JSON_PATH = path.join(ROOT, 'src', 'i18n', 'translations', 'en.json');
const MIN_WORDS = 4;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function collectTsxFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsxFiles(full));
    } else if (entry.isFile() && entry.name.endsWith('.tsx')) {
      results.push(full);
    }
  }
  return results;
}

function shouldSkip(filePath) {
  const rel = path.relative(ROOT, filePath);
  const name = path.basename(filePath);
  return (
    rel.includes('catalog') ||
    rel.includes('Catalog') ||
    name.includes('.test.') ||
    name.includes('.spec.') ||
    name.includes('.stories.') ||
    filePath.includes('__tests__') ||
    filePath.includes('__mocks__')
  );
}

function countWords(str) {
  const words = str.match(/[A-Za-z][A-Za-z'-]*/g);
  return words ? words.length : 0;
}

function startsWithCapital(str) {
  return /^[A-Z]/.test(str.trim());
}

function isTechnicalString(str) {
  const s = str.trim();
  if (/^https?:\/\//i.test(s)) return true;
  if (/^mailto:/i.test(s)) return true;
  if (/^www\./i.test(s)) return true;
  if (/^\.{0,2}\//.test(s)) return true;
  if (/^[a-z][a-z0-9-]*(\s+[a-z][a-z0-9-]*)*$/.test(s)) return true;
  if (/^[a-zA-Z_$][a-zA-Z0-9_$.]*$/.test(s) && !s.includes(' ')) return true;
  if (/^#[0-9a-fA-F]{3,8}$/.test(s)) return true;
  if (/^[\d./-]+$/.test(s)) return true;
  if (/^[a-z]+\/[a-z0-9.+-]+$/i.test(s)) return true;
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return true;
  if (/^[a-z]+(-[a-z]+)+$/.test(s)) return true;
  if (/^[A-Z]{2,}[-/][A-Z0-9-/]+$/.test(s)) return true;
  if (s.includes('${')) return true;
  if (/^[A-Z][a-zA-Z]*\.[A-Z]/.test(s)) return true;
  return false;
}

function isExemptLine(line) {
  const trimmed = line.trim();
  if (/^import\s/.test(trimmed)) return true;
  if (/^from\s/.test(trimmed)) return true;
  if (/^\/\//.test(trimmed)) return true;
  if (/^\*/.test(trimmed)) return true;
  if (/console\.(log|error|warn|info|debug)\(/.test(trimmed)) return true;
  if (/^(type|interface)\s/.test(trimmed)) return true;
  return false;
}

function isInsideTCall(line, pos) {
  const tCallRe = /\bt\(\s*(['"`])/g;
  let tm;
  while ((tm = tCallRe.exec(line)) !== null) {
    const openPos = tm.index;
    const quote = tm[1];
    const closeQuoteIdx = line.indexOf(quote, tCallRe.lastIndex);
    if (closeQuoteIdx === -1) continue;
    const closeParen = line.indexOf(')', closeQuoteIdx);
    if (closeParen === -1) continue;
    if (pos >= openPos && pos <= closeParen) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Key generation
// ---------------------------------------------------------------------------

function fileToPrefix(filePath) {
  const rel = path.relative(path.join(ROOT, 'src'), filePath);
  let name = path.basename(filePath, '.tsx');

  // Remove common suffixes
  name = name.replace(/Page$/, '').replace(/Component$/, '').replace(/Modal$/, '');

  // Convert to camelCase
  name = name.charAt(0).toLowerCase() + name.slice(1);

  if (rel.startsWith('pages/admin/') || /pages\/Admin/.test(rel)) {
    return `admin.${name}`;
  }
  if (rel.startsWith('pages/')) {
    return name;
  }
  if (rel.startsWith('components/')) {
    const parts = rel.split(path.sep);
    if (parts.length > 2) {
      const subDir = parts[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      return `components.${subDir}.${name}`;
    }
    return `components.${name}`;
  }
  return name;
}

function stringToKeySuffix(text) {
  const words = text.match(/[A-Za-z]+/g) || [];
  const selected = words.slice(0, 5);
  if (selected.length === 0) return 'text';
  return selected
    .map((w, i) => i === 0 ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join('');
}

const usedKeys = new Set();

function generateKey(filePath, text) {
  const prefix = fileToPrefix(filePath);
  let suffix = stringToKeySuffix(text);
  let key = `${prefix}.${suffix}`;
  let counter = 2;
  const baseKey = key;
  while (usedKeys.has(key)) {
    key = `${baseKey}${counter}`;
    counter++;
  }
  usedKeys.add(key);
  return key;
}

// ---------------------------------------------------------------------------
// Replacement engine
// ---------------------------------------------------------------------------

function processFile(filePath) {
  const source = fs.readFileSync(filePath, 'utf-8');
  const lines = source.split('\n');
  const replacements = [];

  let inBlockComment = false;
  const hasUseTranslation = /useTranslation/.test(source);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (inBlockComment) {
      if (line.includes('*/')) inBlockComment = false;
      continue;
    }
    if (/\/\*/.test(line) && !/\*\//.test(line)) {
      inBlockComment = true;
      continue;
    }
    if (isExemptLine(line)) continue;

    let m;

    // Pattern 1: JSX text  >Some Text Here<
    const jsxTextRe = />([^<>{}`]+)</g;
    while ((m = jsxTextRe.exec(line)) !== null) {
      const raw = m[1];
      const text = raw.trim();
      if (!text || !/[A-Za-z]/.test(text)) continue;
      if (/[{}]/.test(text)) continue;
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;

      const key = generateKey(filePath, text);
      const leadingSpace = raw.startsWith(' ') ? ' ' : '';
      const trailingSpace = raw.endsWith(' ') ? ' ' : '';

      replacements.push({
        lineIdx: i,
        oldText: `>${raw}<`,
        newText: `>${leadingSpace}{t('${key}')}${trailingSpace}<`,
        key,
        value: text,
        kind: 'JSX text',
      });
    }

    // Pattern 2: String literal props
    const propRe = /((?:placeholder|aria-label|aria-description|title|alt))="([^"]+)"/g;
    while ((m = propRe.exec(line)) !== null) {
      const propName = m[1];
      const text = m[2].trim();
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;

      const key = generateKey(filePath, text);

      replacements.push({
        lineIdx: i,
        oldText: `${propName}="${m[2]}"`,
        newText: `${propName}={t('${key}')}`,
        key,
        value: text,
        kind: 'prop string',
      });
    }

    // Pattern 3: Toast messages
    const toastRe = /(toast(?:\.\w+)?)\(\s*(['"`])([^'"`]+)\2/g;
    while ((m = toastRe.exec(line)) !== null) {
      const toastCall = m[1];
      const quote = m[2];
      const text = m[3].trim();
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;

      const key = generateKey(filePath, text);

      replacements.push({
        lineIdx: i,
        oldText: `${toastCall}(${quote}${m[3]}${quote}`,
        newText: `${toastCall}(t('${key}')`,
        key,
        value: text,
        kind: 'toast message',
      });
    }

    // Pattern 4: Object property strings
    const objPropRe = /((?:label|description|message|title|text|heading|content|tooltip|hint|helperText|errorMessage)):\s*(['"])([^'"]+)\2/g;
    while ((m = objPropRe.exec(line)) !== null) {
      const prop = m[1];
      const quote = m[2];
      const text = m[3].trim();
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;

      const key = generateKey(filePath, text);

      replacements.push({
        lineIdx: i,
        oldText: `${prop}: ${quote}${m[3]}${quote}`,
        newText: `${prop}: t('${key}')`,
        key,
        value: text,
        kind: 'object property',
      });
    }
  }

  if (replacements.length === 0) return null;

  // Apply replacements line by line, right to left
  const newLines = [...lines];
  const byLine = {};
  for (const r of replacements) {
    if (!byLine[r.lineIdx]) byLine[r.lineIdx] = [];
    byLine[r.lineIdx].push(r);
  }

  for (const [lineIdx, lineReps] of Object.entries(byLine)) {
    let line = newLines[lineIdx];
    const sorted = lineReps.sort((a, b) => {
      const posA = line.indexOf(a.oldText);
      const posB = line.indexOf(b.oldText);
      return posB - posA;
    });
    for (const r of sorted) {
      const idx = line.indexOf(r.oldText);
      if (idx !== -1) {
        line = line.slice(0, idx) + r.newText + line.slice(idx + r.oldText.length);
      }
    }
    newLines[lineIdx] = line;
  }

  // Add useTranslation import if not present
  if (!hasUseTranslation) {
    let lastImportIdx = -1;
    for (let i = 0; i < newLines.length; i++) {
      if (/^import\s/.test(newLines[i].trim()) || /from\s+['"]/.test(newLines[i])) {
        lastImportIdx = i;
      }
    }

    const importLine = "import { useTranslation } from '@/i18n'";
    if (lastImportIdx >= 0) {
      newLines.splice(lastImportIdx + 1, 0, importLine);
    } else {
      newLines.unshift(importLine);
    }
  }

  let finalSource = newLines.join('\n');

  // Add const { t } = useTranslation() if not present
  if (!hasUseTranslation) {
    const finalLines = finalSource.split('\n');
    let inserted = false;

    for (let i = 0; i < finalLines.length; i++) {
      const line = finalLines[i];
      if (inserted) break;

      // Skip type/interface declarations
      if (/^(?:export\s+)?(?:type|interface)\s/.test(line.trim())) continue;

      // Look for component function declarations
      if (/(?:export\s+)?(?:default\s+)?(?:function|const)\s+\w+/.test(line)) {
        // Find opening brace
        for (let j = i; j < Math.min(i + 5, finalLines.length); j++) {
          if (finalLines[j].includes('{')) {
            // Make sure it is not a type annotation brace
            if (/:\s*\{$/.test(finalLines[j].trim())) break;
            const indent = finalLines[j].match(/^(\s*)/)?.[1] || '';
            finalLines.splice(j + 1, 0, `${indent}  const { t } = useTranslation()`);
            inserted = true;
            break;
          }
        }
      }
    }

    finalSource = finalLines.join('\n');
  }

  const newEntries = {};
  for (const r of replacements) {
    newEntries[r.key] = r.value;
  }

  return { filePath, originalSource: source, newSource: finalSource, replacements, newEntries };
}

// ---------------------------------------------------------------------------
// Set nested value in object
// ---------------------------------------------------------------------------

function setNestedValue(obj, dotKey, value) {
  const parts = dotKey.split('.');
  let current = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    if (!(parts[i] in current) || typeof current[parts[i]] !== 'object') {
      current[parts[i]] = {};
    }
    current = current[parts[i]];
  }
  current[parts[parts.length - 1]] = value;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  console.log(`\n${DRY_RUN ? 'DRY RUN' : 'APPLYING CHANGES'} - auto-i18n conversion\n`);

  // Backup en.json before anything
  const enRaw = fs.readFileSync(EN_JSON_PATH, 'utf-8');
  const enTranslations = JSON.parse(enRaw);

  if (!DRY_RUN) {
    const backupPath = EN_JSON_PATH + '.backup';
    fs.writeFileSync(backupPath, enRaw, 'utf-8');
    console.log(`Backup: ${backupPath}`);
  }

  // Load existing keys to avoid duplicates
  function collectKeys(obj, prefix = '') {
    for (const [k, v] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${k}` : k;
      usedKeys.add(fullKey);
      if (typeof v === 'object' && v !== null) {
        collectKeys(v, fullKey);
      }
    }
  }
  collectKeys(enTranslations);
  console.log(`Existing translation keys: ${usedKeys.size}`);

  // Collect files
  const allFiles = [];
  for (const dir of SCAN_DIRS) {
    allFiles.push(...collectTsxFiles(dir));
  }
  const files = allFiles.filter(f => !shouldSkip(f));
  console.log(`Files to process: ${files.length} (excluding catalog, tests, stories)\n`);

  let totalReplacements = 0;
  let filesModified = 0;
  const allNewEntries = {};
  const results = [];

  for (const filePath of files) {
    const result = processFile(filePath);
    if (!result) continue;

    results.push(result);
    filesModified++;
    totalReplacements += result.replacements.length;
    Object.assign(allNewEntries, result.newEntries);

    if (VERBOSE) {
      const rel = path.relative(ROOT, filePath);
      console.log(`  ${rel} - ${result.replacements.length} replacements`);
      for (const r of result.replacements) {
        const truncated = r.value.length > 60 ? r.value.slice(0, 57) + '...' : r.value;
        console.log(`      ${r.key} = "${truncated}"`);
      }
    }
  }

  console.log(`\nSummary:`);
  console.log(`   Files modified: ${filesModified}`);
  console.log(`   Strings converted: ${totalReplacements}`);
  console.log(`   New translation keys: ${Object.keys(allNewEntries).length}`);

  if (DRY_RUN) {
    console.log(`\nDry run complete. Run with --apply to write changes.`);

    const entries = Object.entries(allNewEntries);
    console.log(`\nPreview (first 20 of ${entries.length} new keys):`);
    for (const [key, value] of entries.slice(0, 20)) {
      const truncated = value.length > 50 ? value.slice(0, 47) + '...' : value;
      console.log(`   ${key} = "${truncated}"`);
    }
    if (entries.length > 20) {
      console.log(`   ... and ${entries.length - 20} more`);
    }
  } else {
    // Write modified files
    for (const result of results) {
      fs.writeFileSync(result.filePath, result.newSource, 'utf-8');
    }
    console.log(`   ${filesModified} files written`);

    // Update en.json
    for (const [key, value] of Object.entries(allNewEntries)) {
      setNestedValue(enTranslations, key, value);
    }

    fs.writeFileSync(EN_JSON_PATH, JSON.stringify(enTranslations, null, 2) + '\n', 'utf-8');
    console.log(`   en.json updated with ${Object.keys(allNewEntries).length} new keys`);
    console.log(`\nDone! Run 'node scripts/check-i18n.mjs' to verify remaining violations.`);
  }
}

main();
