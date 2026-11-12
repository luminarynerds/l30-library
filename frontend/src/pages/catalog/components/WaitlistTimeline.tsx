/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { clsx } from '@/utils/helpers'
import { getCurrentLocale } from '@/i18n'

interface WaitlistTimelineProps {
  position: number
  totalAhead: number
  estimatedReadyDate: Date | null
  holdStatus: 'pending' | 'ready' | null
  reduceMotion: boolean
}

interface TimelineNode {
  label: string
  sublabel?: string
  state: 'completed' | 'current' | 'future'
}

export function WaitlistTimeline({
  position,
  totalAhead,
  estimatedReadyDate,
  holdStatus,
  reduceMotion,
}: WaitlistTimelineProps): React.ReactElement {
  const isReady = holdStatus === 'ready'

  const nodes: TimelineNode[] = [
    {
      label: 'You',
      sublabel: `#${position} in line`,
      state: 'completed',
    },
    {
      label: `${totalAhead} Ahead`,
      sublabel: totalAhead === 0 ? "You're next!" : `${totalAhead} patron${totalAhead !== 1 ? 's' : ''} ahead`,
      state: totalAhead === 0 ? 'completed' : isReady ? 'completed' : 'current',
    },
    {
      label: estimatedReadyDate
        ? `~${estimatedReadyDate.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric' })}`
        : 'Soon',
      sublabel: 'Estimated',
      state: isReady ? 'completed' : 'future',
    },
    {
      label: 'Ready!',
      sublabel: isReady ? 'Pick up now' : 'Awaiting',
      state: isReady ? 'current' : 'future',
    },
  ]

  const ariaDescription = isReady
    ? `Your hold is ready for pickup! You are position ${position} in the queue.`
    : `You are #${position} in the hold queue with ${totalAhead} patron${totalAhead !== 1 ? 's' : ''} ahead. Estimated ready date: ${estimatedReadyDate?.toLocaleDateString() ?? 'unknown'}.`

  return (
    <div
      className="mt-4 p-4 bg-lsc-cream/50 dark:bg-lsc-dark/50 rounded-xl"
      role="status"
      aria-label={ariaDescription}
    >
      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">Your Hold Status</p>

      {/* Desktop: horizontal */}
      <div className="hidden sm:flex items-center justify-between gap-1">
        {nodes.map((node, idx) => (
          <div key={idx} className="flex items-center flex-1 last:flex-initial">
            {/* Node */}
            <div className="flex flex-col items-center min-w-[60px]">
              <div
                className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors',
                  node.state === 'completed' && 'bg-lsc-rose border-lsc-rose text-white',
                  node.state === 'current' && [
                    'bg-lsc-rose/20 border-lsc-rose text-lsc-rose dark:text-lsc-rose-light',
                    !reduceMotion && 'motion-safe:animate-pulse',
                  ],
                  node.state === 'future' && 'bg-transparent border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 border-dashed'
                )}
              >
                {node.state === 'completed' ? '✓' : idx + 1}
              </div>
              <span className="text-xs font-medium text-lsc-dark dark:text-lsc-cream mt-1 text-center whitespace-nowrap">
                {node.label}
              </span>
              {node.sublabel && (
                <span className="text-xs text-lsc-dark/80 dark:text-lsc-cream/80 text-center">
                  {node.sublabel}
                </span>
              )}
            </div>
            {/* Connector line */}
            {idx < nodes.length - 1 && (
              <div
                className={clsx(
                  'flex-1 h-1 mx-1 rounded',
                  nodes[idx + 1]?.state === 'future' ? 'bg-lsc-border dark:bg-earth-600 border-dashed' : 'bg-lsc-rose/60'
                )}
              />
            )}
          </div>
        ))}
      </div>

      {/* Mobile: 2x2 grid */}
      <div className="grid grid-cols-2 gap-3 sm:hidden">
        {nodes.map((node, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <div
              className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 flex-shrink-0',
                node.state === 'completed' && 'bg-lsc-rose border-lsc-rose text-white',
                node.state === 'current' && [
                  'bg-lsc-rose/20 border-lsc-rose text-lsc-rose dark:text-lsc-rose-light',
                  !reduceMotion && 'motion-safe:animate-pulse',
                ],
                node.state === 'future' && 'bg-transparent border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 border-dashed'
              )}
            >
              {node.state === 'completed' ? '✓' : idx + 1}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-lsc-dark dark:text-lsc-cream truncate" title={node.label}>{node.label}</p>
              {node.sublabel && (
                <p className="text-xs text-lsc-dark/80 dark:text-lsc-cream/80 truncate" title={node.sublabel}>{node.sublabel}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
