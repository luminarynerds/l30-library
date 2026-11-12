/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Accessibility Testing Utilities
 *
 * This module provides utilities for automated accessibility testing
 * using jest-axe (axe-core) integration with Vitest.
 *
 * Usage:
 * ```tsx
 * import { testAccessibility } from '../utils/accessibility'
 *
 * it('should have no accessibility violations', async () => {
 *   const { container } = render(<MyComponent />)
 *   await testAccessibility(container)
 * })
 * ```
 */

import { axe, JestAxeConfigureOptions } from 'jest-axe'
import { expect } from 'vitest'

// Note: toHaveNoViolations matcher is extended in setup.ts

// Default axe configuration for our project
const defaultAxeConfig: JestAxeConfigureOptions = {
  rules: {
    // Disable rules that may conflict with our UI patterns
    // 'color-contrast': { enabled: false }, // Uncomment if contrast checks cause issues
    'region': { enabled: true }, // Ensure content is in landmark regions
  },
}

export async function testAccessibility(
  container: Element,
  options?: JestAxeConfigureOptions
): Promise<void> {
  const config = { ...defaultAxeConfig, ...options }
  const results = await axe(container, config)
  expect(results).toHaveNoViolations()
}

export async function getAccessibilityResults(container: Element) {
  return await axe(container, defaultAxeConfig)
}

/**
 * Common accessibility test patterns
 */
export const a11yPatterns = {
  /**
   * Test that interactive elements are keyboard accessible
   */
  hasKeyboardAccess: (element: Element) => {
    const tabIndex = element.getAttribute('tabindex')
    const isNativelyFocusable = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(element.tagName)
    return isNativelyFocusable || (tabIndex !== null && tabIndex !== '-1')
  },

  /**
   * Test that an element has an accessible name
   */
  hasAccessibleName: (element: Element) => {
    const ariaLabel = element.getAttribute('aria-label')
    const ariaLabelledBy = element.getAttribute('aria-labelledby')
    const title = element.getAttribute('title')
    const textContent = element.textContent?.trim()
    return !!(ariaLabel || ariaLabelledBy || title || textContent)
  },

  /**
   * Test that a dialog has proper ARIA attributes
   */
  isAccessibleDialog: (element: Element) => {
    const role = element.getAttribute('role')
    const ariaModal = element.getAttribute('aria-modal')
    const ariaLabelledBy = element.getAttribute('aria-labelledby')
    return role === 'dialog' && ariaModal === 'true' && !!ariaLabelledBy
  },
}
