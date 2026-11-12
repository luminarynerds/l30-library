/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import wcag from 'wcag-contrast';

function testContrast(bgHex, fgHex, description) {
  const ratio = wcag.hex(bgHex, fgHex);
  const pass = ratio >= 4.5 ? 'PASS' : 'FAIL';
  const fixed = ratio.toFixed(2);
  console.log(`${description}: ${fixed}:1 [${pass}]`);
  return ratio >= 4.5;
}

console.log('===== VERIFYING FIXED COLOR COMBINATIONS =====\n');

let passedTests = 0;
let totalTests = 0;

console.log('FIXED VIOLATIONS:');
console.log('------');

totalTests++;
if (testContrast('#FFEDD5', '#92400e', 'AI topic: bg-orange-100 + text-orange-800')) passedTests++;

totalTests++;
if (testContrast('#F7FEE7', '#4b5809', 'Application topic: bg-lime-100 + text-lime-800')) passedTests++;

totalTests++;
if (testContrast('#F0FDFA', '#0d5d63', 'Partnerships topic: bg-teal-100 + text-teal-800')) passedTests++;

totalTests++;
if (testContrast('#F0FDF4', '#15803d', 'ProgramCard Joined badge: bg-green-100 + text-green-700')) passedTests++;

totalTests++;
if (testContrast('#2a2420', '#e0d5ce', 'ProgramCard progress label dark mode (80% opacity)')) passedTests++;

totalTests++;
if (testContrast('#F9F6F0', '#7a6f6a', 'ProgramCard info grid labels: text-lsc-dark/60 on lsc-cream')) passedTests++;

totalTests++;
if (testContrast('#2a2420', '#c8bfb8', 'ProgramCard info grid labels dark (70% opacity)')) passedTests++;

console.log('\n===== SUMMARY =====');
console.log(`Passed: ${passedTests}/${totalTests} tests`);
if (passedTests === totalTests) {
  console.log('All fixes verified! All colors now meet WCAG AA standards.');
} else {
  console.log(`${totalTests - passedTests} tests still failing.`);
}
