/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Enhanced Focus Trap Hook - WCAG 2.1 Compliant
 *
 * Traps keyboard focus within a container element, ensuring users
 * can only navigate within the designated area. Essential for
 * accessible modals, dialogs, and overlay components.
 *
 * Features:
 * - Automatic focus management with robust Tab cycling
 * - Return focus to trigger element
 * - Initial focus customization
 * - Escape key handler
 * - Compatible with screen readers
 * - Handles dynamic DOM changes
 * - WCAG 2.1 Level A compliant
 *
 * @example
 * ```tsx
 * const Modal = ({ isOpen, onClose }) => {
 *   const focusTrapRef = useFocusTrap<HTMLDivElement>({
 *     isActive: isOpen,
 *     initialFocus: true,
 *     restoreFocus: true,
 *     onEscape: onClose
 *   });
 *
 *   if (!isOpen) return null;
 *
 *   return (
 *     <div ref={focusTrapRef} role="dialog" aria-modal="true">
 *       <h2>Modal Title</h2>
 *       <button onClick={onClose}>Close</button>
 *     </div>
 *   );
 * };
 * ```
 */
import { useRef, useEffect, useCallback } from 'react'

const FOCUSABLE_ELEMENTS = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
  '[contenteditable="true"]',
].join(', ')

export interface FocusTrapOptions {
  /** Whether the focus trap is active */
  isActive?: boolean
  /** Auto-focus first element when trap activates */
  initialFocus?: boolean | string | (() => HTMLElement | null)
  /** Restore focus to previously focused element when trap deactivates */
  restoreFocus?: boolean
  /** Callback when Escape key is pressed */
  onEscape?: () => void
  /** Allow clicking outside to deactivate */
  clickOutsideDeactivates?: boolean
  /** Callback when clicking outside */
  onClickOutside?: () => void
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_ELEMENTS)
  ).filter((el) => {
    // Filter out hidden elements
    const style = window.getComputedStyle(el)
    return (
      style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      !el.hasAttribute('aria-hidden') &&
      el.offsetParent !== null // Also check if element is rendered
    )
  })
}

export function useFocusTrap<T extends HTMLElement = HTMLElement>(
  options: FocusTrapOptions = {}
) {
  const {
    isActive = true,
    initialFocus = true,
    restoreFocus = true,
    onEscape,
    clickOutsideDeactivates = false,
    onClickOutside,
  } = options

  const ref = useRef<T>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)
  const focusIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Store the previously focused element when trap activates
  useEffect(() => {
    if (isActive && restoreFocus) {
      previousActiveElement.current = document.activeElement as HTMLElement
    }
  }, [isActive, restoreFocus])

  // Handle initial focus
  useEffect(() => {
    if (!isActive || !ref.current) return

    const container = ref.current

    // Use requestAnimationFrame for more reliable timing
    const focusInitial = () => {
      if (!ref.current) return

      const focusableElements = getFocusableElements(container)

      if (focusableElements.length === 0) {
        // No focusable elements, focus the container itself
        if (container.tabIndex === -1) {
          container.tabIndex = 0
        }
        container.focus()
        return
      }

      if (!initialFocus) return

      // Determine which element to focus
      let elementToFocus: HTMLElement | null = null

      if (typeof initialFocus === 'function') {
        elementToFocus = initialFocus()
      } else if (typeof initialFocus === 'string') {
        elementToFocus = container.querySelector<HTMLElement>(initialFocus) || null
      } else if (initialFocus === true) {
        // Focus first focusable element, or element with autofocus
        const autofocusElement = container.querySelector<HTMLElement>('[autofocus]')
        elementToFocus = autofocusElement || focusableElements[0] || null
      }

      if (elementToFocus && typeof elementToFocus.focus === 'function') {
        elementToFocus.focus()
      }
    }

    // Use both setTimeout and requestAnimationFrame for maximum compatibility
    requestAnimationFrame(() => {
      setTimeout(focusInitial, 0)
    })
  }, [isActive, initialFocus])

  // Restore focus when trap deactivates
  useEffect(() => {
    return () => {
      if (
        restoreFocus &&
        previousActiveElement.current &&
        typeof previousActiveElement.current.focus === 'function'
      ) {
        // Use requestAnimationFrame for smoother focus restoration
        requestAnimationFrame(() => {
          previousActiveElement.current?.focus()
        })
      }
    }
  }, [restoreFocus])

  // CRITICAL FIX: Monitor focus and enforce containment
  useEffect(() => {
    if (!isActive || !ref.current) return

    const container = ref.current

    const enforceFocus = () => {
      if (!isActive || !container) return

      const activeElement = document.activeElement

      // If focus has escaped the container, bring it back
      if (activeElement && !container.contains(activeElement)) {
        const focusableElements = getFocusableElements(container)

        if (focusableElements.length > 0) {
          // Focus the first focusable element
          focusableElements[0]!.focus()
        } else if (container.tabIndex >= 0) {
          // If no focusable elements, focus container
          container.focus()
        }
      }
    }

    // Monitor focus changes - this is the critical fix
    focusIntervalRef.current = setInterval(enforceFocus, 100)

    return () => {
      if (focusIntervalRef.current) {
        clearInterval(focusIntervalRef.current)
      }
    }
  }, [isActive])

  // Handle Tab key for focus cycling - IMPROVED
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!isActive || !ref.current) return

      // Handle Escape key
      if (event.key === 'Escape' && onEscape) {
        event.preventDefault()
        onEscape()
        return
      }

      // Handle Tab key - CRITICAL FIX
      if (event.key === 'Tab') {
        const container = ref.current
        const focusableElements = getFocusableElements(container)

        if (focusableElements.length === 0) {
          // No focusable elements, prevent tabbing
          event.preventDefault()
          return
        }

        if (focusableElements.length === 1) {
          // Only one focusable element, prevent tabbing
          event.preventDefault()
          return
        }

        const firstElement = focusableElements[0]
        const lastElement = focusableElements[focusableElements.length - 1]
        const activeElement = document.activeElement as HTMLElement

        // Check if active element is in our container
        if (!container.contains(activeElement)) {
          event.preventDefault()
          firstElement!.focus()
          return
        }

        if (event.shiftKey) {
          // Shift + Tab: moving backwards
          if (activeElement === firstElement) {
            event.preventDefault()
            lastElement!.focus()
          }
        } else {
          // Tab: moving forwards
          if (activeElement === lastElement) {
            event.preventDefault()
            firstElement!.focus()
          }
        }
      }
    },
    [isActive, onEscape]
  )

  // Handle click outside
  const handleClickOutside = useCallback(
    (event: MouseEvent) => {
      if (
        !isActive ||
        !ref.current ||
        !clickOutsideDeactivates
      ) {
        return
      }

      if (!ref.current.contains(event.target as Node)) {
        onClickOutside?.()
      }
    },
    [isActive, clickOutsideDeactivates, onClickOutside]
  )

  // Set up event listeners
  useEffect(() => {
    if (!isActive) return

    // Use capture phase to ensure we catch the event before any children
    document.addEventListener('keydown', handleKeyDown, true)

    if (clickOutsideDeactivates) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown, true)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isActive, handleKeyDown, handleClickOutside, clickOutsideDeactivates])

  return ref
}

export function useRestoreFocus(isActive: boolean = true) {
  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (isActive) {
      previousActiveElement.current = document.activeElement as HTMLElement
    }

    return () => {
      if (
        isActive &&
        previousActiveElement.current &&
        typeof previousActiveElement.current.focus === 'function'
      ) {
        requestAnimationFrame(() => {
          previousActiveElement.current?.focus()
        })
      }
    }
  }, [isActive])

  return previousActiveElement
}

export function useFocusManagement<T extends HTMLElement = HTMLElement>() {
  const ref = useRef<T>(null)

  const focus = useCallback(() => {
    ref.current?.focus()
  }, [])

  const focusFirstFocusable = useCallback(() => {
    if (!ref.current) return

    const focusableElements = getFocusableElements(ref.current)
    const firstElement = focusableElements[0]
    if (firstElement) {
      firstElement.focus()
    }
  }, [])

  const focusLastFocusable = useCallback(() => {
    if (!ref.current) return

    const focusableElements = getFocusableElements(ref.current)
    const lastElement = focusableElements[focusableElements.length - 1]
    if (lastElement) {
      lastElement.focus()
    }
  }, [])

  return {
    ref,
    focus,
    focusFirstFocusable,
    focusLastFocusable,
  }
}
