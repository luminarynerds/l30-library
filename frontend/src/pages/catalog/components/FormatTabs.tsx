/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MapPin, ChevronDown } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { Button } from '@/components/ui/Button'
import type { CatalogItem } from '@/api/api'
import type { FormatVariant } from '../hooks/useRelatedFormats'
import type { HoldPositionInfo } from '../hooks/useHoldPosition'
import { getStatusConfig } from '../utils/catalogItemUtils'
import { WaitlistTimeline } from './WaitlistTimeline'
import { t } from '@/i18n'
import { catalogSignInPath } from '../utils/catalogHelpers'

interface FormatTabsProps {
  currentItem: CatalogItem
  formats: FormatVariant[]
  holdPosition: HoldPositionInfo
  onPlaceHold: () => void
  onOpenWayfinding: () => void
  reduceMotion: boolean
  isLoggedIn: boolean
}

function getAvailabilityBadge(status: string): { label: string; className: string } {
  switch (status) {
    case 'available':
      return { label: 'On the shelf now', className: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' }
    case 'checked_out':
      return { label: 'Checked out', className: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' }
    case 'on_hold':
      return { label: 'On shelf, reserved', className: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' }
    default:
      return { label: getStatusConfig(status).label, className: getStatusConfig(status).className }
  }
}

function getPrimaryAction(_item: CatalogItem, format: FormatVariant, hasHold: boolean): { label: string; variant: 'primary' | 'secondary'; disabled: boolean } {
  if (hasHold) {
    return { label: 'Hold placed', variant: 'primary', disabled: true }
  }
  // Physical items: label reflects on-shelf vs checked-out.
  const label = format.status === 'available' ? 'Request for pickup' : 'Join waitlist'
  return { label, variant: 'primary', disabled: false }
}

function getHoldHelperText(status: string): string | null {
  switch (status) {
    case 'available':
      return "This copy is on the shelf — place a hold and we'll set it aside for you."
    case 'on_hold':
      return "It's on the shelf being set aside for another reader. Place a hold to be next in line."
    case 'checked_out':
      return "Someone's reading this now. Place a hold and we'll email you when it's back."
    default:
      return null
  }
}

export function FormatTabs({
  currentItem,
  formats,
  holdPosition,
  onPlaceHold,
  onOpenWayfinding,
  reduceMotion,
  isLoggedIn,
}: FormatTabsProps): React.ReactElement {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(0)
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])
  const singleFormat = formats.length <= 1

  const handleTabKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, idx: number) => {
      let nextIdx = idx
      if (e.key === 'ArrowRight') {
        nextIdx = (idx + 1) % formats.length
      } else if (e.key === 'ArrowLeft') {
        nextIdx = (idx - 1 + formats.length) % formats.length
      } else if (e.key === 'Home') {
        nextIdx = 0
      } else if (e.key === 'End') {
        nextIdx = formats.length - 1
      } else {
        return
      }
      e.preventDefault()
      setActiveTab(nextIdx)
      tabRefs.current[nextIdx]?.focus()
    },
    [formats.length]
  )

  const handlePlaceHoldOrWaitlist = useCallback(() => {
    if (!isLoggedIn) {
      // Sign-in-and-return: LoginPage honors location.state.from, and the
      // ?action=hold deeplink re-opens the hold modal after auth.
      const { pathname, state } = catalogSignInPath(currentItem.id, { action: 'hold', title: currentItem.title })
      navigate(pathname, { state })
      return
    }
    onPlaceHold()
  }, [isLoggedIn, onPlaceHold, navigate, currentItem.id])

  const activeFormat = formats[activeTab] ?? formats[0]
  if (!activeFormat) return <></>

  const isCurrentItem = activeFormat.isCurrent
  const badge = getAvailabilityBadge(activeFormat.status)
  const action = getPrimaryAction(currentItem, activeFormat, isCurrentItem && holdPosition.hasHold)
  const isPhysical = !['ebook', 'audiobook'].includes(activeFormat.item_type)
  const holdHelperText = isPhysical ? getHoldHelperText(activeFormat.status) : null
  const showWaitlist = !['available'].includes(activeFormat.status) && holdPosition.hasHold && isCurrentItem

  return (
    <div>
      {/* Tab bar */}
      {!singleFormat && (
        <div
          role="tablist"
          aria-label={t('aria.formatTabs.availableFormats')}
          className="flex gap-1 border-b border-lsc-border dark:border-earth-700 mb-4 overflow-x-auto"
        >
          {formats.map((format, idx) => (
            <button
              key={format.id}
              ref={(el) => { tabRefs.current[idx] = el }}
              role="tab"
              id={`format-tab-${idx}`}
              aria-selected={activeTab === idx}
              aria-controls={`format-panel-${idx}`}
              tabIndex={activeTab === idx ? 0 : -1}
              onClick={() => setActiveTab(idx)}
              onKeyDown={(e) => handleTabKeyDown(e, idx)}
              className={clsx(
                'px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors -mb-px',
                activeTab === idx
                  ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                  : 'border-transparent text-lsc-dark/80 dark:text-lsc-cream/80 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border dark:hover:border-earth-600'
              )}
            >
              {format.label}
              {format.status === 'available' && (
                <>
                  <span className="ml-1.5 inline-block w-2 h-2 bg-status-success-700 rounded-full" aria-hidden="true" />
                  <span className="sr-only">{t('aria.formatTabs.available', 'Available')}</span>
                </>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Tab panel */}
      <div
        {...(!singleFormat && {
          role: 'tabpanel',
          id: `format-panel-${activeTab}`,
          'aria-labelledby': `format-tab-${activeTab}`,
        })}
        className="space-y-4"
      >
        {singleFormat && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 font-medium uppercase tracking-wide">
            {activeFormat.label} edition
          </p>
        )}
        {/* Availability badge */}
        <div className="flex items-center gap-3">
          <span className={clsx('text-sm px-3 py-1 rounded-full font-medium', badge.className)}>
            {badge.label}
          </span>
          {activeFormat.is_large_print && (
            <span className="text-sm px-3 py-1 bg-earth-50 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light/80 rounded-full font-medium">
              Large Print
            </span>
          )}
        </div>

        {/* Location info */}
        {activeFormat.location && isPhysical && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
            <MapPin className="w-4 h-4" aria-hidden="true" />
            {activeFormat.location}
          </p>
        )}

        {/* Action buttons */}
        {isCurrentItem ? (
          activeFormat.item_type === 'ebook' ? (
            <div className="space-y-2">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                {t('catalog.item.ebookNotBorrowableNote', 'This is an open-access catalog edition. Borrowable eBooks are in our indie collection.')}
              </p>
              <Link
                to="/indie"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
              >
                {t('catalog.item.browseEbooksToBorrow', 'Browse eBooks to borrow')}
              </Link>
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              <Button
                variant={action.variant}
                size="lg"
                disabled={action.disabled}
                onClick={action.disabled ? undefined : handlePlaceHoldOrWaitlist}
              >
                {action.disabled
                  ? action.label
                  : isLoggedIn
                    ? action.label
                    : t('catalog.item.signInToPlaceHold', 'Sign in to place hold')}
              </Button>

              {isPhysical && (
                <Button
                  variant="secondary"
                  onClick={onOpenWayfinding}
                  title="Shows the item's location and how to find it in the building"
                  aria-label={`Find ${currentItem.title} in the library building`}
                >
                  <MapPin className="w-5 h-5" aria-hidden="true" />
                  Find in Library
                </Button>
              )}
            </div>
          )
        ) : (
          <Button
            variant="secondary"
            onClick={() => navigate(`/catalog/${activeFormat.id}`, { state: { fromCatalog: true } })}
          >
            View this edition
          </Button>
        )}

        {isCurrentItem && holdHelperText && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {holdHelperText}
          </p>
        )}

        {!isLoggedIn && isCurrentItem && isPhysical && (
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            Sign in to place a hold or join the waitlist.
          </p>
        )}



      {/* Format comparison */}
      {formats.length > 1 && (
        <details className="mt-4 group">
          <summary className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700/50 rounded-lg select-none list-none transition-colors">
            <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" aria-hidden="true" />
            Compare formats
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700">
                  <th className="text-left py-2 pr-4 font-medium text-lsc-dark/80 dark:text-lsc-cream/80">Format</th>
                  <th className="text-left py-2 pr-4 font-medium text-lsc-dark/80 dark:text-lsc-cream/80">Status</th>
                  <th className="text-left py-2 pr-4 font-medium text-lsc-dark/80 dark:text-lsc-cream/80">Details</th>
                  <th className="text-left py-2 font-medium text-lsc-dark/80 dark:text-lsc-cream/80">Location</th>
                </tr>
              </thead>
              <tbody>
                {formats.map((format) => {
                  const fBadge = getAvailabilityBadge(format.status)
                  return (
                    <tr key={format.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 last:border-0">
                      <td className="py-2.5 pr-4">
                        <button
                          onClick={() => format.isCurrent ? undefined : navigate(`/catalog/${format.id}`, { state: { fromCatalog: true } })}
                          className={clsx(
                            'font-medium',
                            format.isCurrent
                              ? 'text-lsc-rose dark:text-lsc-rose-light cursor-default'
                              : 'text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light'
                          )}
                        >
                          {format.label}
                          {format.isCurrent && <span className="text-xs ml-1 text-lsc-dark/50 dark:text-lsc-cream/50">(current)</span>}
                        </button>
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium', fBadge.className)}>
                          {fBadge.label}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                        {format.page_count ? `${format.page_count} pages` : format.runtime_minutes ? `${Math.floor(format.runtime_minutes / 60)}h ${format.runtime_minutes % 60}m` : '\u2014'}
                      </td>
                      <td className="py-2.5 text-lsc-dark/70 dark:text-lsc-cream/70">
                        {format.location || (format.item_type === 'ebook' ? 'Digital' : '\u2014')}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </details>
      )}

        {/* Waitlist timeline */}
        {showWaitlist && (
          <WaitlistTimeline
            position={holdPosition.position}
            totalAhead={holdPosition.totalAhead}
            estimatedReadyDate={holdPosition.estimatedReadyDate}
            holdStatus={holdPosition.holdStatus}
            reduceMotion={reduceMotion}
          />
        )}
      </div>
    </div>
  )
}
