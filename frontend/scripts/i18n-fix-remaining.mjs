#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Careful i18n migration for files that failed the first pass.
 * Uses a safer approach for import/hook insertion.
 */

import fs from 'fs';
import path from 'path';

const SRC_DIR = path.resolve('src');
const EN_JSON_PATH = path.join(SRC_DIR, 'i18n', 'translations', 'en.json');

// Load existing translations
const existingTranslations = JSON.parse(fs.readFileSync(EN_JSON_PATH, 'utf-8'));

// Track new translations
const newTranslations = {};

// Collect all existing keys
const usedKeys = new Set();
function collectExistingKeys(obj, prefix = '') {
  for (const [key, val] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof val === 'string') usedKeys.add(fullKey);
    else if (typeof val === 'object' && val !== null) collectExistingKeys(val, fullKey);
  }
}
collectExistingKeys(existingTranslations);

function getDomain(filePath) {
  const name = path.basename(filePath, '.tsx');
  const dir = path.dirname(filePath);
  if (name.startsWith('Admin') || dir.includes('/admin/')) return 'admin';
  if (name.startsWith('Staff') || dir.includes('/staff/')) return 'staff';
  if (dir.includes('/account/')) return 'patron';
  if (dir.includes('/board/')) return 'admin';
  if (dir.includes('/closure/') || dir.includes('/closure-management/')) return 'closure';
  if (dir.includes('/linked-data/')) return 'linkedData';
  if (dir.includes('/onboarding/')) return 'onboarding';
  if (dir.includes('/pto/')) return 'scheduling';
  if (dir.includes('/shift-swap/')) return 'scheduling';
  if (dir.includes('/annual-reports/')) return 'reports';
  if (dir.includes('/guides/')) return 'guides';
  if (dir.includes('/legal/')) return 'legal';
  if (name.includes('Event')) return 'events';
  if (name.includes('Card') || name.includes('Application')) return 'patron';
  if (name.includes('Seed')) return 'seedLibrary';
  if (name.includes('Insurance') || name.includes('Compliance')) return 'compliance';
  if (name.includes('Legal')) return 'legal';
  if (name.includes('Business')) return 'community';
  if (name.includes('Gutenberg')) return 'digital';
  if (name.includes('Donate') || name.includes('Career') || name.includes('About')) return 'pages';
  if (name.includes('AI') || name.includes('Tech')) return 'techSupport';
  if (name.includes('Content')) return 'staff';
  if (name.includes('Print')) return 'print';
  return 'common';
}

function generateKey(domain, str, context = '') {
  let key = str
    .replace(/[^a-zA-Z0-9\s]/g, '')
    .trim()
    .split(/\s+/)
    .slice(0, 4)
    .map((w, i) => i === 0 ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join('');
  if (!key) key = 'text';
  if (context) key = context + key.charAt(0).toUpperCase() + key.slice(1);
  return `${domain}.${key}`;
}

// TypeScript / code words that should NOT be translated
const CODE_WORDS = new Set([
  'Promise', 'Array', 'Object', 'String', 'Number', 'Boolean', 'Date', 'Map', 'Set',
  'Record', 'Partial', 'Required', 'Readonly', 'Pick', 'Omit', 'Exclude', 'Extract',
  'React', 'Component', 'Fragment', 'Element', 'Node', 'Props', 'State',
  'HTMLElement', 'HTMLDivElement', 'HTMLInputElement', 'HTMLButtonElement',
  'FormEvent', 'MouseEvent', 'KeyboardEvent', 'ChangeEvent', 'FocusEvent',
  'Ref', 'RefObject', 'MutableRefObject', 'ForwardedRef',
  'Dispatch', 'SetStateAction', 'Reducer', 'Context',
  'Navigator', 'Location', 'History',
  'Response', 'Request', 'Headers', 'FormData', 'URLSearchParams',
  'Error', 'TypeError', 'ReferenceError', 'SyntaxError',
  'Blob', 'File', 'FileList', 'FileReader',
  'AbortController', 'AbortSignal',
  'Timeout', 'Interval', 'Timer',
  'EventTarget', 'EventListener', 'CustomEvent',
  'Observable', 'Subscription', 'Subject',
  'Iterator', 'Generator', 'AsyncGenerator',
  'Symbol', 'BigInt', 'RegExp', 'JSON', 'Math',
  'Intl', 'Proxy', 'Reflect', 'WeakMap', 'WeakSet', 'WeakRef',
]);

function isTranslatableString(str) {
  if (!str || str.trim().length === 0) return false;
  const trimmed = str.trim();
  if (trimmed.length < 2) return false;
  if (/^[0-9.,$%#@!*+\-/\\=<>{}()\[\]|&^~`]+$/.test(trimmed)) return false;
  if (/^https?:\/\//.test(trimmed)) return false;
  if (/^[a-z_]+[A-Z]/.test(trimmed) && !trimmed.includes(' ')) return false;
  if (/^[A-Z_]+$/.test(trimmed)) return false;
  if (/^\{/.test(trimmed)) return false;
  if (/^[a-z]+\.[a-z]+/.test(trimmed) && !trimmed.includes(' ')) return false;
  if (/^\/[a-z]/.test(trimmed)) return false;
  if (/^#[0-9a-fA-F]+$/.test(trimmed)) return false;
  if (/^(true|false|null|undefined)$/.test(trimmed)) return false;
  if (/^(sm|md|lg|xl|2xl|xs)$/.test(trimmed)) return false;
  if (!/[a-zA-Z]/.test(trimmed)) return false;
  // Skip TypeScript / code type names
  if (CODE_WORDS.has(trimmed)) return false;

  const words = trimmed.split(/\s+/);
  if (words.length === 1) {
    if (/^[A-Z][a-z]/.test(trimmed) && trimmed.length >= 3) return true;
    return false;
  }
  return words.length >= 2;
}

function findExistingKey(value, translations, prefix = '') {
  for (const [key, val] of Object.entries(translations)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof val === 'string' && val === value) return fullKey;
    else if (typeof val === 'object' && val !== null) {
      const found = findExistingKey(value, val, fullKey);
      if (found) return found;
    }
  }
  return null;
}

function setNestedValue(obj, dotPath, value) {
  const parts = dotPath.split('.');
  let current = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    if (!current[parts[i]] || typeof current[parts[i]] !== 'object') current[parts[i]] = {};
    current = current[parts[i]];
  }
  current[parts[parts.length - 1]] = value;
}

function getOrCreateKey(domain, value, context = '') {
  const existing = findExistingKey(value, existingTranslations);
  if (existing) return existing;
  const newExisting = findExistingKey(value, newTranslations);
  if (newExisting) return newExisting;

  let key = generateKey(domain, value, context);
  let counter = 0;
  let finalKey = key;
  while (usedKeys.has(finalKey)) {
    counter++;
    finalKey = `${key}${counter}`;
  }
  usedKeys.add(finalKey);
  setNestedValue(newTranslations, finalKey, value);
  return finalKey;
}

// The list of files that still need migration
const files = [
  'src/components/AdminProgramForm.tsx',
  'src/components/EventForm.tsx',
  'src/components/account/ListsSection.tsx',
  'src/components/account/OverviewSection.tsx',
  'src/components/account/QuickActionsCard.tsx',
  'src/components/account/SettingsSection.tsx',
  'src/components/annual-reports/GenerateReportModal.tsx',
  'src/components/annual-reports/ReportDetailsModal.tsx',
  'src/components/annual-reports/ReportsList.tsx',
  'src/components/board/BoardMemberForm.tsx',
  'src/components/board/CommitteeForm.tsx',
  'src/components/board/DocumentsSection.tsx',
  'src/components/board/MeetingForm.tsx',
  'src/components/board/MinutesForm.tsx',
  'src/components/board/MotionForm.tsx',
  'src/components/board/VotingForm.tsx',
  'src/components/closure-management/ClosureManagementPanel.tsx',
  'src/components/closure-management/EventCancellationForm.tsx',
  'src/components/closure-management/ExternalServicePanel.tsx',
  'src/components/closure-management/PatronNotificationPreview.tsx',
  'src/components/closure-management/ReopeningWizard.tsx',
  'src/components/linked-data/LinkedDataViewer.tsx',
  'src/components/onboarding/PatronWelcomeWizard.tsx',
  'src/components/pto/GradualInboxReturn.tsx',
  'src/components/pto/PTORequestForm.tsx',
  'src/components/shift-swap/CreateListingModal.tsx',
  'src/components/shift-swap/ListingDetailsModal.tsx',
  'src/components/staff/BulkOperationsPanel.tsx',
  'src/components/staff/PatronManagement/PatronDetails.tsx',
  'src/components/staff/SendNotificationModal.tsx',
  'src/pages/AIToolsPage.tsx',
  'src/pages/AboutPage.tsx',
  'src/pages/BusinessResourcesPage.tsx',
  'src/pages/CardApplicationPage.tsx',
  'src/pages/CareersPage.tsx',
  'src/pages/DonatePage.tsx',
  'src/pages/GutenbergPage.tsx',
  'src/pages/InsuranceManagement.tsx',
  'src/pages/LegalResourcesPage.tsx',
  'src/pages/SeedLibraryPage.tsx',
  'src/pages/SelfServiceTechSupportHub.tsx',
  'src/pages/StaffContentFlagsPage.tsx',
  'src/pages/guides/CheckPrintJobsGuide.tsx',
  'src/pages/guides/LibraryCardGuide.tsx',
  'src/pages/guides/PasswordResetGuide.tsx',
  'src/pages/guides/ScamRecognitionGuide.tsx',
  'src/pages/guides/WiFiTroubleshootingGuide.tsx',
  'src/pages/guides/WirelessPrintingGuide.tsx',
];

let modifiedCount = 0;

for (const relFile of files) {
  const filePath = path.resolve(relFile);
  if (!fs.existsSync(filePath)) {
    console.log(`SKIP (not found): ${relFile}`);
    continue;
  }

  let content = fs.readFileSync(filePath, 'utf-8');
  const domain = getDomain(filePath);
  let modified = false;

  // Apply text replacements (same patterns as original but without modifying imports/hooks)
  const origContent = content;

  // Helper: Check if a match is inside a TypeScript type context (not JSX)
  function isInTypeContext(fullContent, matchIndex) {
    // Look at the 200 chars before the match
    const before = fullContent.substring(Math.max(0, matchIndex - 200), matchIndex);
    // If we see ): or => or : followed by type-like patterns, it's likely a type annotation
    if (/(?:=>|:\s*)\s*$/.test(before)) return true;
    if (/(?:Promise|Array|Record|Map|Set|Partial|Required|Readonly|Pick|Omit|Exclude|Extract|React\.\w+)\s*$/.test(before)) return true;
    // If previous non-whitespace char is a type operator
    const lastNonWs = before.replace(/\s+$/, '');
    if (lastNonWs.endsWith('|') || lastNonWs.endsWith('&') || lastNonWs.endsWith(',')) return true;
    // Check if inside an interface or type declaration
    const lastLineBreak = before.lastIndexOf('\n');
    const currentLine = lastLineBreak >= 0 ? before.substring(lastLineBreak) : before;
    if (/^\s*(interface|type)\s/.test(currentLine)) return true;
    if (/:\s*\w+\s*$/.test(before)) return true; // property: Type>
    return false;
  }

  // Pattern 1: Multi-word JSX text
  content = content.replace(
    />([\s]*)((?:[A-Z][a-z]+(?:\s+[a-zA-Z'',.\-–-!?:;()&/0-9$#@%]+)*){2,})([\s]*)</g,
    (match, pre, text, post, offset) => {
      if (isInTypeContext(content, offset)) return match;
      const trimmed = text.trim();
      if (!isTranslatableString(trimmed)) return match;
      if (trimmed.includes('{') || trimmed.includes('}')) return match;
      const key = getOrCreateKey(domain, trimmed);
      modified = true;
      return `>${pre}{t('${key}')}${post}<`;
    }
  );

  // Pattern 2: Common single words (only in JSX context, not type annotations)
  content = content.replace(
    />(\s*)(Save|Cancel|Delete|Edit|Search|Submit|Close|Back|Next|Previous|Refresh|Remove|Confirm|Apply|Reset|Clear|Loading|Filter|Sort|Download|Upload|Share|Copy|Details|Overview|Settings|Dismiss|Retry|Hide|Show|Expand|Collapse|Renew|Return|Checkout|Dashboard|Reports|Analytics|Notifications|Profile|Actions|Login|Import|Export|Generate|Verify|Process|Processing|Enabled|Disabled)(\s*)</g,
    (match, pre, word, post, offset) => {
      if (isInTypeContext(content, offset)) return match;
      const key = getOrCreateKey('common', word);
      modified = true;
      return `>${pre}{t('${key}')}${post}<`;
    }
  );

  // Pattern 3: placeholder, aria-label, alt
  content = content.replace(/placeholder="([^"]{4,})"/g, (match, value) => {
    if (!isTranslatableString(value) || value.includes('{') || value.includes('`')) return match;
    const key = getOrCreateKey(domain, value, 'placeholder');
    modified = true;
    return `placeholder={t('${key}')}`;
  });

  content = content.replace(/aria-label="([^"]{4,})"/g, (match, value) => {
    if (!isTranslatableString(value) || value.includes('{') || value.includes('`')) return match;
    const key = getOrCreateKey(domain, value, 'ariaLabel');
    modified = true;
    return `aria-label={t('${key}')}`;
  });

  // Pattern 4: toast messages (handle escaped quotes)
  content = content.replace(
    /toast\.(success|error|info|warning)\(\s*"((?:[^"\\]|\\.){4,})"\s*\)/g,
    (match, type, message) => {
      const cleanMsg = message.replace(/\\'/g, "'").replace(/\\"/g, '"');
      if (!isTranslatableString(cleanMsg)) return match;
      const key = getOrCreateKey(domain, cleanMsg, type === 'error' ? 'error' : type === 'success' ? 'success' : '');
      modified = true;
      return `toast.${type}(t('${key}'))`;
    }
  );
  content = content.replace(
    /toast\.(success|error|info|warning)\(\s*'((?:[^'\\]|\\.){4,})'\s*\)/g,
    (match, type, message) => {
      const cleanMsg = message.replace(/\\'/g, "'").replace(/\\"/g, '"');
      if (!isTranslatableString(cleanMsg)) return match;
      const key = getOrCreateKey(domain, cleanMsg, type === 'error' ? 'error' : type === 'success' ? 'success' : '');
      modified = true;
      return `toast.${type}(t('${key}'))`;
    }
  );

  // Pattern 5: title="Something"
  content = content.replace(/title="([A-Z][^"]{3,})"/g, (match, value) => {
    if (!isTranslatableString(value) || value.includes('{') || value.includes('`') || value.includes('$')) return match;
    const key = getOrCreateKey(domain, value);
    modified = true;
    return `title={t('${key}')}`;
  });

  // Pattern 6: label/description/title/message in objects
  // Handle escaped quotes in single-quoted strings with (?:[^'\\]|\\.)+ pattern
  for (const prop of ['label', 'description', 'title', 'message', 'action']) {
    // Double-quoted strings
    const dblRegex = new RegExp(`${prop}:\\s*"((?:[^"\\\\]|\\\\.){3,})"`, 'g');
    content = content.replace(dblRegex, (match, value) => {
      if (!/^[A-Z]/.test(value)) return match;
      if (!isTranslatableString(value) || value.includes('{') || value.includes('${')) return match;
      const cleanValue = value.replace(/\\'/g, "'").replace(/\\"/g, '"');
      const key = getOrCreateKey(domain, cleanValue);
      modified = true;
      return `${prop}: t('${key}')`;
    });
    // Single-quoted strings (handles escaped apostrophes like \')
    const sglRegex = new RegExp(`${prop}:\\s*'((?:[^'\\\\]|\\\\.){3,})'`, 'g');
    content = content.replace(sglRegex, (match, value) => {
      if (!/^[A-Z]/.test(value)) return match;
      if (!isTranslatableString(value) || value.includes('{')) return match;
      const cleanValue = value.replace(/\\'/g, "'").replace(/\\"/g, '"');
      const key = getOrCreateKey(domain, cleanValue);
      modified = true;
      return `${prop}: t('${key}')`;
    });
  }

  // Pattern 7: Remaining uppercase-starting JSX text
  content = content.replace(
    />([\s]*)((?:[A-Z][a-zA-Z'']+(?:[\s,\-–-&/]+[a-zA-Z'']+)*))(\s*)</g,
    (match, pre, text, post, offset) => {
      if (isInTypeContext(content, offset)) return match;
      const trimmed = text.trim();
      if (!isTranslatableString(trimmed)) return match;
      if (trimmed.includes('{') || trimmed.includes('}')) return match;
      if (match.includes("t('")) return match;
      const key = getOrCreateKey(domain, trimmed);
      modified = true;
      return `>${pre}{t('${key}')}${post}<`;
    }
  );

  if (!modified) {
    console.log(`SKIP (no translatable strings): ${relFile}`);
    continue;
  }

  // Now safely add import and hook
  // Step 1: Add import - find the last line that starts with "import " and add after it
  if (!content.includes('useTranslation')) {
    const lines = content.split('\n');
    let lastImportLine = -1;
    let inMultilineImport = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('import ')) {
        lastImportLine = i;
        // Check if it's a multi-line import
        if (line.includes('{') && !line.includes('}')) {
          inMultilineImport = true;
        }
      }
      if (inMultilineImport && line.includes('}')) {
        lastImportLine = i;
        inMultilineImport = false;
      }
      // Stop looking after we hit non-import code
      if (!inMultilineImport && lastImportLine >= 0 && !line.startsWith('import ') && line !== '' && !line.startsWith('//') && !line.startsWith('*') && !line.startsWith('/*') && !line.startsWith('}')) {
        break;
      }
    }

    if (lastImportLine >= 0) {
      // Determine relative path to i18n
      const fileDir = path.dirname(filePath);
      const i18nDir = path.join(SRC_DIR, 'i18n');
      let relI18n = path.relative(fileDir, i18nDir);
      if (!relI18n.startsWith('.')) relI18n = './' + relI18n;

      lines.splice(lastImportLine + 1, 0, `import { useTranslation } from '${relI18n}'`);
      content = lines.join('\n');
    }
  }

  // Step 2: Add hook call - find the main component function
  if (!content.includes('useTranslation()')) {
    // Find "export default function X(" or "export function X(" or standalone function
    const hookPatterns = [
      /^(export\s+default\s+function\s+\w+\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{)/m,
      /^(export\s+function\s+\w+\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{)/m,
      /^(function\s+[A-Z]\w*\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{)/m,
    ];

    let inserted = false;
    for (const pat of hookPatterns) {
      const match = pat.exec(content);
      if (match) {
        const insertIdx = match.index + match[0].length;
        content = content.substring(0, insertIdx) +
          '\n  const { t } = useTranslation()' +
          content.substring(insertIdx);
        inserted = true;
        break;
      }
    }

    // If no match, try arrow functions
    if (!inserted) {
      const arrowMatch = /^((?:export\s+)?const\s+[A-Z]\w*\s*=\s*(?:\([^)]*\)|[^=]+)\s*=>\s*\{)/m.exec(content);
      if (arrowMatch) {
        const insertIdx = arrowMatch.index + arrowMatch[0].length;
        content = content.substring(0, insertIdx) +
          '\n  const { t } = useTranslation()' +
          content.substring(insertIdx);
      }
    }
  }

  fs.writeFileSync(filePath, content, 'utf-8');
  modifiedCount++;
  console.log(`FIXED: ${relFile}`);
}

// Merge new translations
function deepMerge(target, source) {
  for (const [key, value] of Object.entries(source)) {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      if (!target[key] || typeof target[key] !== 'object') target[key] = {};
      deepMerge(target[key], value);
    } else {
      if (!target[key]) target[key] = value;
    }
  }
}

deepMerge(existingTranslations, newTranslations);
fs.writeFileSync(EN_JSON_PATH, JSON.stringify(existingTranslations, null, 2) + '\n', 'utf-8');

console.log(`\nFixed ${modifiedCount} files`);
function countKeys(obj) {
  let count = 0;
  for (const val of Object.values(obj)) {
    if (typeof val === 'string') count++;
    else if (typeof val === 'object' && val !== null) count += countKeys(val);
  }
  return count;
}
console.log(`New keys added: ${countKeys(newTranslations)}`);
