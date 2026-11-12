/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { useState, useEffect, useRef, useMemo } from 'react'
import type { AnimatedCounterProps } from './types'

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function AnimatedCounter({ end, duration = 2000, prefix = '', suffix = '', className = '' }: AnimatedCounterProps) {
  const [count, setCount] = useState(prefersReducedMotion ? end : 0)
  const [started, setStarted] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (prefersReducedMotion) return
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry?.isIntersecting && !started) setStarted(true) },
      { threshold: 0.5 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [started])

  useEffect(() => {
    if (!started || prefersReducedMotion) return
    const startTime = Date.now()
    const timer = setInterval(() => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(eased * end))
      if (progress >= 1) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [started, end, duration])

  return <span ref={ref} className={className}>{prefix}{count.toLocaleString()}{suffix}</span>
}

export function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = ((current + 1) / total) * 100
  return (
    <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-1.5">
      <div
        className="bg-lsc-rose h-1.5 rounded-full transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export function SceneTransition({ sceneKey, children }: { sceneKey: number; children: React.ReactNode }) {
  const [visible, setVisible] = useState(prefersReducedMotion)
  const [direction, setDirection] = useState<'left' | 'right'>('right')
  const prevKey = useRef(sceneKey)

  useEffect(() => {
    if (prefersReducedMotion) return

    setDirection(sceneKey > prevKey.current ? 'right' : 'left')
    prevKey.current = sceneKey
    setVisible(false)
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => setVisible(true))
    })
    return () => cancelAnimationFrame(frame)
  }, [sceneKey])

  if (prefersReducedMotion) {
    return <>{children}</>
  }

  return (
    <div
      className="transition-all duration-500 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible
          ? 'translateX(0)'
          : direction === 'right'
          ? 'translateX(40px)'
          : 'translateX(-40px)',
      }}
    >
      {children}
    </div>
  )
}

function StaggeredItem({ children, index, staggerMs }: { children: React.ReactNode; index: number; staggerMs: number }) {
  const [visible, setVisible] = useState(prefersReducedMotion)
  useEffect(() => {
    if (prefersReducedMotion) return
    const t = setTimeout(() => setVisible(true), index * staggerMs)
    return () => clearTimeout(t)
  }, [index, staggerMs])

  if (prefersReducedMotion) {
    return <>{children}</>
  }

  return (
    <div
      className="transition-all duration-500 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(16px)',
      }}
    >
      {children}
    </div>
  )
}

export function StaggeredList({ children, staggerMs = 80 }: { children: React.ReactNode; staggerMs?: number }) {
  const items = Array.isArray(children) ? children : [children]
  return (
    <>
      {items.map((child, i) => (
        <StaggeredItem key={i} index={i} staggerMs={staggerMs}>
          {child}
        </StaggeredItem>
      ))}
    </>
  )
}

// Simple deterministic hash for confetti variation
const pseudoRandom = (seed: number) => (((seed * 2654435761) >>> 0) / 4294967296)

export function ConfettiBurst() {
  const particles = useMemo(() =>
    Array.from({ length: 40 }, (_, i) => ({
      id: i,
      x: pseudoRandom(i) * 100,
      delay: pseudoRandom(i + 40) * 0.5,
      duration: 1.5 + pseudoRandom(i + 80) * 1.5,
      size: 4 + pseudoRandom(i + 120) * 6,
      color: ['#f59e0b', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899'][i % 6]!,
      rotation: pseudoRandom(i + 160) * 360,
    })),
    []
  )

  if (prefersReducedMotion) return null

  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden" aria-hidden>
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute animate-confetti-fall"
          style={{
            left: `${p.x}%`,
            top: '-10px',
            width: `${p.size}px`,
            height: `${p.size * 0.6}px`,
            backgroundColor: p.color,
            borderRadius: '2px',
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
            transform: `rotate(${p.rotation}deg)`,
          }}
        />
      ))}
      <style>{`
        @keyframes confetti-fall {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }
        .animate-confetti-fall {
          animation-name: confetti-fall;
          animation-timing-function: cubic-bezier(0.25, 0.46, 0.45, 0.94);
          animation-fill-mode: forwards;
        }
      `}</style>
    </div>
  )
}

export function useSwipe(onLeft: () => void, onRight: () => void) {
  const touchStart = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    const handleStart = (e: TouchEvent) => {
      const touch = e.touches[0]
      if (touch) touchStart.current = { x: touch.clientX, y: touch.clientY }
    }
    const handleEnd = (e: TouchEvent) => {
      if (!touchStart.current) return
      const touch = e.changedTouches[0]
      if (!touch) return
      const dx = touch.clientX - touchStart.current.x
      const dy = touch.clientY - touchStart.current.y
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) {
        if (dx > 0) onRight()
        else onLeft()
      }
      touchStart.current = null
    }
    window.addEventListener('touchstart', handleStart, { passive: true })
    window.addEventListener('touchend', handleEnd, { passive: true })
    return () => {
      window.removeEventListener('touchstart', handleStart)
      window.removeEventListener('touchend', handleEnd)
    }
  }, [onLeft, onRight])
}
