/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTemplateFromProgram } from '@/api/program-planning-api'
import { getEvents, type Event } from '@/api/events-api'
import { X, Search, Copy, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import FocusTrap from 'focus-trap-react'

function CopyFromProgramModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    return () => { previousActiveElement.current?.focus() }
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProgram, setSelectedProgram] = useState<{ id: number; title: string; date: string; category: string | null } | null>(null)
  const [showDropdown, setShowDropdown] = useState(false)
  const [searchResults, setSearchResults] = useState<Event[]>([])
  const [searching, setSearching] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Click-outside detection
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }
    setSearching(true)
    const timer = setTimeout(async () => {
      try {
        const result = await getEvents({ search: searchQuery.trim(), upcoming: false, per_page: 15 })
        setSearchResults(result.data)
        setShowDropdown(true)
      } catch {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
    return () => { clearTimeout(timer); setSearching(false) }
  }, [searchQuery])

  const copyMutation = useMutation({
    mutationFn: () => createTemplateFromProgram(selectedProgram!.id, templateName),
    onSuccess: () => {
      toast.success(t('programPlanning.templateCreatedFromProgram'))
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
      onClose()
    },
    onError: () => toast.error(t('programPlanning.failedToCreateTemplateFrom')),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProgram) return
    copyMutation.mutate()
  }

  const handleSelectProgram = (event: Event) => {
    setSelectedProgram({
      id: event.id,
      title: event.title,
      date: event.start_time,
      category: event.category ?? null,
    })
    setSearchQuery('')
    setShowDropdown(false)
    setSearchResults([])
  }

  const handleClearSelection = () => {
    setSelectedProgram(null)
    setTimeout(() => searchInputRef.current?.focus(), 0)
  }

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
    } catch {
      return iso
    }
  }

  return (
    <FocusTrap
      focusTrapOptions={{
        allowOutsideClick: false,
        escapeDeactivates: false,
        returnFocusOnDeactivate: true,
      }}
    >
    <div
      className="fixed inset-0 z-50"
      role="presentation"
      onKeyDown={handleKeyDown}
    >
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" onClick={onClose} />
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="copy-from-program-title"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-md"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
          <h2 id="copy-from-program-title" className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">{t('programPlanning.copyFromPastProgram')}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-earth-100 dark:hover:bg-earth-700">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Create a template from a successful past program. Budget, supplies, and marketing timeline will be copied.
          </p>
          <div ref={dropdownRef} className="relative">
            <label htmlFor="copy-program-search" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Program *</label>
            {selectedProgram ? (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900">
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate block">{selectedProgram.title}</span>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    {formatDate(selectedProgram.date)}
                    {selectedProgram.category && ` · ${selectedProgram.category}`}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleClearSelection}
                  className="p-0.5 rounded hover:bg-earth-200 dark:hover:bg-earth-700 flex-shrink-0"
                  aria-label="Clear selected program"
                >
                  <X className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                </button>
              </div>
            ) : (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/40 pointer-events-none" />
                  <input
                    id="copy-program-search"
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onFocus={() => { if (searchResults.length) setShowDropdown(true) }}
                    placeholder="Search past programs..."
                    autoComplete="off"
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                  {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/40" />}
                </div>
                {showDropdown && (
                  <ul
                    role="listbox"
                    aria-live="polite"
                    className="absolute left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 shadow-lg z-10"
                  >
                    {searchResults.length === 0 ? (
                      <li className="px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/50">No programs found</li>
                    ) : (
                      searchResults.map(ev => (
                        <li
                          key={ev.id}
                          role="option"
                          aria-selected={false}
                          tabIndex={0}
                          onClick={() => handleSelectProgram(ev)}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelectProgram(ev) } }}
                          className="px-3 py-2 cursor-pointer hover:bg-earth-100 dark:hover:bg-earth-700 border-b last:border-b-0 border-earth-100 dark:border-earth-800"
                        >
                          <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream block truncate">{ev.title}</span>
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                            {formatDate(ev.start_time)}
                            {ev.category && ` · ${ev.category}`}
                          </span>
                        </li>
                      ))
                    )}
                  </ul>
                )}
              </>
            )}
          </div>
          <div>
            <label htmlFor="copy-template-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Template Name *</label>
            <input
              id="copy-template-name"
              type="text"
              required
              value={templateName}
              onChange={e => setTemplateName(e.target.value)}
              placeholder={t('placeholder.programPlanning.egSummerReading2026')}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedProgram || !templateName.trim() || copyMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-600 text-white hover:bg-earth-700 disabled:opacity-50"
            >
              {copyMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              <Copy className="w-4 h-4" />
              Create Template
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>
    </FocusTrap>
  )
}

export default CopyFromProgramModal
