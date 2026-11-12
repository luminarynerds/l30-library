#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Fix pass 2: Remove ALL misplaced `const { t } = useTranslation()` lines
 * and re-insert them correctly.
 *
 * Strategy: Remove the hook line, then insert it as the FIRST statement
 * inside the first PascalCase function/arrow component.
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

function fixFile(filePath) {
  const source = fs.readFileSync(filePath, 'utf-8');
  const lines = source.split('\n');

  // Find hook lines
  const hookIndices = [];
  for (let i = 0; i < lines.length; i++) {
    if (isHookLine(lines[i])) hookIndices.push(i);
  }
  if (hookIndices.length === 0) return null;

  // Check if ANY hook line is misplaced by doing a simple brace-depth analysis
  // A correctly placed hook should be at depth >= 1 (inside a function body)
  let hasMisplaced = false;
  for (const idx of hookIndices) {
    let depth = 0;
    for (let i = 0; i < idx; i++) {
      for (const ch of lines[i]) {
        if (ch === '{') depth++;
        if (ch === '}') depth--;
      }
    }
    // Also count braces on the same line before the hook position
    // Actually, the hook is on its own line, so depth before this line tells us
    // depth 0 = top-level (inside an object literal or wrong place)
    // We need to check: is this inside a function body or inside an object/array?

    // Better check: look at the context. If the previous non-empty, non-hook line
    // is something like a property assignment, array element, or param, it's wrong
    let prevIdx = idx - 1;
    while (prevIdx >= 0 && lines[prevIdx].trim() === '') prevIdx--;
    if (prevIdx >= 0) {
      const prev = lines[prevIdx].trim();
      // Wrong contexts:
      // - Inside object literal: prev ends with , or { (and looks like key: value)
      // - Inside array: prev ends with , or [
      // - Inside destructured params: prev ends with , or ({
      // - After interface/type opening brace
      if (
        /^(?:export\s+)?(?:const|let|var)\s+\w+.*=\s*\{$/.test(prev) || // const X = {
        /^(?:export\s+)?(?:const|let|var)\s+\w+.*=\s*\[$/.test(prev) || // const X = [
        /[,{]\s*$/.test(prev) && !/=>\s*\{$/.test(prev) && !/\)\s*\{$/.test(prev) && !/function[^{]*\{$/.test(prev) // ends with , or { but not => { or ) {
      ) {
        // Check it's not actually after a function body opening
        if (!/=>\s*\{\s*$/.test(prev) && !/\)\s*\{\s*$/.test(prev) && !/function\s*\([^)]*\)\s*\{\s*$/.test(prev)) {
          hasMisplaced = true;
          break;
        }
      }
    }
  }

  if (!hasMisplaced) return null;

  // Remove all hook lines
  const cleaned = lines.filter((_, i) => !hookIndices.includes(i));

  // Check if there's already a correctly placed hook remaining
  const stillHasHook = cleaned.some(l => /const\s*\{[^}]*t[^}]*\}\s*=\s*useTranslation\(\)/.test(l));
  if (stillHasHook) {
    return { filePath, newSource: cleaned.join('\n'), action: 'removed misplaced duplicate' };
  }

  // Find the component function and insert the hook correctly
  // Look for PascalCase function declarations
  let insertIdx = -1;

  for (let i = 0; i < cleaned.length; i++) {
    const line = cleaned[i];
    const trimmed = line.trim();

    // Skip type/interface
    if (/^(?:export\s+)?(?:type|interface|enum)\s/.test(trimmed)) continue;

    // Match component function patterns
    const isComponentFunc =
      /^(?:export\s+)?(?:default\s+)?function\s+[A-Z]/.test(trimmed) ||
      /^(?:export\s+)?const\s+[A-Z]\w*\s*(?::\s*React\.FC)?/.test(trimmed);

    if (!isComponentFunc) continue;

    // Find the opening brace of the function BODY (not params)
    // We need to track parens to skip past parameter destructuring
    let parenDepth = 0;
    let foundParams = false;
    let braceDepth = 0;

    for (let j = i; j < Math.min(i + 30, cleaned.length); j++) {
      for (let c = 0; c < cleaned[j].length; c++) {
        const ch = cleaned[j][c];
        if (ch === '(') { parenDepth++; foundParams = true; }
        if (ch === ')') parenDepth--;

        // After all parens are closed, the next { is the function body
        if (foundParams && parenDepth === 0) {
          // Now find the next {
          // It might be on this line or a subsequent line
          const remaining = cleaned[j].substring(c + 1);
          const braceInRemaining = remaining.indexOf('{');
          if (braceInRemaining !== -1) {
            insertIdx = j;
            break;
          }
          // Check next lines
          for (let k = j + 1; k < Math.min(j + 5, cleaned.length); k++) {
            if (cleaned[k].includes('{')) {
              insertIdx = k;
              break;
            }
          }
          break;
        }

        // For arrow functions without parens or with => {
        if (ch === '=' && c + 1 < cleaned[j].length && cleaned[j][c + 1] === '>') {
          const afterArrow = cleaned[j].substring(c + 2).trim();
          if (afterArrow.startsWith('{')) {
            insertIdx = j;
            break;
          }
          // Check next line
          if (j + 1 < cleaned.length && cleaned[j + 1].trim().startsWith('{')) {
            insertIdx = j + 1;
            break;
          }
        }
      }
      if (insertIdx !== -1) break;
    }
    if (insertIdx !== -1) break;
  }

  if (insertIdx === -1) {
    return { filePath, newSource: cleaned.join('\n'), action: 'NEEDS MANUAL - no component found' };
  }

  const indent = cleaned[insertIdx].match(/^(\s*)/)?.[1] || '';
  cleaned.splice(insertIdx + 1, 0, `${indent}  const { t } = useTranslation()`);

  return { filePath, newSource: cleaned.join('\n'), action: 'fixed' };
}

function main() {
  console.log(`\n${DRY_RUN ? 'DRY RUN' : 'APPLYING'} - fix pass 2\n`);

  const dirs = [
    path.join(ROOT, 'src', 'pages'),
    path.join(ROOT, 'src', 'components'),
  ];

  const allFiles = [];
  for (const dir of dirs) allFiles.push(...collectTsxFiles(dir));

  let fixed = 0, manual = 0;
  const results = [];

  for (const f of allFiles) {
    const result = fixFile(f);
    if (!result) continue;
    results.push(result);
    const rel = path.relative(ROOT, f);
    if (result.action.includes('MANUAL')) {
      console.log(`  ⚠ ${rel} - ${result.action}`);
      manual++;
    } else {
      console.log(`  ✓ ${rel} - ${result.action}`);
      fixed++;
    }
  }

  console.log(`\nFixed: ${fixed}, Manual: ${manual}`);

  if (!DRY_RUN) {
    for (const r of results) fs.writeFileSync(r.filePath, r.newSource, 'utf-8');
    console.log(`${results.length} files written.`);
  } else {
    console.log('Run with --apply to write.');
  }
}

main();
