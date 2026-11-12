#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Fix misplaced `const { t } = useTranslation()` lines.
 * The auto-i18n script sometimes inserts the hook declaration in the wrong place
 * (inside destructured params, array literals, etc).
 *
 * This script:
 * 1. Removes misplaced `const { t } = useTranslation()` lines
 * 2. Re-inserts them correctly inside the first React component function body
 *
 * Usage:
 *   node scripts/fix-i18n-hooks.mjs --dry-run    # Preview (default)
 *   node scripts/fix-i18n-hooks.mjs --apply       # Apply fixes
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

const DRY_RUN = !process.argv.includes('--apply');

function collectTsxFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) results.push(...collectTsxFiles(full));
    else if (entry.isFile() && entry.name.endsWith('.tsx')) results.push(full);
  }
  return results;
}

function isHookLine(line) {
  return /^\s*const\s*\{\s*t\s*\}\s*=\s*useTranslation\(\)\s*$/.test(line);
}

/**
 * Find the correct insertion point: the first line after a React component
 * function's opening brace.
 *
 * Looks for patterns like:
 *   export default function Foo(...) {
 *   export function Foo(...) {
 *   function Foo(...) {
 *   const Foo = (...) => {
 *   const Foo: React.FC = (...) => {
 *   export const Foo = (...) => {
 *
 * Returns the line index of the opening brace, or -1.
 */
function findComponentBodyStart(lines) {
  // Strategy: find function declarations that look like React components
  // (PascalCase name, returns JSX). Then find their opening brace.

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip type/interface/import/const enum declarations
    if (/^(?:export\s+)?(?:type|interface|enum)\s/.test(trimmed)) continue;
    if (/^import\s/.test(trimmed)) continue;

    // Match: export default function ComponentName( or function ComponentName(
    // or export function ComponentName(
    const funcMatch = trimmed.match(/^(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w*)\s*(?:<[^>]*>)?\s*\(/);
    if (funcMatch) {
      // Find the opening brace of this function
      for (let j = i; j < Math.min(i + 10, lines.length); j++) {
        const braceIdx = lines[j].indexOf('{');
        if (braceIdx !== -1) {
          // Make sure it's the function body brace, not a destructured param
          // If the line has both { and the function signature, it's likely the body
          // But if it's like `{ prop1, prop2 }` inside params, skip
          const beforeBrace = lines[j].substring(0, braceIdx);

          // If we're on the same line as the function declaration and there's a ( before {,
          // this might be a destructured parameter. Check if there's a matching ) after.
          if (j === i && trimmed.includes('({')) {
            // This is destructured params: function Foo({ prop1, prop2 }) {
            // Find the closing }) and then the actual body {
            let depth = 0;
            for (let k = j; k < Math.min(j + 20, lines.length); k++) {
              for (const ch of lines[k]) {
                if (ch === '{') depth++;
                if (ch === '}') depth--;
              }
              // When depth is 1, we found the function body opening
              // Actually, let's find the line with `): ` or `) {` or `}) {`
              if (/\)\s*(?::\s*\S+(?:\s*\|\s*\S+)*)?\s*\{?\s*$/.test(lines[k]) && depth <= 1) {
                // Check if brace is on this line
                if (lines[k].includes('{') && depth >= 1) {
                  return k;
                }
                // Brace might be on next line
                if (k + 1 < lines.length && lines[k + 1].trim() === '{') {
                  return k + 1;
                }
                if (k + 1 < lines.length && lines[k + 1].trim().startsWith('{')) {
                  return k + 1;
                }
              }
            }
            // Fallback: just return the first line where depth reaches 1 after params
            continue;
          }

          // Simple case: function Foo() { or function Foo(props) {
          return j;
        }
      }
    }

    // Match: const ComponentName = (...) => { or export const ComponentName =
    const arrowMatch = trimmed.match(/^(?:export\s+)?const\s+([A-Z]\w*)\s*(?::\s*\S+(?:<[^>]*>)?)?\s*=\s*/);
    if (arrowMatch) {
      // Find the arrow and opening brace
      for (let j = i; j < Math.min(i + 15, lines.length); j++) {
        if (/=>\s*\{/.test(lines[j]) || /=>\s*$/.test(lines[j])) {
          // The brace is on this line or next
          if (lines[j].includes('{')) return j;
          if (j + 1 < lines.length && lines[j + 1].trim().startsWith('{')) return j + 1;
        }
        // Also match: = function(...) {
        if (/function\s*(?:<[^>]*>)?\s*\([^)]*\)\s*\{/.test(lines[j])) {
          return j;
        }
      }
    }
  }

  return -1;
}

function fixFile(filePath) {
  const source = fs.readFileSync(filePath, 'utf-8');
  const lines = source.split('\n');

  // Check if file has the hook line
  const hookLineIndices = [];
  for (let i = 0; i < lines.length; i++) {
    if (isHookLine(lines[i])) {
      hookLineIndices.push(i);
    }
  }

  if (hookLineIndices.length === 0) return null;

  // Check if the hook is correctly placed (inside a function body, not in params/arrays)
  // A correctly placed hook should be after a line containing `{` that opens a function body
  // and before any return/JSX

  // Simple heuristic: check if the line BEFORE the hook is part of a destructured param,
  // array literal, or object literal
  let needsFix = false;
  for (const idx of hookLineIndices) {
    if (idx === 0) { needsFix = true; break; }
    const prevLine = lines[idx - 1]?.trim() || '';
    const nextLine = lines[idx + 1]?.trim() || '';

    // Bad placements:
    // 1. Inside destructured params: previous line ends with { and is a function signature
    if (/(?:function\s+\w+\s*\(?\s*\{|=>\s*\{|\(\s*\{)\s*$/.test(prevLine)) {
      // This could be correct if it's the function body, check if next lines look like params
      if (/^\w+\s*[,:}]/.test(nextLine) && !/^\s*(const|let|var|return|if|for|try|switch|useE|useS|useC|useR|useM|useQ)/.test(nextLine)) {
        needsFix = true;
        break;
      }
    }

    // 2. Inside array literal or object literal
    if (/[\[{,]\s*$/.test(prevLine) && /^\s*\{?\s*value:/.test(nextLine)) {
      needsFix = true;
      break;
    }

    // 3. Between destructured params
    if (/,\s*$/.test(prevLine) && /^\w+\s*[,:]/.test(nextLine)) {
      needsFix = true;
      break;
    }

    // 4. If the line before has opening ( or destructured params without closing
    if (/\(\s*$/.test(prevLine) || /\(\{\s*$/.test(prevLine)) {
      needsFix = true;
      break;
    }
  }

  if (!needsFix) return null;

  // Remove all misplaced hook lines
  const cleanedLines = lines.filter((_, i) => !hookLineIndices.includes(i));

  // Also check if useTranslation is already properly called elsewhere
  const alreadyHasProperHook = cleanedLines.some(l =>
    /const\s*\{[^}]*t[^}]*\}\s*=\s*useTranslation\(\)/.test(l)
  );

  if (alreadyHasProperHook) {
    // Just remove the duplicates
    return { filePath, newSource: cleanedLines.join('\n'), action: 'removed duplicate' };
  }

  // Find correct insertion point
  const bodyStart = findComponentBodyStart(cleanedLines);

  if (bodyStart === -1) {
    // Can't find component — just put it after imports as a top-level call won't work,
    // but at least it won't break syntax. Flag for manual review.
    return { filePath, newSource: cleanedLines.join('\n'), action: 'NEEDS MANUAL REVIEW - no component found' };
  }

  // Insert after the opening brace line
  const indent = cleanedLines[bodyStart].match(/^(\s*)/)?.[1] || '';
  cleanedLines.splice(bodyStart + 1, 0, `${indent}  const { t } = useTranslation()`);

  return { filePath, newSource: cleanedLines.join('\n'), action: 'fixed' };
}

function main() {
  console.log(`\n${DRY_RUN ? 'DRY RUN' : 'APPLYING'} - fix misplaced useTranslation hooks\n`);

  const dirs = [
    path.join(ROOT, 'src', 'pages'),
    path.join(ROOT, 'src', 'components'),
  ];

  const allFiles = [];
  for (const dir of dirs) {
    allFiles.push(...collectTsxFiles(dir));
  }

  let fixed = 0;
  let manualReview = 0;
  const results = [];

  for (const filePath of allFiles) {
    const result = fixFile(filePath);
    if (!result) continue;

    results.push(result);
    const rel = path.relative(ROOT, filePath);

    if (result.action.includes('MANUAL')) {
      console.log(`  ⚠ ${rel} - ${result.action}`);
      manualReview++;
    } else {
      console.log(`  ✓ ${rel} - ${result.action}`);
      fixed++;
    }
  }

  console.log(`\nFixed: ${fixed}, Need manual review: ${manualReview}`);

  if (!DRY_RUN) {
    for (const result of results) {
      fs.writeFileSync(result.filePath, result.newSource, 'utf-8');
    }
    console.log(`${results.length} files written.`);
  } else {
    console.log(`Run with --apply to write changes.`);
  }
}

main();
