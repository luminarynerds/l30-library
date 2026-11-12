/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  BookOpen, ChevronRight, ChevronLeft,
  Timer, CheckCircle2, ArrowRight, MessageCircle,
  Pause, SkipForward, Grid3X3, Maximize, Minimize,
} from 'lucide-react'
import { SCENES } from '@/components/board-demo/board-demo-data'
import { ProgressBar, SceneTransition, useSwipe } from '@/components/board-demo/DemoAnimations'
import { OverviewGridModal } from '@/components/board-demo/OverviewGridModal'
import { WelcomeScene } from '@/components/board-demo/WelcomeScene'
import { CheckoutScene } from '@/components/board-demo/CheckoutScene'
import { HoldsScene } from '@/components/board-demo/HoldsScene'
import { DashboardScene } from '@/components/board-demo/DashboardScene'
import { CommunityValueScene } from '@/components/board-demo/CommunityValueScene'
import { CatalogSearchScene } from '@/components/board-demo/CatalogSearchScene'
import { AccessibilityScene } from '@/components/board-demo/AccessibilityScene'
import { SecurityScene } from '@/components/board-demo/SecurityScene'
import { WowScene } from '@/components/board-demo/WowScene'
import PageContainer from '@/components/layout/PageContainer'

const SCENE_COMPONENTS: Record<number, React.FC> = {
  0: WelcomeScene,
  1: CheckoutScene,
  2: HoldsScene,
  3: DashboardScene,
  4: CommunityValueScene,
  5: CatalogSearchScene,
  6: AccessibilityScene,
  7: SecurityScene,
  8: WowScene,
}

export default function BoardDemoPage(): React.ReactElement {
  const [currentScene, setCurrentScene] = useState(0)
  const [startTime] = useState(() => Date.now())
  const [elapsed, setElapsed] = useState(0)
  const [autoAdvance, setAutoAdvance] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showOverview, setShowOverview] = useState(false)
  const [autoCountdown, setAutoCountdown] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const timer = setInterval(() => setElapsed(Date.now() - startTime), 1000)
    return () => clearInterval(timer)
  }, [startTime])

  const formatTime = useCallback((ms: number) => {
    const totalSec = Math.floor(ms / 1000)
    const min = Math.floor(totalSec / 60)
    const sec = totalSec % 60
    return `${min}:${sec.toString().padStart(2, '0')}`
  }, [])

  const scene = SCENES[currentScene]!
  const SceneComponent = SCENE_COMPONENTS[currentScene]!

  const goNext = useCallback(() => {
    setCurrentScene((s) => Math.min(s + 1, SCENES.length - 1))
  }, [])
  const goPrev = useCallback(() => {
    setCurrentScene((s) => Math.max(s - 1, 0))
  }, [])

  useSwipe(goNext, goPrev)

  useEffect(() => {
    if (!autoAdvance) return
    if (currentScene >= SCENES.length - 1) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- turns off the auto-advance timer when the last scene is reached
      setAutoAdvance(false)
      return
    }
    const durationSec = scene.durationMinutes * 60
    setAutoCountdown(durationSec)

    const countdown = setInterval(() => {
      setAutoCountdown((c) => {
        if (c <= 1) {
          clearInterval(countdown)
          setCurrentScene((s) => Math.min(s + 1, SCENES.length - 1))
          return 0
        }
        return c - 1
      })
    }, 1000)

    return () => clearInterval(countdown)
  }, [autoAdvance, currentScene, scene.durationMinutes])

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen?.()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen?.()
      setIsFullscreen(false)
    }
  }, [])

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault()
        setCurrentScene((s) => Math.min(s + 1, SCENES.length - 1))
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setCurrentScene((s) => Math.max(s - 1, 0))
      }
      if (e.key === 'Home') {
        e.preventDefault()
        setCurrentScene(0)
      }
      if (e.key === 'End') {
        e.preventDefault()
        setCurrentScene(SCENES.length - 1)
      }
      if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen()
      }
      if (e.key === 'Escape' && showOverview) {
        setShowOverview(false)
      }
      if (e.key === 'g' || e.key === 'G') {
        setShowOverview((v) => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggleFullscreen, showOverview])

  return (
    <div ref={containerRef} className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      {showOverview && (
        <OverviewGridModal
          currentScene={currentScene}
          onSelect={(i) => { setCurrentScene(i); setShowOverview(false) }}
        />
      )}

      <div className="sticky top-0 z-40 bg-lsc-white/95 dark:bg-earth-800/95 backdrop-blur border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BookOpen className="w-5 h-5 text-lsc-rose" />
              <span className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">
                L30 Board Demo
              </span>
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hidden sm:inline">
                &middot; {scene.title}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAutoAdvance((a) => !a)}
                className={`flex items-center gap-1 px-2 py-1 text-xs rounded-lg transition-colors ${
                  autoAdvance
                    ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200'
                }`}
                title="Auto-advance scenes"
              >
                {autoAdvance ? <Pause className="w-3 h-3" /> : <SkipForward className="w-3 h-3" />}
                <span className="hidden sm:inline">{autoAdvance ? `Auto (${Math.floor(autoCountdown / 60)}:${(autoCountdown % 60).toString().padStart(2, '0')})` : 'Auto'}</span>
              </button>

              <button
                onClick={() => setShowOverview((v) => !v)}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
                title="Scene overview (G)"
              >
                <Grid3X3 className="w-3 h-3" />
              </button>

              <button
                onClick={toggleFullscreen}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
                title="Fullscreen (F)"
              >
                {isFullscreen ? <Minimize className="w-3 h-3" /> : <Maximize className="w-3 h-3" />}
              </button>

              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1 ml-1">
                <Timer className="w-3.5 h-3.5" />
                {formatTime(elapsed)}
              </span>
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {currentScene + 1} / {SCENES.length}
              </span>
            </div>
          </div>
          <ProgressBar current={currentScene} total={SCENES.length} />
        </PageContainer>
      </div>

      <PageContainer className="pt-4">
        <div className="flex gap-1.5 overflow-x-auto pb-2 scrollbar-hide">
          {SCENES.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setCurrentScene(i)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                i === currentScene
                  ? 'bg-lsc-rose text-white shadow-sm scale-105'
                  : i < currentScene
                  ? 'bg-status-success-100 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-400 hover:scale-[1.03]'
                  : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 hover:scale-[1.03]'
              }`}
              aria-current={i === currentScene ? 'step' : undefined}
            >
              {i < currentScene && <CheckCircle2 className="w-3 h-3" />}
              <s.icon className="w-3 h-3" />
              <span className="hidden sm:inline">{s.title}</span>
            </button>
          ))}
        </div>
      </PageContainer>

      <SceneTransition sceneKey={currentScene}>
        <PageContainer as="main" className="py-6">
          <div className={`rounded-xl bg-gradient-to-r ${scene.bgGradient} p-6 mb-6`}>
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl bg-lsc-white/80 dark:bg-earth-800/80 shadow-sm`}>
                <scene.icon className={`w-7 h-7 ${scene.color}`} />
              </div>
              <div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{scene.title}</h1>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{scene.subtitle}</p>
              </div>
              <div className="ml-auto text-right hidden sm:block">
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{scene.durationMinutes} min</span>
              </div>
            </div>
          </div>

          <div className="bg-status-warning-50/50 dark:bg-status-warning-900/10 rounded-lg p-4 mb-6 border border-status-warning-200/50 dark:border-status-warning-800/30">
            <details open>
              <summary className="text-sm font-medium text-status-warning-800 dark:text-status-warning-400 cursor-pointer select-none flex items-center gap-2">
                <MessageCircle className="w-4 h-4" />
                Presenter Notes
              </summary>
              <ul className="mt-2 space-y-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {scene.talkingPoints.map((point, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <ArrowRight className="w-3.5 h-3.5 text-status-warning-500 mt-0.5 shrink-0" />
                    {point}
                  </li>
                ))}
              </ul>
            </details>
          </div>

          <SceneComponent />
        </PageContainer>
      </SceneTransition>

      <div className="sticky bottom-0 bg-lsc-white/95 dark:bg-earth-800/95 backdrop-blur border-t border-lsc-border dark:border-earth-700">
        <PageContainer className="py-3 flex items-center justify-between">
          <button
            onClick={goPrev}
            disabled={currentScene === 0}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>

          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hidden sm:flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">←</kbd>
            <kbd className="px-1.5 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">→</kbd>
            navigate &middot;
            <kbd className="px-1.5 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">F</kbd>
            fullscreen &middot;
            <kbd className="px-1.5 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">G</kbd>
            overview
          </span>

          <button
            onClick={goNext}
            disabled={currentScene === SCENES.length - 1}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-lsc-rose text-white hover:bg-status-warning-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </PageContainer>
      </div>
    </div>
  )
}
