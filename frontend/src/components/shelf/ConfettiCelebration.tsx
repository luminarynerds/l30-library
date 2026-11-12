/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import type { ReadingMilestone } from '@/api/domains/content/reading-milestones-api'
import { t } from '@/i18n'

interface ConfettiCelebrationProps {
  milestone: ReadingMilestone | null
}

export default function ConfettiCelebration({ milestone }: ConfettiCelebrationProps) {
  const [visible, setVisible] = useState(false)
  // Lazy-init so the first render already knows the preference — no
  // confetti frame flashes before an effect can correct it.
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    if (!milestone) return
    if (prefersReducedMotion) {
      // Reset visibility in case the preference flipped while confetti was
      // mid-animation (this re-run cleared that run's hide-timer).
      // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing animation state with reduced-motion preference
      setVisible(false)
      toast.success(t('toast.shelf.title', { title: milestone.title }))
      return
    }
    setVisible(true)
    const timer = setTimeout(() => setVisible(false), 3000)
    return () => clearTimeout(timer)
  }, [milestone, prefersReducedMotion])

  // Generate confetti pieces deterministically from index
  const pieces = useMemo(() => Array.from({ length: 30 }, (_, i) => {
    const hash = ((i * 2654435761) >>> 0) / 4294967296
    const hash2 = (((i + 7) * 2654435761) >>> 0) / 4294967296
    const hash3 = (((i + 13) * 2654435761) >>> 0) / 4294967296
    return {
      id: i,
      left: `${hash * 100}%`,
      delay: `${hash2 * 0.5}s`,
      color: ['#f59e0b', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899'][i % 6],
      size: 6 + hash3 * 6,
      isRound: hash > 0.5,
    }
  }), [])

  if (!visible || !milestone) return null

  return (
    <div
      className="fixed inset-0 z-50 pointer-events-none overflow-hidden"
      aria-live="polite"
      aria-label={`Celebration: ${milestone.title}`}
    >
      {pieces.map((p) => (
        <div
          key={p.id}
          className="absolute animate-confetti-fall"
          style={{
            left: p.left,
            top: '-10px',
            animationDelay: p.delay,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            borderRadius: p.isRound ? '50%' : '2px',
          }}
        />
      ))}

      {/* Inline keyframes */}
      <style>{`
        @keyframes confetti-fall {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }
        .animate-confetti-fall {
          animation: confetti-fall 2.5s ease-in forwards;
        }
      `}</style>
    </div>
  )
}
