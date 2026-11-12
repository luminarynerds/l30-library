/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useRef, useCallback, useEffect } from 'react'

export type AlertSoundPreset =
  | 'gentle_chime'
  | 'soft_pulse'
  | 'warble'
  | 'two_tone'
  | 'urgent_siren'

export interface AlertSoundOption {
  id: AlertSoundPreset
  label: string
  description: string
  /** Rough loudness/intensity, 1 (gentlest) - 5 (harshest) */
  intensity: number
}

export const ALERT_SOUND_OPTIONS: AlertSoundOption[] = [
  {
    id: 'gentle_chime',
    label: 'Gentle chime',
    description: 'Soft repeating chime, easy on the ears',
    intensity: 1,
  },
  {
    id: 'soft_pulse',
    label: 'Soft pulse',
    description: 'Slow rounded pulse, calmer alert',
    intensity: 2,
  },
  {
    id: 'warble',
    label: 'Warble',
    description: 'Gentle wobble between two close tones',
    intensity: 3,
  },
  {
    id: 'two_tone',
    label: 'Two-tone alarm',
    description: 'Alternating two-tone, moderate attention',
    intensity: 4,
  },
  {
    id: 'urgent_siren',
    label: 'Urgent siren',
    description: 'Rising tone sweep, most noticeable',
    intensity: 5,
  },
]

export const DEFAULT_ALERT_SOUND: AlertSoundPreset = 'gentle_chime'

interface UseAlertAudioOptions {
  preset?: AlertSoundPreset
}

interface PresetConfig {
  type: OscillatorType
  gain: number
  schedule: (osc: OscillatorNode, ctx: AudioContext) => () => void
}

function buildPresetConfig(preset: AlertSoundPreset): PresetConfig {
  switch (preset) {
    case 'gentle_chime':
      return {
        type: 'sine',
        gain: 0.08,
        schedule: (osc, ctx) => {
          const tones = [392, 523]
          let i = 0
          const master = (ctx as AudioContext & { _alertMaster?: GainNode })._alertMaster
          if (!master) return () => {}
          const baseGain = master.gain.value
          const chime = () => {
            const now = ctx.currentTime
            osc.frequency.setValueAtTime(tones[i % 2] ?? tones[0] ?? 440, now)
            master.gain.cancelScheduledValues(now)
            master.gain.setValueAtTime(0.0, now)
            master.gain.linearRampToValueAtTime(baseGain, now + 0.15)
            master.gain.linearRampToValueAtTime(0.0, now + 0.8)
            i++
          }
          chime()
          const id = setInterval(chime, 3000)
          return () => clearInterval(id)
        },
      }
    case 'soft_pulse':
      return {
        type: 'sine',
        gain: 0.10,
        schedule: (osc, ctx) => {
          osc.frequency.value = 340
          const master = (ctx as AudioContext & { _alertMaster?: GainNode })._alertMaster
          if (!master) return () => {}
          const baseGain = master.gain.value
          const pulse = () => {
            const now = ctx.currentTime
            master.gain.cancelScheduledValues(now)
            master.gain.setValueAtTime(0.0, now)
            master.gain.linearRampToValueAtTime(baseGain, now + 0.4)
            master.gain.linearRampToValueAtTime(0.0, now + 1.2)
          }
          pulse()
          const id = setInterval(pulse, 3500)
          return () => clearInterval(id)
        },
      }
    case 'warble':
      return {
        type: 'triangle',
        gain: 0.12,
        schedule: (osc) => {
          osc.frequency.value = 440
          let high = true
          const id = setInterval(() => {
            high = !high
            osc.frequency.value = high ? 460 : 430
          }, 300)
          return () => clearInterval(id)
        },
      }
    case 'two_tone':
      return {
        type: 'triangle',
        gain: 0.15,
        schedule: (osc) => {
          osc.frequency.value = 520
          let high = true
          const id = setInterval(() => {
            high = !high
            osc.frequency.value = high ? 520 : 440
          }, 800)
          return () => clearInterval(id)
        },
      }
    case 'urgent_siren':
      return {
        type: 'triangle',
        gain: 0.20,
        schedule: (osc, ctx) => {
          const startFreq = 440
          const endFreq = 660
          const sweepMs = 1200
          osc.frequency.value = startFreq
          const sweep = () => {
            const now = ctx.currentTime
            osc.frequency.cancelScheduledValues(now)
            osc.frequency.setValueAtTime(startFreq, now)
            osc.frequency.linearRampToValueAtTime(endFreq, now + sweepMs / 2000)
            osc.frequency.linearRampToValueAtTime(startFreq, now + sweepMs / 1000)
          }
          sweep()
          const id = setInterval(sweep, sweepMs)
          return () => clearInterval(id)
        },
      }
    default:
      // Unknown preset from backend -- fall back to gentle chime
      return {
        type: "sine" as OscillatorType,
        gain: 0.08,
        schedule: (osc: OscillatorNode, ctx: AudioContext) => {
          const tones = [392, 523]
          let i = 0
          const master = (ctx as AudioContext & { _alertMaster?: GainNode })._alertMaster
          if (!master) return () => {}
          const baseGain = master.gain.value
          const chime = () => {
            const now = ctx.currentTime
            osc.frequency.setValueAtTime(tones[i % 2] ?? tones[0] ?? 440, now)
            master.gain.cancelScheduledValues(now)
            master.gain.setValueAtTime(0.0, now)
            master.gain.linearRampToValueAtTime(baseGain, now + 0.15)
            master.gain.linearRampToValueAtTime(0.0, now + 0.8)
            i++
          }
          chime()
          const id = setInterval(chime, 3000)
          return () => clearInterval(id)
        },
      }
  }
}

export function useAlertAudio(options: UseAlertAudioOptions = {}) {
  const { preset = DEFAULT_ALERT_SOUND } = options
  const audioCtxRef = useRef<AudioContext | null>(null)
  const oscillatorRef = useRef<OscillatorNode | null>(null)
  const cleanupRef = useRef<(() => void) | null>(null)
  const isPlayingRef = useRef(false)
  const presetRef = useRef(preset)

  useEffect(() => {
    presetRef.current = preset
  }, [preset])

  const stop = useCallback(() => {
    isPlayingRef.current = false
    if (cleanupRef.current) {
      cleanupRef.current()
      cleanupRef.current = null
    }
    if (oscillatorRef.current) {
      try {
        oscillatorRef.current.stop()
      } catch {
        // already stopped
      }
      oscillatorRef.current = null
    }
    if (audioCtxRef.current) {
      void audioCtxRef.current.close()
      audioCtxRef.current = null
    }
  }, [])

  const start = useCallback(() => {
    if (isPlayingRef.current) return
    isPlayingRef.current = true

    const ctx = new AudioContext()
    audioCtxRef.current = ctx

    const config = buildPresetConfig(presetRef.current)

    const master = ctx.createGain()
    master.gain.value = config.gain
    master.connect(ctx.destination)
    ;(ctx as AudioContext & { _alertMaster?: GainNode })._alertMaster = master

    const osc = ctx.createOscillator()
    osc.type = config.type
    osc.connect(master)
    osc.start()
    oscillatorRef.current = osc

    cleanupRef.current = config.schedule(osc, ctx)
  }, [])

  useEffect(() => {
    return () => stop()
  }, [stop])

  return { start, stop, isPlaying: isPlayingRef.current }
}
