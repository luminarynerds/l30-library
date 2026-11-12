/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
import { MapPin, X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { US_STATES_MAP } from './ban-tracker-data'
import type { StateCount } from './types'

// Geographically-arranged tile grid layout (FiveThirtyEight / NPR style)
// [col, row] — 12 columns x 8 rows
const TILE_GRID: Record<string, [number, number]> = {
  ME: [11, 0],
  VT: [10, 0], NH: [11, 1],
  WA: [1, 1], MT: [2, 1], ND: [3, 1], MN: [4, 1], WI: [5, 1], MI: [7, 1], NY: [9, 1], MA: [10, 1],
  OR: [1, 2], ID: [2, 2], SD: [3, 2], IA: [4, 2], IL: [5, 2], IN: [6, 2], OH: [7, 2], PA: [8, 2], NJ: [9, 2], CT: [10, 2], RI: [11, 2],
  NV: [1, 3], WY: [2, 3], NE: [3, 3], MO: [4, 3], KY: [5, 3], WV: [6, 3], VA: [7, 3], MD: [8, 3], DE: [9, 3],
  CA: [0, 4], UT: [1, 4], CO: [2, 4], KS: [3, 4], AR: [4, 4], TN: [5, 4], NC: [6, 4], SC: [7, 4], DC: [9, 4],
  AZ: [1, 5], NM: [2, 5], OK: [3, 5], LA: [4, 5], MS: [5, 5], AL: [6, 5], GA: [7, 5],
  TX: [3, 6], FL: [7, 6],
  AK: [0, 7], HI: [2, 7],
}

// First abbrev in TILE_GRID iteration order — used as the default keyboard
// landing cell so the map is reachable via a single tab stop (WCAG 2.4.3).
const FIRST_ABBREV = Object.keys(TILE_GRID)[0]

// Build a reverse lookup: "col,row" -> abbrev, for arrow-key adjacency.
const COORD_TO_ABBREV: Record<string, string> = Object.entries(TILE_GRID).reduce(
  (acc, [abbrev, [col, row]]) => {
    acc[`${col},${row}`] = abbrev
    return acc
  },
  {} as Record<string, string>,
)

function getHeatFill(count: number, maxCount: number, isDark: boolean): string {
  if (maxCount === 0 || count === 0) return isDark ? '#374151' : '#f3f4f6'
  const ratio = count / maxCount
  if (isDark) {
    if (ratio > 0.75) return '#7f1d1d'
    if (ratio > 0.5) return '#78350f'
    if (ratio > 0.25) return '#713f12'
    return '#422006'
  }
  if (ratio > 0.75) return '#fecaca'
  if (ratio > 0.5) return '#fed7aa'
  if (ratio > 0.25) return '#fde68a'
  return '#fef9c3'
}

function getHeatTextFill(count: number, maxCount: number, isDark: boolean): string {
  if (maxCount === 0 || count === 0) return '#9ca3af'
  const ratio = count / maxCount
  if (isDark) {
    if (ratio > 0.75) return '#fecaca'
    if (ratio > 0.5) return '#fed7aa'
    if (ratio > 0.25) return '#fde68a'
    return '#fef9c3'
  }
  if (ratio > 0.75) return '#991b1b'
  if (ratio > 0.5) return '#9a3412'
  if (ratio > 0.25) return '#92400e'
  return '#854d0e'
}

export function StateMap({
  stateData,
  selectedState,
  onStateClick,
}: {
  stateData: StateCount[]
  selectedState: string
  onStateClick: (state: string) => void
}): React.ReactElement {
  const { t } = useTranslation()
  const [hoveredState, setHoveredState] = useState<string | null>(null)
  const [focusedState, setFocusedState] = useState<string | null>(null)
  // Roving-tabindex target. Until the user focuses a cell, the first cell in
  // TILE_GRID iteration order is the single tab stop (WCAG 2.4.3).
  const [currentTarget, setCurrentTarget] = useState<string | null>(null)
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })

  // Refs to each <g> by abbrev, so arrow-nav can imperatively focus the next cell.
  const cellRefs = useRef<Map<string, SVGGElement>>(new Map())
  // True when the most recent currentTarget change came from a keyboard arrow,
  // so the focus effect knows to call .focus(). Prevents stealing focus on mount.
  const moveByKeyboard = useRef(false)

  const containerRef = useRef<HTMLDivElement | null>(null)

  const stateCountMap = useMemo(() => {
    const map = new Map<string, number>()
    for (const item of stateData) {
      map.set(item.state, item.count)
    }
    return map
  }, [stateData])

  const maxCount = useMemo(() => {
    let max = 0
    for (const item of stateData) {
      if (item.count > max) max = item.count
    }
    return max
  }, [stateData])

  const [isDark, setIsDark] = useState<boolean>(
    () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  )
  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    const update = () => setIsDark(root.classList.contains('dark'))
    update()
    const observer = new MutationObserver(update)
    observer.observe(root, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  const CELL = 56
  const GAP = 4
  const COLS = 12
  const ROWS = 8
  const svgWidth = COLS * (CELL + GAP) + GAP
  const svgHeight = ROWS * (CELL + GAP) + GAP

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }

  // Move tooltip to anchor over a given abbrev's <g>, in container-pixel coords.
  // Used when keyboard focus changes (mouse path uses handleMouseMove).
  const positionTooltipOverCell = useCallback((abbrev: string) => {
    const g = cellRefs.current.get(abbrev)
    const container = containerRef.current
    if (!g || !container) return
    const cellRect = g.getBoundingClientRect()
    const containerRect = container.getBoundingClientRect()
    setTooltipPos({
      x: cellRect.left - containerRect.left + cellRect.width / 2,
      y: cellRect.top - containerRect.top + cellRect.height / 2,
    })
  }, [])

  useEffect(() => {
    if (!moveByKeyboard.current) return
    moveByKeyboard.current = false
    if (!currentTarget) return
    const node = cellRefs.current.get(currentTarget)
    node?.focus()
    positionTooltipOverCell(currentTarget)
  }, [currentTarget, positionTooltipOverCell])

  const handleKeyDown = (e: React.KeyboardEvent<SVGGElement>, abbrev: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onStateClick(abbrev === selectedState ? '' : abbrev)
      return
    }
    const dir: Record<string, [number, number]> = {
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
      ArrowUp: [0, -1],
      ArrowDown: [0, 1],
    }
    const delta = dir[e.key]
    if (!delta) return
    const here = TILE_GRID[abbrev]
    if (!here) return
    const next = COORD_TO_ABBREV[`${here[0] + delta[0]},${here[1] + delta[1]}`]
    if (!next) return
    e.preventDefault()
    moveByKeyboard.current = true
    setCurrentTarget(next)
  }

  const hoveredCount = hoveredState ? (stateCountMap.get(hoveredState) ?? 0) : 0
  // Tooltip surfaces for either mouse hover OR keyboard focus.
  const tooltipAbbrev = hoveredState ?? focusedState
  const tooltipCount = tooltipAbbrev ? (stateCountMap.get(tooltipAbbrev) ?? hoveredCount) : 0

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        <MapPin className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
          Bans by State
        </h3>
      </div>

      {/* Color legend */}
      <div className="flex items-center gap-3 mb-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
        <span>Fewer</span>
        <div className="flex gap-0.5">
          {(isDark
            ? ['#422006', '#713f12', '#78350f', '#7f1d1d']
            : ['#fef9c3', '#fde68a', '#fed7aa', '#fecaca']
          ).map((hex) => (
            <div key={hex} className="w-6 h-3 rounded-sm" style={{ backgroundColor: hex }} />
          ))}
        </div>
        <span>More</span>
      </div>

      {/* SVG Tile Grid Map */}
      <div ref={containerRef} className="relative w-full" onMouseMove={handleMouseMove}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto"
          role="img"
          aria-label={t('publicBanTracker.interactiveMapOfBookBans')}
        >
          {Object.entries(TILE_GRID).map(([abbrev, [col, row]]) => {
            const count = stateCountMap.get(abbrev) ?? 0
            const x = GAP + col * (CELL + GAP)
            const y = GAP + row * (CELL + GAP)
            const fill = getHeatFill(count, maxCount, isDark)
            const textFill = getHeatTextFill(count, maxCount, isDark)
            const isHovered = hoveredState === abbrev
            const isSelected = selectedState === abbrev
            const isFocused = focusedState === abbrev
            // Roving tabindex: only the current target is tab-reachable; the
            // first cell is the default until the user focuses something.
            const isTabStop = currentTarget ? currentTarget === abbrev : abbrev === FIRST_ABBREV

            // Focus outline beats selection outline when both apply.
            const strokeColor = isFocused
              ? '#ea580c'
              : isSelected
                ? '#ea580c'
                : isHovered
                  ? (isDark ? '#d97706' : '#f59e0b')
                  : 'transparent'
            const strokeWidth = isFocused ? 3 : isSelected ? 3 : isHovered ? 2 : 0

            return (
              <g
                key={abbrev}
                ref={(node) => {
                  if (node) cellRefs.current.set(abbrev, node)
                  else cellRefs.current.delete(abbrev)
                }}
                onClick={() => onStateClick(abbrev === selectedState ? '' : abbrev)}
                onMouseEnter={() => setHoveredState(abbrev)}
                onMouseLeave={() => setHoveredState(null)}
                onFocus={() => {
                  setFocusedState(abbrev)
                  setCurrentTarget(abbrev)
                  positionTooltipOverCell(abbrev)
                }}
                onBlur={() => setFocusedState(null)}
                style={{ cursor: 'pointer', outline: 'none' }}
                role="button"
                tabIndex={isTabStop ? 0 : -1}
                aria-label={`${US_STATES_MAP[abbrev]}: ${count} ban report${count !== 1 ? 's' : ''}. Click to filter.`}
                onKeyDown={(e) => handleKeyDown(e, abbrev)}
              >
                <rect
                  x={x}
                  y={y}
                  width={CELL}
                  height={CELL}
                  rx={6}
                  fill={fill}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  style={{
                    transition: 'fill 0.15s ease, stroke 0.15s ease, transform 0.15s ease',
                    transformOrigin: `${x + CELL / 2}px ${y + CELL / 2}px`,
                    transform: isHovered ? 'scale(1.08)' : 'scale(1)',
                  }}
                />
                <text
                  x={x + CELL / 2}
                  y={y + CELL / 2 - 4}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={textFill}
                  fontSize="12"
                  fontWeight="700"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {abbrev}
                </text>
                <text
                  x={x + CELL / 2}
                  y={y + CELL / 2 + 12}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={textFill}
                  fontSize="10"
                  fontWeight="400"
                  opacity={0.75}
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {count}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Tooltip — surfaces for mouse hover OR keyboard focus */}
        {tooltipAbbrev && (
          <div
            className="absolute z-10 pointer-events-none px-3 py-2 rounded-lg shadow-lg bg-earth-900 dark:bg-earth-100 text-white dark:text-earth-900 text-xs font-medium whitespace-nowrap"
            style={{
              left: `${Math.min(tooltipPos.x + 12, (typeof window !== 'undefined' ? window.innerWidth * 0.8 : 400))}px`,
              top: `${tooltipPos.y - 40}px`,
            }}
          >
            <span className="font-bold">{US_STATES_MAP[tooltipAbbrev]}</span>
            {': '}
            {tooltipCount} ban{tooltipCount !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {selectedState && (
        <div className="mt-3 flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span>
            Filtering by <span className="font-semibold text-lsc-rose dark:text-lsc-rose-light">{US_STATES_MAP[selectedState]}</span>
          </span>
          <button
            onClick={() => onStateClick('')}
            className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
            aria-label={t('aria.publicBanTracker.clearStateFilter')}
          >
            <X className="w-3 h-3" aria-hidden="true" />
            Clear
          </button>
        </div>
      )}
    </div>
  )
}
