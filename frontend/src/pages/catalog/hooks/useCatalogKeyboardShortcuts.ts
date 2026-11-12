/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, type RefObject } from 'react'
import { stopSpeaking } from '@/pages/catalog/utils/catalogTextToSpeech'

interface Params {
  searchInputRef: RefObject<HTMLInputElement | null>
  isDrawerOpen: boolean
  setIsDrawerOpen: (next: boolean | ((prev: boolean) => boolean)) => void
  simplifiedView: boolean
  setSimplifiedView: (next: boolean | ((prev: boolean) => boolean)) => void
  setSpeakingItemId: (id: number | null) => void
  quietMode: boolean
  updateA11ySetting: (key: 'quietMode', value: boolean) => void
  reduceMotion: boolean
  announceToScreenReader: (message: string) => void
  /** WCAG 2.1.4 opt-out: when false, no single-key shortcuts are bound. */
  shortcutsEnabled: boolean
}

export function useCatalogKeyboardShortcuts({
  searchInputRef,
  isDrawerOpen,
  setIsDrawerOpen,
  simplifiedView,
  setSimplifiedView,
  setSpeakingItemId,
  quietMode,
  updateA11ySetting,
  announceToScreenReader,
  reduceMotion,
  shortcutsEnabled,
}: Params): void {
  const simplifiedViewRef = useRef(simplifiedView)
  const announceRef = useRef(announceToScreenReader)
  const isDrawerOpenRef = useRef(isDrawerOpen)

  useEffect(() => { simplifiedViewRef.current = simplifiedView }, [simplifiedView])
  useEffect(() => { announceRef.current = announceToScreenReader }, [announceToScreenReader])
  useEffect(() => { isDrawerOpenRef.current = isDrawerOpen }, [isDrawerOpen])

  useEffect(() => {
    if (!shortcutsEnabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target
      if (
        target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target instanceof HTMLSelectElement
        || (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return
      }

      switch (e.key) {
        case '/':
          e.preventDefault()
          searchInputRef.current?.focus()
          announceRef.current('Search field focused')
          break
        case 'f':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault()
            if (window.innerWidth <= 1024) {
              setIsDrawerOpen(prev => !prev)
            } else {
              // Locale-independent target: aria-labels are translated, so we
              // anchor on a data attribute instead (CatalogFilterSidebar).
              document.querySelector('[data-catalog-filters]')?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
            }
            announceRef.current('Filters focused')
          }
          break
        case 'q':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault()
            updateA11ySetting('quietMode', !quietMode)
            announceRef.current(quietMode ? 'Quiet mode off' : 'Quiet mode on')
          }
          break
        case 'Escape':
          if (isDrawerOpenRef.current) {
            setIsDrawerOpen(false)
            announceRef.current('Filters hidden')
          }
          stopSpeaking()
          setSpeakingItemId(null)
          break
        case 's':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault()
            setSimplifiedView(prev => !prev)
            announceRef.current(simplifiedViewRef.current ? 'Full view enabled' : 'Simplified view enabled')
          }
          break
        case '?': {
          e.preventDefault()
          // Locale-independent target (CatalogSearchBar's KeyboardShortcutHelp).
          const helpBtn = document.querySelector('[data-keyboard-shortcuts-help]') as HTMLButtonElement | null
          helpBtn?.click()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quietMode, shortcutsEnabled])
}
