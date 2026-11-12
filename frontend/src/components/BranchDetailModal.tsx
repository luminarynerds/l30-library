/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useId, useState, useEffect } from 'react'
import FocusTrap from 'focus-trap-react'
import { X, MapPin, Phone, Mail, Globe, Clock, Navigation2, Accessibility, Users, Wrench, Truck, Zap } from 'lucide-react'
import { Branch, getBranchHours, getBranchTypeLabel, formatBranchAddress, isBranchOpen } from '@/api/branch-api'
import { useTranslation} from '@/i18n'

interface BranchDetailModalProps {
  branch: Branch
  isOpen: boolean
  onClose: () => void
}

export function BranchDetailModal({ branch, isOpen, onClose }: BranchDetailModalProps) {
  const { t } = useTranslation()
  const modalId = useId()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [hours, setHours] = useState<any[] | null>(null)
  const [hoursLoading, setHoursLoading] = useState(false)
  const [isCurrentlyOpen, setIsCurrentlyOpen] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setHours(null)
      return
    }

    async function loadHours() {
      try {
        setHoursLoading(true)
        const branchHours = await getBranchHours(branch.id)
        setHours(branchHours)
        setIsCurrentlyOpen(isBranchOpen(branchHours))
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
        setHours([])
      } finally {
        setHoursLoading(false)
      }
    }

    loadHours()
  }, [isOpen, branch.id])

  if (!isOpen) return null

  const getDirectionsUrl = () => {
    if (branch.latitude && branch.longitude) {
      return `https://www.google.com/maps/dir/?api=1&destination=${branch.latitude},${branch.longitude}`
    }
    return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(formatBranchAddress(branch))}`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300'
      case 'permanently_closed':
        return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300'
      case 'under_renovation':
        return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300'
      case 'temporarily_closed':
        return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300'
      case 'planned':
        return 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light'
      default:
        return 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100'
    }
  }

  const formatStatus = (status: string) => {
    return status
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  return (
    <FocusTrap>
      <div
        className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${modalId}-title`}
      >
        <div className="flex items-start justify-center min-h-screen pt-4 px-4 sm:pt-0">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-2xl w-full my-8">
            {/* Header */}
            <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-start justify-between">
              <div>
                <h2 id={`${modalId}-title`} className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {branch.name}
                </h2>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span
                    className={`px-3 py-1 text-sm font-medium rounded-full ${
                      branch.branch_type === 'bookmobile'
                        ? 'bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300'
                        : branch.branch_type === 'main'
                          ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light'
                          : 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100'
                    }`}
                  >
                    {getBranchTypeLabel(branch.branch_type, t)}
                  </span>
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(branch.status)}`}>
                    {formatStatus(branch.status)}
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-600 dark:hover:text-earth-300 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label={t('aria.authModals.close')}
              >
                <X aria-hidden="true" className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-4 space-y-6 max-h-[calc(100vh-200px)] overflow-y-auto">
              {/* Address */}
              <div>
                <div className="flex items-start gap-3">
                  <MapPin aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('contact.address', 'Address')}</p>
                    <p className="text-lsc-dark dark:text-lsc-cream mt-1">{formatBranchAddress(branch)}</p>
                  </div>
                </div>
              </div>

              {/* Contact Information */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {branch.phone && (
                  <div className="flex items-start gap-3">
                    <Phone aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-1" />
                    <div>
                      <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('contact.phone', 'Phone')}</p>
                      <a
                        href={`tel:${branch.phone}`}
                        className="text-lsc-rose dark:text-lsc-rose-light hover:underline mt-1 block"
                      >
                        {branch.phone}
                      </a>
                    </div>
                  </div>
                )}

                {branch.email && (
                  <div className="flex items-start gap-3">
                    <Mail aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-1" />
                    <div>
                      <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('contact.email', 'Email')}</p>
                      <a
                        href={`mailto:${branch.email}`}
                        className="text-lsc-rose dark:text-lsc-rose-light hover:underline mt-1 block break-all"
                      >
                        {branch.email}
                      </a>
                    </div>
                  </div>
                )}

                {branch.website && (
                  <div className="flex items-start gap-3 sm:col-span-2">
                    <Globe aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-1" />
                    <div>
                      <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.website', 'Website')}</p>
                      <a
                        href={branch.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-lsc-rose dark:text-lsc-rose-light hover:underline mt-1 block break-all"
                      >
                        {branch.website}
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {/* Hours */}
              {hours && hours.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Clock aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.hours', 'Hours')}</p>
                    {isCurrentlyOpen && (
                      <span className="px-2 py-1 text-xs font-medium bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 rounded-full">
                        {t('home.hours.openNow')}
                      </span>
                    )}
                  </div>
                  {hoursLoading ? (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{t('branches.loadingHours', 'Loading hours...')}</p>
                  ) : (
                    <div className="space-y-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {hours.map((hour) => (
                        <div key={hour.id} className="flex justify-between">
                          <span className="capitalize">{hour.day_of_week}</span>
                          <span>
                            {hour.is_closed ? (
                              t('home.hours.closed')
                            ) : hour.open_time && hour.close_time ? (
                              `${hour.open_time} - ${hour.close_time}`
                            ) : (
                              t('branches.hoursNotAvailable', 'Hours not available')
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Facilities & Amenities */}
              <div>
                <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{t('branches.facilitiesAmenities', 'Facilities & Amenities')}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {branch.is_ada_accessible && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Accessibility aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.adaAccessible', 'ADA Accessible')}</span>
                    </div>
                  )}
                  {branch.has_meeting_rooms && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Users aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.meetingRooms', 'Meeting Rooms')}</span>
                    </div>
                  )}
                  {branch.has_makerspace && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Wrench aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.makerspace', 'Makerspace')}</span>
                    </div>
                  )}
                  {branch.has_computer_lab && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Zap aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.computerLab', 'Computer Lab')}</span>
                    </div>
                  )}
                  {branch.has_drive_through && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Truck aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.driveThrough', 'Drive-Through')}</span>
                    </div>
                  )}
                  {branch.has_self_checkout && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Zap aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.selfCheckout', 'Self-Checkout')}</span>
                    </div>
                  )}
                  {branch.has_book_drop && (
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Navigation2 aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                      <span className="text-sm">{t('branches.features.bookDrop', 'Book Drop')}</span>
                    </div>
                  )}
                </div>
                {!branch.is_ada_accessible &&
                  !branch.has_meeting_rooms &&
                  !branch.has_makerspace &&
                  !branch.has_computer_lab &&
                  !branch.has_drive_through &&
                  !branch.has_self_checkout &&
                  !branch.has_book_drop && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm italic">{t('components.branchDetail.noSpecialAmenitiesListed')}</p>
                  )}
              </div>

              {/* Additional Info */}
              {(branch.square_footage || branch.parking_spaces) && (
                <div>
                  <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{t('branches.details', 'Details')}</p>
                  <div className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {branch.square_footage && (
                      <p>{t('branches.squareFootage', 'Square Footage: {{value}}').replace('{{value}}', branch.square_footage.toLocaleString())}</p>
                    )}
                    {branch.parking_spaces && <p>{t('branches.parkingSpaces', 'Parking Spaces: {{value}}').replace('{{value}}', String(branch.parking_spaces))}</p>}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-lsc-border dark:border-earth-700 flex gap-3 flex-wrap">
              <a
                href={getDirectionsUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors min-h-[44px] min-w-[44px]"
              >
                <Navigation2 aria-hidden="true" className="w-4 h-4" />
                <span>{t('branches.getDirections', 'Get Directions')}</span>
              </a>
              <button
                onClick={onClose}
                className="flex items-center justify-center px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors min-h-[44px] min-w-[44px]"
              >
                {t('common.close', 'Close')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}

export default BranchDetailModal
