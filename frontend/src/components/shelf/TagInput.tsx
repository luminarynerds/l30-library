/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef } from 'react'
import { X } from 'lucide-react'
import { t } from '@/i18n'

interface TagInputProps {
  tags: string[]
  allTags: string[]
  onChange: (tags: string[]) => void
  maxTags?: number
  maxLength?: number
}

export default function TagInput({
  tags,
  allTags,
  onChange,
  maxTags = 10,
  maxLength = 30,
}: TagInputProps) {
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const suggestions = input.length > 0
    ? allTags.filter(
        (t) => t.toLowerCase().includes(input.toLowerCase()) && !tags.includes(t),
      ).slice(0, 5)
    : []

  const addTag = (tag: string) => {
    const trimmed = tag.trim().slice(0, maxLength)
    if (!trimmed || tags.includes(trimmed) || tags.length >= maxTags) return
    onChange([...tags, trimmed])
    setInput('')
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (suggestions.length > 0) {
        addTag(suggestions[0]!)
      } else if (input.trim()) {
        addTag(input)
      }
    } else if (e.key === 'Backspace' && !input && tags.length > 0) {
      removeTag(tags[tags.length - 1]!)
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  // Chip colors (cycle through palette)
  const chipColors = [
    'bg-status-info-100 dark:bg-status-info-900/40 text-status-info-700 dark:text-status-info-300',
    'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300',
    'bg-category-100 dark:bg-category-900/40 text-category-700 dark:text-category-300',
    'bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300',
    'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300',
    'bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300',
  ]

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-1.5">
        {tags.map((tag, i) => (
          <span
            key={tag}
            className={`inline-flex items-center gap-0.5 text-xs px-2 py-0.5 rounded-full ${chipColors[i % chipColors.length]}`}
          >
            {tag}
            <button
              onClick={() => removeTag(tag)}
              aria-label={`Remove tag ${tag}`}
              className="hover:opacity-70 transition-opacity"
            >
              <X className="w-3 h-3" aria-hidden="true" />
            </button>
          </span>
        ))}
        {tags.length < maxTags && (
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              setShowSuggestions(true)
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            onKeyDown={handleKeyDown}
            placeholder={tags.length === 0 ? 'Add tag...' : ''}
            maxLength={maxLength}
            aria-label={t('aria.shelf.addATag')}
            className="flex-1 min-w-[60px] text-xs bg-transparent text-lsc-dark dark:text-lsc-cream outline-none placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40"
          />
        )}
      </div>

      {/* Autocomplete dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <ul className="absolute left-0 top-full mt-1 z-20 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg shadow-lg py-1 min-w-[140px]">
          {suggestions.map((s) => (
            <li key={s}>
              <button
                onMouseDown={(e) => { e.preventDefault(); addTag(s) }}
                className="w-full text-left px-3 py-1.5 text-xs text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700"
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
