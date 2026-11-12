#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Codemod: Replace manually-defined union types with imports from generated schema.
 *
 * Finds patterns like:
 *   export type FineStatus = 'unpaid' | 'paid' | 'waived' | 'partial';
 * And replaces them with:
 *   export type FineStatus = components['schemas']['FineStatus'];
 *
 * Only replaces types that exist in the generated schema.
 *
 * Usage:
 *   node scripts/codemod-use-generated-enums.mjs          # dry run
 *   node scripts/codemod-use-generated-enums.mjs --apply  # apply changes
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(__dirname, '..');
const schemaPath = resolve(frontendRoot, 'src', 'api', 'generated', 'schema.d.ts');

const apply = process.argv.includes('--apply');

// Step 1: Extract all enum type names from generated schema
const schemaContent = readFileSync(schemaPath, 'utf8');
const generatedEnums = new Set();

// Match lines like:        TypeName: "value1" | "value2" | ...;
const enumPattern = /^\s{8}(\w+): "[\w]+" \| "/gm;
let match;
while ((match = enumPattern.exec(schemaContent)) !== null) {
  generatedEnums.add(match[1]);
}

// Also catch single-value enums:        TypeName: "value";
const singlePattern = /^\s{8}(\w+): "\w+";$/gm;
while ((match = singlePattern.exec(schemaContent)) !== null) {
  generatedEnums.add(match[1]);
}

console.log(`Found ${generatedEnums.size} enum types in generated schema\n`);

// Step 2: Find all .ts files under src/api/ (excluding generated/)
function walkDir(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const full = resolve(dir, entry);
    if (entry === 'generated' || entry === 'node_modules') continue;
    const stat = statSync(full);
    if (stat.isDirectory()) {
      files.push(...walkDir(full));
    } else if (entry.endsWith('.ts') || entry.endsWith('.tsx')) {
      files.push(full);
    }
  }
  return files;
}

const searchDirs = [
  resolve(frontendRoot, 'src', 'api'),
  resolve(frontendRoot, 'src', 'types'),
  resolve(frontendRoot, 'src', 'constants'),
  resolve(frontendRoot, 'src', 'hooks'),
  resolve(frontendRoot, 'src', 'utils'),
];

const allFiles = [];
for (const dir of searchDirs) {
  try { allFiles.push(...walkDir(dir)); } catch { /* dir may not exist */ }
}

// Step 3: Process each file
// Match: export type TypeName = 'val1' | 'val2' | ...;
// Also handles no trailing semicolon and varying whitespace
const typePatternStr = /^(export )?type (\w+) = '[^']+'(\s*\|\s*'[^']+')*\s*;?$/gm;

let totalReplacements = 0;
let totalFiles = 0;

for (const filePath of allFiles) {
  const content = readFileSync(filePath, 'utf8');
  let modified = content;
  let fileReplacements = 0;
  const typesReplaced = [];

  let typeMatch;
  typePatternStr.lastIndex = 0;
  const replacements = [];

  while ((typeMatch = typePatternStr.exec(content)) !== null) {
    const exportPrefix = typeMatch[1] || '';
    const typeName = typeMatch[2];
    const fullMatch = typeMatch[0];

    if (generatedEnums.has(typeName)) {
      const replacement = `${exportPrefix}type ${typeName} = components['schemas']['${typeName}'];`;
      replacements.push({ from: fullMatch, to: replacement });
      typesReplaced.push(typeName);
      fileReplacements++;
    }
  }

  if (fileReplacements === 0) continue;

  for (const { from, to } of replacements) {
    modified = modified.replace(from, to);
  }

  // Add the components import if not already present
  if (!modified.includes("from '@/api/generated/schema'") &&
      !modified.includes("from '../generated/schema'") &&
      !modified.includes("from '../../generated/schema'")) {
    const importLine = "import type { components } from '@/api/generated/schema';";
    const lines = modified.split('\n');
    let lastImportIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('import ')) lastImportIdx = i;
    }
    if (lastImportIdx >= 0) {
      lines.splice(lastImportIdx + 1, 0, importLine);
    } else {
      lines.unshift(importLine);
    }
    modified = lines.join('\n');
  }

  const rel = relative(frontendRoot, filePath);
  const action = apply ? 'Fixed' : 'Would fix';
  console.log(`  ${action} ${fileReplacements} types in ${rel}: ${typesReplaced.join(', ')}`);

  if (apply) {
    writeFileSync(filePath, modified);
  }

  totalReplacements += fileReplacements;
  totalFiles++;
}

console.log(`\nTotal: ${totalReplacements} types in ${totalFiles} files`);
if (!apply && totalReplacements > 0) {
  console.log('\nRun with --apply to make the changes.');
}
