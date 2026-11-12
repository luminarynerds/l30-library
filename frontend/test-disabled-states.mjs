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

console.log('===== TESTING DISABLED BUTTON STATES =====\n');

let passedTests = 0;
let totalTests = 0;

// When a button is disabled with opacity-50, the color becomes a mix of the button color and the background
// For lsc-orange (#9e5a2d) with 50% opacity on white = rgba becomes approximately #cfb0a1
// white text on disabled orange button

console.log('DISABLED BUTTON STATES (50% opacity):');
console.log('------');

// lsc-orange with 50% opacity on white background
totalTests++;
if (testContrast('#cfb0a1', '#FFFFFF', 'Disabled lsc-orange button with white text (50% opacity)')) passedTests++;

// lsc-orange with 50% opacity on dark background
totalTests++;
if (testContrast('#5a3b22', '#FFFFFF', 'Disabled lsc-orange button on dark bg with white text (50% opacity)')) passedTests++;

// blue button disabled state
totalTests++;
if (testContrast('#c0d9ef', '#FFFFFF', 'Disabled blue-600 button with white text (50% opacity)')) passedTests++;

// red button disabled state
totalTests++;
if (testContrast('#f0cccf', '#FFFFFF', 'Disabled red-600 button with white text (50% opacity)')) passedTests++;

console.log(`\n===== SUMMARY =====`);
console.log(`Passed: ${passedTests}/${totalTests} tests`);
if (passedTests === totalTests) {
  console.log('All disabled button states are accessible!');
} else {
  console.log(`${totalTests - passedTests} tests failing. May need to darken disabled button colors.`);
}
