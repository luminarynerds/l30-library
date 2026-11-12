#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Fix hook placement for files where useTranslation() wasn't properly inserted.
 * Finds files that import useTranslation but don't call it inside a component,
 * and adds the hook call.
 */

import fs from 'fs';
import path from 'path';

const SRC_DIR = path.resolve('src');

// Find all .tsx files that reference t(' but don't have useTranslation()
function findFilesNeedingHookFix(dir) {
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === '__tests__' || entry.name === 'node_modules') continue;
      results.push(...findFilesNeedingHookFix(fullPath));
    } else if (entry.name.endsWith('.tsx')) {
      const content = fs.readFileSync(fullPath, 'utf-8');
      if (content.includes("t('") && content.includes('useTranslation') && !content.includes('useTranslation()')) {
        results.push(fullPath);
      }
    }
  }
  return results;
}

const files = [
  ...findFilesNeedingHookFix(path.join(SRC_DIR, 'pages')),
  ...findFilesNeedingHookFix(path.join(SRC_DIR, 'components')),
];

console.log(`Found ${files.length} files needing hook fix`);

for (const filePath of files) {
  let content = fs.readFileSync(filePath, 'utf-8');
  const relPath = path.relative(SRC_DIR, filePath);

  // Find the first function component that contains t(' calls
  // Strategy: find function declarations and check if t(' appears in their body
  const lines = content.split('\n');
  let insertLineIdx = -1;
  let braceDepth = 0;
  let inComponent = false;
  let componentStartLine = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check for function component declarations
    if (!inComponent) {
      if (/^(export\s+default\s+)?function\s+[A-Z]/.test(trimmed) ||
          /^(export\s+)?const\s+[A-Z]\w+\s*[:=]/.test(trimmed)) {
        // Check if this is a function with a body (has { )
        if (trimmed.includes('{')) {
          inComponent = true;
          componentStartLine = i;
          braceDepth = 0;
          // Count braces on this line
          for (const ch of trimmed) {
            if (ch === '{') braceDepth++;
            if (ch === '}') braceDepth--;
          }
          // The hook should go on the next line after the opening {
          insertLineIdx = i + 1;
          // Check if the line already has useTranslation
          const nextFewLines = lines.slice(i, i + 5).join('\n');
          if (nextFewLines.includes('useTranslation()')) {
            inComponent = false;
            insertLineIdx = -1;
            continue;
          }
          // Verify this component uses t('
          let hasT = false;
          let tmpDepth = braceDepth;
          for (let j = i + 1; j < lines.length; j++) {
            for (const ch of lines[j]) {
              if (ch === '{') tmpDepth++;
              if (ch === '}') tmpDepth--;
            }
            if (lines[j].includes("t('")) {
              hasT = true;
              break;
            }
            if (tmpDepth <= 0) break;
          }
          if (hasT) {
            break; // Found the right component
          } else {
            inComponent = false;
            insertLineIdx = -1;
          }
        }
      }
    }
  }

  if (insertLineIdx >= 0) {
    // Determine indentation
    const prevLine = lines[insertLineIdx - 1];
    const indent = prevLine.match(/^\s*/)?.[0] || '';
    const hookIndent = indent + '  ';

    lines.splice(insertLineIdx, 0, `${hookIndent}const { t } = useTranslation()`);
    content = lines.join('\n');
    fs.writeFileSync(filePath, content, 'utf-8');
    console.log(`FIXED: ${relPath}`);
  } else {
    console.log(`SKIP (couldn't find component): ${relPath}`);
  }
}
