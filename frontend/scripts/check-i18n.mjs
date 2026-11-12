#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * CI Check: Detect hardcoded English strings in .tsx files
 *
 * Scans src/pages/ and src/components/ for hardcoded English strings
 * that should be wrapped in t() for internationalization.
 *
 * A violation is a string that:
 *   - Contains 4 or more English words
 *   - Starts with a capital letter
 *   - Is NOT already inside a t('...') call
 *   - Is NOT a URL, file path, CSS class, code identifier, or technical value
 *
 * Exit code 0 = no violations, exit code 1 = violations found.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const SCAN_DIRS = [
  path.join(ROOT, 'src', 'pages'),
  path.join(ROOT, 'src', 'components'),
];

/** Minimum number of words to consider a string a violation */
const MIN_WORDS = 4;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Recursively collect all .tsx files under `dir`.
 */
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

/**
 * Return true if the file path looks like a test file.
 */
function isTestFile(filePath) {
  const name = path.basename(filePath);
  return (
    name.includes('.test.') ||
    name.includes('.spec.') ||
    filePath.includes('__tests__') ||
    filePath.includes('__mocks__')
  );
}

/**
 * Count "English words" in a string.  A word is a contiguous run of
 * alphabetic (ASCII) characters (possibly containing apostrophes /
 * hyphens in the middle, like "don't" or "neurodivergent-friendly").
 */
function countWords(str) {
  const words = str.match(/[A-Za-z][A-Za-z'-]*/g);
  return words ? words.length : 0;
}

/**
 * Return true if the string starts with an uppercase ASCII letter.
 */
function startsWithCapital(str) {
  return /^[A-Z]/.test(str.trim());
}

/**
 * Return true if the candidate string should be ignored because it looks
 * like a technical / non-user-facing value.
 */
function isTechnicalString(str) {
  const s = str.trim();

  // URLs
  if (/^https?:\/\//i.test(s)) return true;
  if (/^mailto:/i.test(s)) return true;
  if (/^www\./i.test(s)) return true;

  // File paths (starts with / or ./ or ../ or contains file extensions)
  if (/^\.{0,2}\//.test(s)) return true;

  // CSS class names (contain hyphens and lowercase, e.g. "bg-lsc-orange")
  if (/^[a-z][a-z0-9-]*(\s+[a-z][a-z0-9-]*)*$/.test(s)) return true;

  // Looks like a code identifier (camelCase or snake_case with no spaces)
  if (/^[a-zA-Z_$][a-zA-Z0-9_$.]*$/.test(s) && !s.includes(' ')) return true;

  // Hex colours
  if (/^#[0-9a-fA-F]{3,8}$/.test(s)) return true;

  // Pure numbers / dates / semver
  if (/^[\d./-]+$/.test(s)) return true;

  // MIME types
  if (/^[a-z]+\/[a-z0-9.+-]+$/i.test(s)) return true;

  // Email addresses
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return true;

  // Data attributes, aria roles (contain only lowercase + hyphens)
  if (/^[a-z]+(-[a-z]+)+$/.test(s)) return true;

  // Placeholder patterns like "YYYY-MM-DD", "ISBN", single-word technical tokens
  if (/^[A-Z]{2,}[-/][A-Z0-9-/]+$/.test(s)) return true;

  // Template literals with interpolations  ${...}
  if (s.includes('${')) return true;

  // TypeScript / JSX type-like values  e.g. "React.ReactNode"
  if (/^[A-Z][a-zA-Z]*\.[A-Z]/.test(s)) return true;

  return false;
}

/**
 * Return true if the line is inside an import statement, comment,
 * console.log/error/warn, or type annotation context where strings
 * are acceptable.
 */
function isExemptLine(line) {
  const trimmed = line.trim();

  // Import statements
  if (/^import\s/.test(trimmed)) return true;
  if (/^from\s/.test(trimmed)) return true;

  // Single-line comments
  if (/^\/\//.test(trimmed)) return true;

  // Multi-line comment content (starts with * like JSDoc/block comment lines)
  if (/^\*/.test(trimmed)) return true;

  // Console statements (developer-only)
  if (/console\.(log|error|warn|info|debug)\(/.test(trimmed)) return true;

  // TypeScript type annotations / interfaces / type aliases
  if (/^(type|interface)\s/.test(trimmed)) return true;

  return false;
}

// ---------------------------------------------------------------------------
// Extraction patterns
// ---------------------------------------------------------------------------

/**
 * Find all hardcoded English string violations in a single file.
 * Returns an array of { line: number, text: string, kind: string }.
 */
function findViolations(filePath, source) {
  const violations = [];
  const lines = source.split('\n');

  // Track whether we are inside a block comment so we can skip those lines.
  let inBlockComment = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // ---- Block comment tracking -------------------------------------------
    if (inBlockComment) {
      if (line.includes('*/')) {
        inBlockComment = false;
      }
      continue;
    }
    if (/\/\*/.test(line) && !/\*\//.test(line)) {
      // Block comment starts but does not close on this line
      inBlockComment = true;
      continue;
    }

    // Skip exempt lines
    if (isExemptLine(line)) continue;

    // ---- Pattern 1: JSX text content  >Some Text Here< -------------------
    // Match text between > and < that is on the same line.
    const jsxTextRe = />([^<>{}`]+)</g;
    let m;
    while ((m = jsxTextRe.exec(line)) !== null) {
      const raw = m[1];
      const text = raw.trim();
      if (!text) continue;
      // Skip strings that are just whitespace / punctuation / numbers
      if (!/[A-Za-z]/.test(text)) continue;
      // Skip if it looks like a JSX expression fragment (contains { or })
      if (/[{}]/.test(text)) continue;
      // Skip very short non-sentences
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      // Make sure this is NOT inside a t('...') wrapper on the same line
      if (isInsideTCall(line, m.index)) continue;
      violations.push({ line: lineNum, text, kind: 'JSX text' });
    }

    // ---- Pattern 2: String literal props ----------------------------------
    // placeholder="...", aria-label="...", title="...", alt="..."
    const propRe = /(?:placeholder|aria-label|aria-description|title|alt)="([^"]+)"/g;
    while ((m = propRe.exec(line)) !== null) {
      const text = m[1].trim();
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;
      violations.push({ line: lineNum, text, kind: 'prop string' });
    }

    // ---- Pattern 3: Toast messages ----------------------------------------
    // toast.error("..."), toast.success("..."), toast.warning("..."), toast("...")
    const toastRe = /toast(?:\.\w+)?\(\s*(['"`])([^'"`]+)\1/g;
    while ((m = toastRe.exec(line)) !== null) {
      const text = m[2].trim();
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;
      violations.push({ line: lineNum, text, kind: 'toast message' });
    }

    // ---- Pattern 4: Object property strings -------------------------------
    // label: "...", description: "...", message: "...", title: "...",
    // text: "...", heading: "...", content: "..."
    const objPropRe = /(?:label|description|message|title|text|heading|content|tooltip|hint|helperText|errorMessage):\s*(['"])([^'"]+)\1/g;
    while ((m = objPropRe.exec(line)) !== null) {
      const text = m[2].trim();
      if (countWords(text) < MIN_WORDS) continue;
      if (!startsWithCapital(text)) continue;
      if (isTechnicalString(text)) continue;
      if (isInsideTCall(line, m.index)) continue;
      violations.push({ line: lineNum, text, kind: 'object property' });
    }
  }

  return violations;
}

/**
 * Rough heuristic: check whether the match position falls inside
 * a t('...') or t("...") wrapper on the same line.
 *
 * We look backwards from `pos` to see if there is an unclosed `t(`
 * or `t("` that wraps this position.
 */
function isInsideTCall(line, pos) {
  // Search for t( patterns before `pos` and see if the matching close
  // paren comes after `pos`.
  const tCallRe = /\bt\(\s*(['"`])/g;
  let tm;
  while ((tm = tCallRe.exec(line)) !== null) {
    const openPos = tm.index;
    const quote = tm[1];
    // Find the closing quote + )
    const closeQuoteIdx = line.indexOf(quote, tCallRe.lastIndex);
    if (closeQuoteIdx === -1) continue;
    const closeParen = line.indexOf(')', closeQuoteIdx);
    if (closeParen === -1) continue;
    // If pos falls between openPos and closeParen, it is wrapped.
    if (pos >= openPos && pos <= closeParen) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const allFiles = [];
  for (const dir of SCAN_DIRS) {
    allFiles.push(...collectTsxFiles(dir));
  }

  // Exclude test files
  const files = allFiles.filter((f) => !isTestFile(f));

  let totalViolations = 0;
  const fileReports = [];

  for (const filePath of files) {
    const source = fs.readFileSync(filePath, 'utf-8');
    const violations = findViolations(filePath, source);
    if (violations.length > 0) {
      totalViolations += violations.length;
      fileReports.push({ filePath, violations });
    }
  }

  // ---- Report -------------------------------------------------------------
  if (totalViolations === 0) {
    console.log('\n\x1b[32m\u2714 No hardcoded English strings found.\x1b[0m\n');
    process.exit(0);
  }

  console.log(
    `\n\x1b[31m\u2716 Found ${totalViolations} hardcoded English string${totalViolations === 1 ? '' : 's'} in ${fileReports.length} file${fileReports.length === 1 ? '' : 's'}.\x1b[0m\n`
  );

  for (const { filePath, violations } of fileReports) {
    const rel = path.relative(ROOT, filePath);
    console.log(`\x1b[1m${rel}\x1b[0m`);
    for (const v of violations) {
      const truncated = v.text.length > 80 ? v.text.slice(0, 77) + '...' : v.text;
      console.log(`  \x1b[33mline ${v.line}\x1b[0m  [${v.kind}]  "${truncated}"`);
    }
    console.log('');
  }

  console.log(
    `Wrap these strings with t() from the i18n system.\n` +
    `Example:  t('pages.someTranslationKey')\n`
  );

  process.exit(1);
}

main();
