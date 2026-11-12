/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
const wcag = require('wcag-contrast');

function testContrast(bgHex, fgHex, description) {
  const ratio = wcag.score(bgHex, fgHex);
  const pass = ratio >= 4.5 ? 'PASS' : 'FAIL';
  console.log(`${description}`);
  console.log(`  BG: ${bgHex}, FG: ${fgHex}`);
  console.log(`  Ratio: ${ratio.toFixed(2)}:1 ${pass === 'PASS' ? 'PASS' : 'FAIL'}`);
  console.log('');
  return ratio;
}

console.log('===== EXTERNALRESOURCECARD TESTS =====\n');

console.log('DIFFICULTY COLORS - LIGHT MODE');
console.log('------');
testContrast('#F0FDF4', '#15803d', 'bg-green-100 + text-green-700 (beginner)');
testContrast('#EFF6FF', '#1d4ED8', 'bg-blue-100 + text-blue-700 (intermediate)');
testContrast('#FAF5FF', '#6D28D9', 'bg-purple-100 + text-purple-700 (advanced)');

console.log('DIFFICULTY COLORS - DARK MODE');
console.log('------');
// dark:bg-green-900/30 on #2a2420 = #1f2e1d
testContrast('#1f2e1d', '#86EFAC', 'dark:bg-green-900/30 + dark:text-green-300 (beginner)');
// dark:bg-blue-900/30 on #2a2420 = #1e2c46
testContrast('#1e2c46', '#93C5FD', 'dark:bg-blue-900/30 + dark:text-blue-300 (intermediate)');
// dark:bg-purple-900/30 on #2a2420 = #27174a
testContrast('#27174a', '#D8B4FE', 'dark:bg-purple-900/30 + dark:text-purple-300 (advanced)');

console.log('\nTOPIC COLORS - LIGHT MODE (sampling)');
console.log('------');
testContrast('#FFEDD5', '#B45309', 'bg-orange-100 + text-orange-700 (AI)');
testContrast('#FCE7F3', '#BE185D', 'bg-pink-100 + text-pink-700 (Ethics)');
testContrast('#ECFDFD', '#0E7490', 'bg-cyan-100 + text-cyan-700 (Data Management)');
testContrast('#EDE9FE', '#4338CA', 'bg-indigo-100 + text-indigo-700 (Governance)');
testContrast('#FEF3C7', '#B45309', 'bg-amber-100 + text-amber-700 (Leadership)');
testContrast('#FEE2E2', '#B91C1C', 'bg-red-100 + text-red-700 (Data Visualization)');
testContrast('#FEFCE8', '#A16207', 'bg-yellow-100 + text-yellow-700 (Privacy)');
testContrast('#F7FEE7', '#4ADE80', 'bg-lime-100 + text-lime-700 (Application)');
testContrast('#F0FDFA', '#0D9488', 'bg-teal-100 + text-teal-700 (Partnerships)');
testContrast('#FAE8FF', '#A21CAF', 'bg-fuchsia-100 + text-fuchsia-700 (Talent)');
testContrast('#F5F3FF', '#6D28D9', 'bg-violet-100 + text-violet-700 (Quality)');

console.log('\nTOPIC COLORS - DARK MODE (sampling)');
console.log('------');
testContrast('#44240b', '#FEDBA9', 'dark:bg-orange-900/30 + dark:text-orange-300 (AI)');
testContrast('#42132b', '#F685BA', 'dark:bg-pink-900/30 + dark:text-pink-300 (Ethics)');
testContrast('#083d44', '#06B6D4', 'dark:bg-cyan-900/30 + dark:text-cyan-300 (Data Management)');

console.log('\n===== EXTERNALRESOURCECARD TEXT & TAG COLORS =====\n');
testContrast('#FFFFFF', '#4B5563', 'text-gray-600 on white (provider)');
testContrast('#FFFFFF', '#374151', 'text-gray-700 on white (description)');
testContrast('#2a2420', '#9CA3AF', 'dark:text-gray-400 on dark bg (#2a2420)');
testContrast('#2a2420', '#D1D5DB', 'dark:text-gray-300 on dark bg (#2a2420)');
testContrast('#F3F4F6', '#374151', 'bg-gray-100 + text-gray-700 (resource type)');
testContrast('#1F2937', '#D1D5DB', 'dark:bg-gray-800 + dark:text-gray-300 (resource type)');

console.log('\n===== PROGRAMCARD TESTS =====\n');
testContrast('#FFFFFF', '#9e5a2d', 'text-lsc-orange on white (featured badge)');
testContrast('#2a2420', '#e9a466', 'dark:text-lsc-orange-light on dark bg (featured badge)');
testContrast('#F0FDF4', '#16A34A', 'bg-green-100 + text-green-600 (Joined badge)');
testContrast('#1f2e1d', '#4ADE80', 'dark:bg-green-900/30 + dark:text-green-400 (Joined badge)');
testContrast('#FFFFFF', '#6b5f58', 'text-lsc-dark/70 (70% opacity) on white (description)');
testContrast('#2a2420', '#f5f3f1', 'dark:text-lsc-cream/80 (80% opacity) on dark bg (description)');
testContrast('#FFFFFF', '#7a6f6a', 'text-lsc-dark/60 (60% opacity) on white (labels)');
testContrast('#2a2420', '#8b8780', 'dark:text-lsc-cream/60 (60% opacity) on dark bg (labels)');
testContrast('#FFFBEB', '#B45309', 'bg-amber-50 + text-amber-700 (urgency indicator)');
testContrast('#221d08', '#FBBF24', 'dark:bg-amber-900/20 + dark:text-amber-400 (urgency indicator)');
testContrast('#F9F6F0', '#7a6f6a', 'text-lsc-dark/60 on lsc-cream bg (info grid labels)');
testContrast('#9e5a2d', '#FFFFFF', 'bg-lsc-orange + text-white (join button)');

console.log('\n===== CUSTOM COLORS FROM TAILWIND.CONFIG =====\n');
testContrast('#FFFFFF', '#75644f', 'cream-600 on white');
testContrast('#FFFFFF', '#a38b6f', 'earth-400 on white');
testContrast('#FFFFFF', '#C67720', 'amber-600 on white');
testContrast('#FFFFFF', '#CC6339', 'kids-dark on white');
testContrast('#FFFFFF', '#4570A3', 'teen-dark on white');
testContrast('#FFFFFF', '#2f4a3d', 'staff-dark on white');
testContrast('#FFFFFF', '#5d4628', 'resources-dark on white');

console.log('\n===== BUTTON & INTERACTIVE STATES =====\n');
testContrast('#EFF6FF', '#1d4ED8', 'bg-blue-50 + text-blue-600 (button state)');
// blue-900/20 on #2a2420 = #1e2c46
testContrast('#1e2c46', '#60A5FA', 'dark:bg-blue-900/20 + dark:text-blue-400 (button state)');

console.log('\nTesting complete!');
