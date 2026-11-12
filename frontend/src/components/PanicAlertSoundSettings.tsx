/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useRef, useState } from 'react'
import { Volume2, VolumeX, Play, Square, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { usePanicAlert } from '../contexts/PanicAlertContext'
import {
  useAlertAudio,
  ALERT_SOUND_OPTIONS,
  DEFAULT_ALERT_SOUND,
  type AlertSoundPreset,
} from '@/hooks/useAlertAudio'

const PREVIEW_MS = 2500

export function PanicAlertSoundSettings() {
  const { preferences, preferencesLoading, updatePreferences } = usePanicAlert()
  const [draft, setDraft] = useState<AlertSoundPreset>(DEFAULT_ALERT_SOUND)
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [previewing, setPreviewing] = useState<AlertSoundPreset | null>(null)
  const [saving, setSaving] = useState(false)
  const previewTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { start: startPreview, stop: stopPreview } = useAlertAudio({
    preset: previewing ?? draft,
  })

  useEffect(() => {
    if (preferences) {
      setDraft(
        (preferences.sound_preference as AlertSoundPreset | undefined) ??
          DEFAULT_ALERT_SOUND,
      )
      setSoundEnabled(preferences.sound_enabled)
    }
  }, [preferences])

  useEffect(() => {
    return () => {
      if (previewTimeoutRef.current) clearTimeout(previewTimeoutRef.current)
      stopPreview()
    }
  }, [stopPreview])

  const isDirty =
    !!preferences &&
    (preferences.sound_preference !== draft ||
      preferences.sound_enabled !== soundEnabled)

  const handlePreview = (preset: AlertSoundPreset) => {
    if (previewing === preset) {
      stopPreview()
      setPreviewing(null)
      if (previewTimeoutRef.current) clearTimeout(previewTimeoutRef.current)
      return
    }
    stopPreview()
    setPreviewing(preset)
    // Defer start until next tick so the hook re-resolves the preset ref
    setTimeout(() => {
      startPreview()
      previewTimeoutRef.current = setTimeout(() => {
        stopPreview()
        setPreviewing(null)
      }, PREVIEW_MS)
    }, 0)
  }

  const handleSave = async () => {
    if (!preferences) return
    setSaving(true)
    try {
      await updatePreferences({
        ...preferences,
        sound_enabled: soundEnabled,
        sound_preference: draft,
      })
      toast.success('Alarm sound preference saved')
    } catch (err) {
      toast.error('Failed to save alarm sound preference')
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setSaving(false)
    }
  }

  if (preferencesLoading && !preferences) {
    return (
      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
        Loading sound preferences…
      </div>
    )
  }

  if (!preferences) {
    return null
  }

  return (
    <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Panic alarm sound
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Choose how the alarm sounds when a panic alert fires. Use Preview to listen
            before saving.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setSoundEnabled((v: boolean) => !v)}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-pressed={soundEnabled}
        >
          {soundEnabled ? (
            <>
              <Volume2 className="w-4 h-4" aria-hidden="true" />
              Sound on
            </>
          ) : (
            <>
              <VolumeX className="w-4 h-4" aria-hidden="true" />
              Sound off
            </>
          )}
        </button>
      </div>

      <fieldset
        disabled={!soundEnabled}
        className={soundEnabled ? '' : 'opacity-50'}
      >
        <legend className="sr-only">Alarm tone</legend>
        <div className="space-y-2">
          {ALERT_SOUND_OPTIONS.map((opt) => {
            const isSelected = draft === opt.id
            const isPlaying = previewing === opt.id
            return (
              <div
                key={opt.id}
                className={`flex items-center justify-between gap-4 p-3 rounded-lg border ${
                  isSelected
                    ? 'border-lsc-rose bg-lsc-rose/5'
                    : 'border-lsc-border dark:border-earth-700'
                }`}
              >
                <label className="flex items-start gap-3 cursor-pointer flex-1">
                  <input
                    type="radio"
                    name="alarm-sound"
                    value={opt.id}
                    checked={isSelected}
                    onChange={() => setDraft(opt.id)}
                    className="mt-1 text-lsc-rose focus:ring-lsc-rose"
                  />
                  <div>
                    <div className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                      {opt.label}
                      <span
                        className="rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                        aria-label={`Intensity ${opt.intensity} of 5`}
                      >
                        Intensity {opt.intensity}/5
                      </span>
                    </div>
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {opt.description}
                    </div>
                  </div>
                </label>
                <button
                  type="button"
                  onClick={() => handlePreview(opt.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  aria-label={isPlaying ? `Stop preview of ${opt.label}` : `Preview ${opt.label}`}
                >
                  {isPlaying ? (
                    <>
                      <Square className="w-3.5 h-3.5" aria-hidden="true" />
                      Stop
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" aria-hidden="true" />
                      Preview
                    </>
                  )}
                </button>
              </div>
            )
          })}
        </div>
      </fieldset>

      <div className="flex justify-end gap-2 mt-6">
        <button
          type="button"
          onClick={handleSave}
          disabled={!isDirty || saving}
          className="px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
        >
          {saving ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              Saving…
            </span>
          ) : (
            'Save sound preference'
          )}
        </button>
      </div>
    </div>
  )
}
