#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Translation Validation Script
 *
 * Compares all translation files against en.json (source of truth) and reports:
 * - Missing keys in each language
 * - Extra keys that don't exist in en.json
 * - Empty or placeholder translations
 * - Coverage percentage for each language
 *
 * Exit codes:
 * - 0: All translations are complete and valid
 * - 1: Issues found (missing keys, extra keys, or empty values)
 *
 * Usage: node scripts/validate-translations.js [--verbose] [--fix-empty]
 */

const fs = require('fs');
const path = require('path');

// Configuration
const TRANSLATIONS_DIR = path.join(__dirname, '../frontend/src/i18n/translations');
const SOURCE_LANG = 'en';

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
};

// Parse command line arguments
const args = process.argv.slice(2);
const verbose = args.includes('--verbose') || args.includes('-v');
const showHelp = args.includes('--help') || args.includes('-h');

if (showHelp) {
  console.log(`
${colors.bold}Translation Validation Script${colors.reset}

Validates translation files against en.json (source of truth).

${colors.bold}Usage:${colors.reset}
  node scripts/validate-translations.js [options]

${colors.bold}Options:${colors.reset}
  -v, --verbose    Show detailed information about each issue
  -h, --help       Show this help message

${colors.bold}Exit Codes:${colors.reset}
  0  All translations are complete and valid
  1  Issues found (missing keys, extra keys, or empty values)
`);
  process.exit(0);
}

/**
 * Flatten a nested object into dot-notation keys
 * @param {object} obj - The object to flatten
 * @param {string} prefix - The current key prefix
 * @returns {Map<string, any>} - Map of flattened keys to values
 */
function flattenObject(obj, prefix = '') {
  const result = new Map();

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const nested = flattenObject(value, fullKey);
      for (const [nestedKey, nestedValue] of nested) {
        result.set(nestedKey, nestedValue);
      }
    } else {
      result.set(fullKey, value);
    }
  }

  return result;
}

/**
 * Check if a value is empty or a placeholder
 * @param {any} value - The value to check
 * @param {string} key - The key (for context)
 * @returns {{isEmpty: boolean, reason: string|null}}
 */
function checkEmptyOrPlaceholder(value, key) {
  if (value === null || value === undefined) {
    return { isEmpty: true, reason: 'null or undefined' };
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();

    if (trimmed === '') {
      return { isEmpty: true, reason: 'empty string' };
    }

    // Check for common placeholder patterns. TODO/FIXME/XXX are matched
    // case-sensitively so the Spanish word "Todo"/"Todos" and format literals
    // like "XXXX-XXXX" don't trigger false positives — only all-caps
    // developer markers do.
    const placeholderPatterns = [
      /^TODO\b/,
      /^FIXME\b/,
      /^XXX\b/,
      /^\[.*\]$/,  // [placeholder]
      /^<.*>$/,    // <placeholder>
      /^_+$/,      // underscores only
      /^\.{3,}$/,  // just dots
    ];

    for (const pattern of placeholderPatterns) {
      if (pattern.test(trimmed)) {
        return { isEmpty: true, reason: `placeholder pattern: ${trimmed}` };
      }
    }
  }

  return { isEmpty: false, reason: null };
}

/**
 * Get language display name
 * @param {string} code - Language code
 * @returns {string}
 */
function getLanguageName(code) {
  const names = {
    en: 'English',
    es: 'Spanish',
    fr: 'French',
    de: 'German',
    ar: 'Arabic',
    ru: 'Russian',
    zh: 'Chinese',
    ja: 'Japanese',
    ko: 'Korean',
    pt: 'Portuguese',
    it: 'Italian',
  };
  return names[code] || code.toUpperCase();
}

/**
 * Load and parse a JSON file
 * @param {string} filePath - Path to the JSON file
 * @returns {object|null}
 */
function loadJsonFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`${colors.red}Error loading ${filePath}: ${error.message}${colors.reset}`);
    return null;
  }
}

/**
 * Validate a translation file against the source
 * @param {string} langCode - The language code
 * @param {Map<string, any>} sourceKeys - Flattened source keys
 * @param {Map<string, any>} targetKeys - Flattened target keys
 * @returns {object} Validation results
 */
function validateTranslation(langCode, sourceKeys, targetKeys) {
  const missingKeys = [];
  const extraKeys = [];
  const emptyValues = [];

  // Find missing keys (in source but not in target)
  for (const [key, sourceValue] of sourceKeys) {
    if (!targetKeys.has(key)) {
      missingKeys.push({ key, sourceValue });
    }
  }

  // Find extra keys (in target but not in source) and empty values
  for (const [key, value] of targetKeys) {
    if (!sourceKeys.has(key)) {
      extraKeys.push({ key, value });
    } else {
      const { isEmpty, reason } = checkEmptyOrPlaceholder(value, key);
      if (isEmpty) {
        emptyValues.push({ key, value, reason });
      }
    }
  }

  const totalSourceKeys = sourceKeys.size;
  const translatedKeys = totalSourceKeys - missingKeys.length;
  const coveragePercent = totalSourceKeys > 0
    ? ((translatedKeys / totalSourceKeys) * 100).toFixed(1)
    : 0;

  return {
    langCode,
    langName: getLanguageName(langCode),
    totalSourceKeys,
    translatedKeys,
    coveragePercent,
    missingKeys,
    extraKeys,
    emptyValues,
    hasIssues: missingKeys.length > 0 || extraKeys.length > 0 || emptyValues.length > 0,
  };
}

/**
 * Print a section of keys with optional details
 * @param {string} title - Section title
 * @param {Array} items - Items to print
 * @param {string} color - Color code
 * @param {boolean} showDetails - Whether to show item details
 */
function printSection(title, items, color, showDetails = false) {
  if (items.length === 0) return;

  console.log(`\n  ${color}${title} (${items.length}):${colors.reset}`);

  if (showDetails) {
    const maxItems = 20;
    const displayItems = items.slice(0, maxItems);

    for (const item of displayItems) {
      if (item.reason) {
        console.log(`    ${colors.gray}- ${item.key} (${item.reason})${colors.reset}`);
      } else if (item.sourceValue !== undefined) {
        const preview = typeof item.sourceValue === 'string'
          ? item.sourceValue.substring(0, 50) + (item.sourceValue.length > 50 ? '...' : '')
          : JSON.stringify(item.sourceValue);
        console.log(`    ${colors.gray}- ${item.key}: "${preview}"${colors.reset}`);
      } else {
        console.log(`    ${colors.gray}- ${item.key}${colors.reset}`);
      }
    }

    if (items.length > maxItems) {
      console.log(`    ${colors.gray}... and ${items.length - maxItems} more${colors.reset}`);
    }
  } else {
    // Group by top-level section
    const sections = new Map();
    for (const item of items) {
      const section = item.key.split('.')[0];
      if (!sections.has(section)) {
        sections.set(section, 0);
      }
      sections.set(section, sections.get(section) + 1);
    }

    const sectionSummary = Array.from(sections.entries())
      .map(([section, count]) => `${section}: ${count}`)
      .join(', ');
    console.log(`    ${colors.gray}${sectionSummary}${colors.reset}`);
  }
}

/**
 * Get coverage bar visualization
 * @param {number} percent - Coverage percentage
 * @returns {string}
 */
function getCoverageBar(percent) {
  const width = 20;
  const filled = Math.round((percent / 100) * width);
  const empty = width - filled;

  let color;
  if (percent >= 90) color = colors.green;
  else if (percent >= 70) color = colors.yellow;
  else color = colors.red;

  return `${color}[${'='.repeat(filled)}${' '.repeat(empty)}]${colors.reset}`;
}

/**
 * Main validation function
 */
function main() {
  console.log(`\n${colors.bold}${colors.blue}Translation Validation Report${colors.reset}`);
  console.log(`${colors.gray}${'='.repeat(50)}${colors.reset}\n`);

  // Check if translations directory exists
  if (!fs.existsSync(TRANSLATIONS_DIR)) {
    console.error(`${colors.red}Error: Translations directory not found: ${TRANSLATIONS_DIR}${colors.reset}`);
    process.exit(1);
  }

  // Load source (English) translations
  const sourcePath = path.join(TRANSLATIONS_DIR, `${SOURCE_LANG}.json`);
  const sourceData = loadJsonFile(sourcePath);

  if (!sourceData) {
    console.error(`${colors.red}Error: Could not load source translations (${SOURCE_LANG}.json)${colors.reset}`);
    process.exit(1);
  }

  const sourceKeys = flattenObject(sourceData);
  console.log(`${colors.cyan}Source (${SOURCE_LANG}.json):${colors.reset} ${sourceKeys.size} keys\n`);

  // Find all translation files
  const files = fs.readdirSync(TRANSLATIONS_DIR)
    .filter(f => f.endsWith('.json') && f !== `${SOURCE_LANG}.json`)
    .sort();

  if (files.length === 0) {
    console.log(`${colors.yellow}No translation files found to validate.${colors.reset}`);
    process.exit(0);
  }

  // Validate each translation file
  const results = [];
  let hasAnyIssues = false;

  for (const file of files) {
    const langCode = path.basename(file, '.json');
    const filePath = path.join(TRANSLATIONS_DIR, file);
    const targetData = loadJsonFile(filePath);

    if (!targetData) {
      results.push({
        langCode,
        langName: getLanguageName(langCode),
        error: 'Could not load file',
        hasIssues: true,
      });
      hasAnyIssues = true;
      continue;
    }

    const targetKeys = flattenObject(targetData);
    const result = validateTranslation(langCode, sourceKeys, targetKeys);
    results.push(result);

    if (result.hasIssues) {
      hasAnyIssues = true;
    }
  }

  // Print results for each language
  console.log(`${colors.bold}Language Coverage:${colors.reset}\n`);

  for (const result of results) {
    if (result.error) {
      console.log(`${colors.red}${result.langName} (${result.langCode}): ERROR - ${result.error}${colors.reset}`);
      continue;
    }

    const bar = getCoverageBar(parseFloat(result.coveragePercent));
    const statusIcon = result.hasIssues ? `${colors.yellow}!${colors.reset}` : `${colors.green}+${colors.reset}`;

    console.log(`${statusIcon} ${colors.bold}${result.langName}${colors.reset} (${result.langCode}.json)`);
    console.log(`  Coverage: ${bar} ${result.coveragePercent}% (${result.translatedKeys}/${result.totalSourceKeys})`);

    if (result.hasIssues) {
      printSection('Missing keys', result.missingKeys, colors.red, verbose);
      printSection('Extra keys', result.extraKeys, colors.yellow, verbose);
      printSection('Empty/placeholder values', result.emptyValues, colors.yellow, verbose);
    }

    console.log('');
  }

  // Print summary
  console.log(`${colors.gray}${'='.repeat(50)}${colors.reset}`);
  console.log(`${colors.bold}Summary:${colors.reset}\n`);

  const completeLanguages = results.filter(r => !r.hasIssues && !r.error);
  const incompleteLanguages = results.filter(r => r.hasIssues || r.error);

  console.log(`  Total languages: ${results.length}`);
  console.log(`  ${colors.green}Complete: ${completeLanguages.length}${colors.reset}`);
  console.log(`  ${colors.yellow}Needs work: ${incompleteLanguages.length}${colors.reset}`);

  if (incompleteLanguages.length > 0) {
    console.log(`\n  ${colors.bold}Languages needing attention:${colors.reset}`);
    for (const lang of incompleteLanguages) {
      if (lang.error) {
        console.log(`    - ${lang.langName}: ${colors.red}${lang.error}${colors.reset}`);
      } else {
        const issues = [];
        if (lang.missingKeys.length > 0) issues.push(`${lang.missingKeys.length} missing`);
        if (lang.extraKeys.length > 0) issues.push(`${lang.extraKeys.length} extra`);
        if (lang.emptyValues.length > 0) issues.push(`${lang.emptyValues.length} empty`);
        console.log(`    - ${lang.langName} (${lang.coveragePercent}%): ${issues.join(', ')}`);
      }
    }
  }

  console.log('');

  // Exit with appropriate code
  if (hasAnyIssues) {
    console.log(`${colors.red}Validation failed: Translation issues found.${colors.reset}\n`);
    if (!verbose) {
      console.log(`${colors.gray}Tip: Run with --verbose for detailed issue information.${colors.reset}\n`);
    }
    process.exit(1);
  } else {
    console.log(`${colors.green}All translations are complete and valid!${colors.reset}\n`);
    process.exit(0);
  }
}

// Run the script
main();
