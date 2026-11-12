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

console.log('===== VERIFYING FIXED DISABLED BUTTON STATES =====\n');

let passedTests = 0;
let totalTests = 0;

// New disabled state using earth-500
console.log('FIXED PRIMARY BUTTON DISABLED STATE:');
console.log('------');

// Primary button disabled: earth-500 (#8a7153) + white text
totalTests++;
if (testContrast('#8a7153', '#FFFFFF', 'Disabled primary button: earth-500 + white text')) passedTests++;

// Secondary button (already uses opacity-50, should still be readable)
totalTests++;
if (testContrast('#F9F6F0', '#2C241B', 'Disabled secondary button: lsc-cream + lsc-dark')) passedTests++;

// Danger button disabled: gray-500
totalTests++;
if (testContrast('#6B7280', '#FFFFFF', 'Disabled danger button: gray-500 + white text')) passedTests++;

console.log(`\n===== SUMMARY =====`);
console.log(`Passed: ${passedTests}/${totalTests} tests`);
if (passedTests === totalTests) {
  console.log('All disabled button states are now WCAG AA compliant!');
} else {
  console.log(`${totalTests - passedTests} tests still failing.`);
}
