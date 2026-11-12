/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import {
  Loader2,
  CheckCircle2,
  Plus,
  X,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  updateMyReadingPreferences,
  type HomeDeliveryEnrollment,
} from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import { clean } from "@/lib/utils"
import { GENRE_OPTIONS } from "./types"

export function PreferencesTab({ enrollment }: { enrollment: HomeDeliveryEnrollment }) {
  const { t } = useTranslation()
  const prefs = enrollment.reading_preferences
  const [selectedGenres, setSelectedGenres] = useState<string[]>(prefs?.preferred_genres || [])
  const [excludedGenres, setExcludedGenres] = useState<string[]>(prefs?.excluded_genres || [])
  const [favoriteAuthors, setFavoriteAuthors] = useState<string[]>(prefs?.favorite_authors || [])
  const [authorInput, setAuthorInput] = useState("")
  const [fictionPref, setFictionPref] = useState(prefs?.fiction_preference ?? 50)
  const [contentRating, setContentRating] = useState(prefs?.content_rating || "adult")
  const [largePrint, setLargePrint] = useState(prefs?.prefers_large_print || false)
  const [audiobooks, setAudiobooks] = useState(prefs?.prefers_audiobooks || false)
  const [shortBooks, setShortBooks] = useState(prefs?.prefers_short_books || false)
  const [notes, setNotes] = useState(prefs?.notes || "")
  const [saving, setSaving] = useState(false)

  const inputCls = "w-full px-3 py-2 border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-sage/50 focus:border-sage min-h-[44px]"

  function toggleGenre(genre: string, list: string[], setter: (v: string[]) => void) {
    setter(list.includes(genre) ? list.filter(g => g !== genre) : [...list, genre])
  }

  function addAuthor() {
    const trimmed = authorInput.trim()
    if (trimmed && !favoriteAuthors.includes(trimmed)) {
      setFavoriteAuthors([...favoriteAuthors, trimmed])
    }
    setAuthorInput("")
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await updateMyReadingPreferences(clean({
        preferred_genres: selectedGenres,
        excluded_genres: excludedGenres,
        favorite_authors: favoriteAuthors,
        fiction_preference: fictionPref,
        content_rating: contentRating,
        prefers_large_print: largePrint,
        prefers_audiobooks: audiobooks,
        prefers_short_books: shortBooks,
        notes: notes.trim() || undefined,
      }))
      toast.success(t('toast.readingPreferences.readingPreferencesSaved'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.readingPreferences.failedToSavePreferences'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Preferred Genres */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Preferred Genres</h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">{t("patronHomeDelivery.selectGenresYouEnjoyReading")}</p>
        <div className="flex flex-wrap gap-2">
          {GENRE_OPTIONS.map(g => (
            <button
              key={g}
              type="button"
              onClick={() => toggleGenre(g, selectedGenres, setSelectedGenres)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors min-h-[36px] ${
                selectedGenres.includes(g)
                  ? "bg-sage text-white border-sage"
                  : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-sage/30 dark:border-earth-600 hover:border-sage"
              }`}
              aria-pressed={selectedGenres.includes(g)}
              aria-label={`${g} genre`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Excluded Genres */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Excluded Genres</h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">{t("patronHomeDelivery.selectGenresYouWantTo")}</p>
        <div className="flex flex-wrap gap-2">
          {GENRE_OPTIONS.map(g => (
            <button
              key={g}
              type="button"
              onClick={() => toggleGenre(g, excludedGenres, setExcludedGenres)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors min-h-[36px] ${
                excludedGenres.includes(g)
                  ? "bg-status-danger-600 text-white border-status-danger-600"
                  : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-sage/30 dark:border-earth-600 hover:border-status-danger-400"
              }`}
              aria-pressed={excludedGenres.includes(g)}
              aria-label={`Exclude ${g}`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {/* Favorite Authors */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Favorite Authors</h2>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={authorInput}
            onChange={e => setAuthorInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addAuthor() } }}
            className={inputCls}
            placeholder={t("patronHomeDelivery.typeAnAuthorNameAnd")}
            aria-label={t('aria.readingPreferences.addFavoriteAuthor')}
          />
          <button
            type="button"
            onClick={addAuthor}
            className="bg-sage text-white px-4 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors min-h-[44px] shrink-0"
            aria-label={t('aria.readingPreferences.addAuthor')}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
        {favoriteAuthors.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {favoriteAuthors.map(a => (
              <span key={a} className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-sage/10 dark:bg-sage/20 text-sm text-sage font-medium">
                {a}
                <button
                  type="button"
                  onClick={() => setFavoriteAuthors(favoriteAuthors.filter(x => x !== a))}
                  className="hover:text-status-danger-600 min-w-[20px] min-h-[20px] flex items-center justify-center"
                  aria-label={`Remove ${a}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Fiction / Nonfiction Slider + Content Rating */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6 space-y-5">
        <div>
          <label htmlFor="pref-fiction" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            Fiction vs. Nonfiction Preference
          </label>
          <div className="flex items-center gap-3">
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 w-20 text-right">Nonfiction</span>
            <input
              id="pref-fiction"
              type="range"
              min={0}
              max={100}
              value={fictionPref}
              onChange={e => setFictionPref(Number(e.target.value))}
              className="flex-1 accent-sage"
              aria-label={`Fiction preference: ${fictionPref}%`}
            />
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 w-20">Fiction</span>
          </div>
          <p className="text-center text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
            {fictionPref}% fiction / {100 - fictionPref}% nonfiction
          </p>
        </div>

        <div>
          <label htmlFor="pref-rating" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Content Rating</label>
          <select id="pref-rating" value={contentRating} onChange={e => setContentRating(e.target.value)} className={inputCls}>
            <option value="children">Children</option>
            <option value="young_adult">Young Adult</option>
            <option value="adult">Adult</option>
            <option value="any">Any</option>
          </select>
        </div>
      </div>

      {/* Format toggles */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Format Preferences</h2>
        <div className="space-y-3">
          {[
            { id: "pref-large", label: "Large print books", checked: largePrint, setter: setLargePrint },
            { id: "pref-audio", label: "Audiobooks", checked: audiobooks, setter: setAudiobooks },
            { id: "pref-short", label: t("patronHomeDelivery.shortBooksUnderPages"), checked: shortBooks, setter: setShortBooks },
          ].map(opt => (
            <label key={opt.id} className="flex items-center gap-3 cursor-pointer min-h-[44px]">
              <input
                id={opt.id}
                type="checkbox"
                checked={opt.checked}
                onChange={e => opt.setter(e.target.checked)}
                className="w-5 h-5 rounded border-sage/30 text-sage focus:ring-sage"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
        <label htmlFor="pref-notes" className="block text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Additional Notes</label>
        <textarea
          id="pref-notes"
          value={notes}
          onChange={e => setNotes(e.target.value)}
          className={`${inputCls} min-h-[80px]`}
          placeholder={t("patronHomeDelivery.anythingElseWeShouldKnow")}
        />
      </div>

      <button
        type="submit"
        disabled={saving}
        className="bg-sage text-white px-6 py-3 rounded-lg font-medium hover:bg-sage/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] flex items-center gap-2"
        aria-label={t('aria.readingPreferences.saveReadingPreferences')}
      >
        {saving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
        {saving ? "Saving..." : "Save Preferences"}
      </button>
    </form>
  )
}
