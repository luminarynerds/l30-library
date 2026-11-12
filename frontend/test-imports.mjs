/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Test that all components and hooks can be imported
import('src/features/accessibility/components/index.ts').then(() => {
  console.log('Components imported successfully')
}).catch(err => {
  console.error('Component import failed:', err.message)
  process.exit(1)
})

import('src/features/accessibility/hooks/index.ts').then(() => {
  console.log('Hooks imported successfully')
}).catch(err => {
  console.error('Hook import failed:', err.message)
  process.exit(1)
})
