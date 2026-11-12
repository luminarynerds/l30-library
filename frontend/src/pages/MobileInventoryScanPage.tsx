/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ScanBarcode,
  Loader2,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ArrowUpDown,
  Wifi,
  WifiOff,
  ChevronLeft,
  ChevronRight,
  Trophy,
  Clock,
  MapPin,
  Package,
  Cloud,
  CloudOff,
  X,
  List,
  Eye,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { getInventorySections, getSectionItems } from '@/api/mobile-scanning-api'
import { getInventoryAudits, startInventoryAudit, completeInventoryAudit } from '@/api/inventory-api'
import { useInventoryScanner } from '@/hooks/useInventoryScanner'
import type { ScanRecord } from '@/hooks/useInventoryScanner'
import type { SectionItem, InventorySection } from '@/api/mobile-scanning-api'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// ==================== Format Helpers ====================

function formatDuration(ms: number): string {
  if (ms < 0) return '--'
  const totalSec = Math.floor(ms / 1000)
  const hours = Math.floor(totalSec / 3600)
  const minutes = Math.floor((totalSec % 3600) / 60)
  const seconds = totalSec % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function formatTimeRemaining(ms: number | null): string {
  if (ms === null || ms <= 0) return '--'
  return '~' + formatDuration(ms) + ' left'
}

// ==================== Sub-Components ====================

function ScanStatusBadge({ status }: { status: ScanRecord['status'] }) {
  const configs: Record<ScanRecord['status'], { bg: string; icon: React.ReactNode; label: string }> = {
    found: {
      bg: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
      icon: <CheckCircle className="w-4 h-4" />,
      label: 'Found',
    },
    not_on_shelf: {
      bg: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
      icon: <XCircle className="w-4 h-4" />,
      label: 'Not on shelf',
    },
    out_of_order: {
      bg: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
      icon: <ArrowUpDown className="w-4 h-4" />,
      label: 'Out of order',
    },
    already_scanned: {
      bg: 'bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70',
      icon: <AlertTriangle className="w-4 h-4" />,
      label: 'Duplicate',
    },
  }
  const config = configs[status]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg}`}>
      {config.icon}
      {config.label}
    </span>
  )
}

function ProgressBar({ pct, className = '' }: { pct: number; className?: string }) {
  return (
    <div className={`h-3 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden ${className}`}>
      <div
        className="h-full rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-lsc-rose to-green-500"
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  )
}

function StatCard({
  label,
  value,
  icon,
  color = 'text-lsc-dark dark:text-lsc-cream',
}: {
  label: string
  value: string | number
  icon: React.ReactNode
  color?: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-3 border border-lsc-border dark:border-earth-700 flex items-center gap-3">
      <div className="text-lsc-dark/70 dark:text-lsc-cream/70">{icon}</div>
      <div>
        <p className={`text-lg font-bold ${color}`}>{value}</p>
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      </div>
    </div>
  )
}

// ==================== Section Picker ====================

function SectionPicker({
  sections,
  onSelect,
}: {
  sections: InventorySection[]
  onSelect: (section: InventorySection) => void
}) {
  const [search, setSearch] = useState('')
  const filtered = sections.filter((s) =>
    s.location.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="space-y-4">
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-earth-600" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('placeholder.mobileInventoryScan.searchSections')}
          className="w-full pl-10 pr-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-lg"
          autoFocus
        />
      </div>
      <div className="grid gap-2 max-h-[60vh] overflow-y-auto">
        {filtered.map((section) => (
          <button
            key={section.location}
            onClick={() => onSelect(section)}
            className="flex items-center justify-between p-4 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors text-left"
          >
            <div>
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{section.location}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {section.item_count} items
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-earth-600" />
          </button>
        ))}
        {filtered.length === 0 && (
          <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            No sections found
          </p>
        )}
      </div>
    </div>
  )
}

// ==================== Scan Feed ====================

function ScanFeed({
  records,
  onClose,
}: {
  records: ScanRecord[]
  onClose: () => void
}) {
  return (
    <ModalBackdrop onClose={onClose} title="Scan History">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-t-xl sm:rounded-xl w-full sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Scan History</h3>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 rounded-lg" aria-label={t('aria.mobileInventoryScan.closeScanHistory')}>
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-2">
          {records.length === 0 ? (
            <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No scans yet</p>
          ) : (
            [...records].reverse().map((record, i) => (
              <div key={`${record.barcode}-${i}`} className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={record.title || record.barcode}>
                    {record.title || record.barcode}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">{record.barcode}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                  <ScanStatusBadge status={record.status} />
                  {!record.synced && (
                    <CloudOff className="w-3 h-3 text-status-warning-500" aria-label={t('aria.mobileInventoryScan.pendingSync')} />
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ==================== Missing Items Panel ====================

function MissingItemsPanel({
  items,
  onClose,
}: {
  items: SectionItem[]
  onClose: () => void
}) {
  const { t } = useTranslation()
  return (
    <ModalBackdrop onClose={onClose} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-t-xl sm:rounded-xl w-full sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-status-danger-600 dark:text-status-danger-400">
            Missing Items ({items.length})
          </h3>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 rounded-lg" aria-label={t('aria.mobileInventoryScan.closeMissingItems')}>
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-2">
          {items.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="w-12 h-12 text-status-success-500 mx-auto mb-2" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('mobileInventoryScan.allItemsAccountedFor')}</p>
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id} className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg border border-status-danger-200 dark:border-status-danger-900/40">
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {item.catalog_title || 'Unknown Title'}
                </p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {item.catalog_author} &bull; {item.barcode}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ==================== Main Page ====================

type ViewState = 'section-picker' | 'scanning' | 'results'

// eslint-disable-next-line complexity
export default function MobileInventoryScanPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [viewState, setViewState] = useState<ViewState>('section-picker')
  const [selectedSection, setSelectedSection] = useState<InventorySection | null>(null)
  const [activeAuditId, setActiveAuditId] = useState<number | null>(null)
  const [showFeed, setShowFeed] = useState(false)
  const [showMissing, setShowMissing] = useState(false)
  const barcodeInputRef = useRef<HTMLInputElement>(null)
  const [barcodeInput, setBarcodeInput] = useState('')

  // Redirect non-staff
  useEffect(() => {
    if (!authLoading && (!user || user.role === 'patron')) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate('/account')
    }
  }, [authLoading, user, navigate, t])

  // Fetch sections
  const { data: sectionsData, isLoading: loadingSections } = useQuery({
    queryKey: ['inventory', 'sections'],
    queryFn: getInventorySections,
    enabled: viewState === 'section-picker',
  })

  // Fetch section items when selected
  const { data: sectionItemsData, isLoading: loadingItems } = useQuery({
    queryKey: ['inventory', 'section-items', selectedSection?.location],
    queryFn: () => getSectionItems(selectedSection!.location),
    enabled: !!selectedSection,
  })

  // Fetch active audits to find or create one
  const { data: auditsData } = useQuery({
    queryKey: ['inventory', 'audits', 'active'],
    queryFn: () => getInventoryAudits({ status: 'in_progress' }),
  })

  const sectionItems: SectionItem[] = sectionItemsData?.items ?? []

  // Scanner hook
  const scanner = useInventoryScanner(activeAuditId, selectedSection?.location ?? '', sectionItems)

  // Find or create audit when section is selected
  const handleSelectSection = useCallback(async (section: InventorySection) => {
    setSelectedSection(section)

    // Look for an active audit that matches this location
    const activeAudit = auditsData?.items.find(
      (a) => a.completed_at === null && a.location_filter?.toLowerCase().includes(section.location.toLowerCase()),
    )

    if (activeAudit) {
      setActiveAuditId(activeAudit.id)
    } else {
      // Create a new audit for this section
      try {
        const newAudit = await startInventoryAudit({
          name: `Mobile Scan: ${section.location} - ${new Date().toLocaleDateString()}`,
          location_filter: section.location,
        })
        setActiveAuditId(newAudit.id)
      } catch {
        toast.error(t('mobileInventoryScan.failedToStartAudit'))
        return
      }
    }

    setViewState('scanning')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditsData])

  // Start scanning once everything is loaded
  useEffect(() => {
    if (viewState === 'scanning' && activeAuditId && sectionItems.length > 0 && !scanner.session) {
      scanner.startSession()
    }
  }, [viewState, activeAuditId, sectionItems.length, scanner])

  // Handle barcode submission
  const handleScan = useCallback((e?: React.FormEvent) => {
    e?.preventDefault()
    const code = barcodeInput.trim()
    if (!code) return

    const result = scanner.scanBarcode(code)
    if (result) {
      setBarcodeInput('')
      // Show appropriate toast
      if (result.status === 'found') {
        toast.success(result.title ? `Found: ${result.title}` : 'Item found')
      } else if (result.status === 'not_on_shelf') {
        toast.error(t('mobileInventoryScan.notOnShelfForThis'))
      } else if (result.status === 'out_of_order') {
        toast('Out of order', { icon: '↕' })
      } else if (result.status === 'already_scanned') {
        toast('Already scanned', { icon: '⚠' })
      }
    }

    // Refocus input
    barcodeInputRef.current?.focus()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [barcodeInput, scanner])

  // Handle completing
  const handleComplete = useCallback(async () => {
    await scanner.completeSession()
    if (activeAuditId) {
      try {
        await completeInventoryAudit(activeAuditId)
      } catch { /* may already be completed */ }
    }
    setViewState('results')
  }, [scanner, activeAuditId])

  // Handle going back to section picker
  const handleBack = useCallback(() => {
    if (scanner.session?.isActive) {
      scanner.pauseSession()
    }
    setViewState('section-picker')
    setSelectedSection(null)
    setActiveAuditId(null)
  }, [scanner])

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!user || user.role === 'patron') return <></>

  return (

    <AdminShell title="Mobile Inventory Scan">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      {/* Header */}
      <header className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 sticky top-0 z-40">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {viewState !== 'section-picker' && (
              <button
                onClick={handleBack}
                className="p-2 -ml-2 text-earth-600 hover:text-earth-900 dark:text-earth-300 dark:hover:text-earth-100"
                aria-label={t('aria.mobileInventoryScan.backToSections')}
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            )}
            <div>
              <h1 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <ScanBarcode className="w-5 h-5 text-lsc-rose" />
                Inventory Scan
              </h1>
              {selectedSection && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{selectedSection.location}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Online indicator */}
            {scanner.isOnline ? (
              <Wifi className="w-4 h-4 text-status-success-500" aria-label={t('aria.mobileInventoryScan.online')} />
            ) : (
              <WifiOff className="w-4 h-4 text-status-danger-500" aria-label={t('aria.mobileInventoryScan.offline')} />
            )}

            {/* Pending sync count */}
            {scanner.pendingOfflineCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-status-warning-600 dark:text-status-warning-400">
                <CloudOff className="w-3 h-3" />
                {scanner.pendingOfflineCount}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-4 pb-24">
        {/* ==================== Section Picker ==================== */}
        {viewState === 'section-picker' && (
          <div className="space-y-4">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Select a section to start scanning inventory
            </p>
            {loadingSections ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : (
              <SectionPicker
                sections={sectionsData?.sections ?? []}
                onSelect={handleSelectSection}
              />
            )}
          </div>
        )}

        {/* ==================== Scanning View ==================== */}
        {viewState === 'scanning' && (
          <div className="space-y-4">
            {loadingItems ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : (
              <>
                {/* Encouragement banner */}
                {scanner.encouragement && (
                  <div className="bg-gradient-to-r from-lsc-rose/10 to-green-500/10 border border-lsc-rose/20 rounded-lg p-3 flex items-center gap-3">
                    <Trophy className="w-5 h-5 text-lsc-rose flex-shrink-0" />
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {scanner.encouragement}
                    </p>
                  </div>
                )}

                {/* Progress section */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {scanner.stats.completionPct}% Complete
                    </span>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {scanner.stats.totalScanned} / {scanner.stats.totalExpected}
                    </span>
                  </div>
                  <ProgressBar pct={scanner.stats.completionPct} />
                  <div className="flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDuration(scanner.stats.elapsedMs)}
                    </span>
                    <span>{formatTimeRemaining(scanner.stats.estimatedRemainingMs)}</span>
                    {scanner.stats.scanRate > 0 && (
                      <span>{scanner.stats.scanRate}/min</span>
                    )}
                  </div>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-2 gap-2">
                  <StatCard
                    label="Scanned"
                    value={scanner.stats.totalScanned}
                    icon={<CheckCircle className="w-5 h-5" />}
                    color="text-status-success-600 dark:text-status-success-400"
                  />
                  <StatCard
                    label="Not Yet Scanned"
                    value={scanner.stats.totalMissing}
                    icon={<Package className="w-5 h-5" />}
                    color="text-lsc-dark/70 dark:text-lsc-cream/70"
                  />
                  <StatCard
                    label="Out of Order"
                    value={scanner.stats.totalOutOfOrder}
                    icon={<ArrowUpDown className="w-5 h-5" />}
                    color="text-status-warning-600 dark:text-status-warning-400"
                  />
                  <StatCard
                    label="Not on Shelf"
                    value={scanner.stats.totalNotOnShelf}
                    icon={<XCircle className="w-5 h-5" />}
                    color="text-status-danger-600 dark:text-status-danger-400"
                  />
                </div>

                {/* Barcode input */}
                <form onSubmit={handleScan} className="space-y-2">
                  <div className="relative">
                    <ScanBarcode className="absolute left-3 top-1/2 -translate-y-1/2 w-6 h-6 text-lsc-rose" />
                    <input
                      ref={barcodeInputRef}
                      type="text"
                      value={barcodeInput}
                      onChange={(e) => setBarcodeInput(e.target.value)}
                      placeholder={scanner.isPaused ? 'Paused — resume to scan' : 'Scan or type barcode...'}
                      disabled={scanner.isPaused}
                      autoFocus
                      className="w-full pl-12 pr-4 py-4 rounded-lg border-2 border-lsc-rose/50 focus:border-lsc-rose bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-lg font-mono disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label={t('aria.mobileInventoryScan.barcodeInput')}
                    />
                  </div>
                </form>

                {/* Last scan result */}
                {scanner.lastScanResult && (
                  <div className={`rounded-lg p-3 border ${
                    scanner.lastScanResult.status === 'found'
                      ? 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-900/40'
                      : scanner.lastScanResult.status === 'not_on_shelf'
                        ? 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-900/40'
                        : scanner.lastScanResult.status === 'out_of_order'
                          ? 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-900/40'
                          : 'bg-earth-50 dark:bg-earth-700/50 border-lsc-border dark:border-earth-700'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={scanner.lastScanResult.title || scanner.lastScanResult.barcode}>
                          {scanner.lastScanResult.title || scanner.lastScanResult.barcode}
                        </p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">
                          {scanner.lastScanResult.barcode}
                        </p>
                      </div>
                      <ScanStatusBadge status={scanner.lastScanResult.status} />
                    </div>
                  </div>
                )}

                {/* Syncing indicator */}
                {scanner.isSyncing && (
                  <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Cloud className="w-4 h-4 motion-safe:animate-spin" />
                    Syncing scans...
                  </div>
                )}

                {/* Action buttons */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setShowFeed(true)}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700"
                  >
                    <List className="w-4 h-4" />
                    History ({scanner.session?.scanRecords.length ?? 0})
                  </button>
                  <button
                    onClick={() => setShowMissing(true)}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700"
                  >
                    <Eye className="w-4 h-4" />
                    Missing ({scanner.missingItems.length})
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* ==================== Results View ==================== */}
        {viewState === 'results' && (
          <div className="space-y-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 text-center space-y-3">
              <Trophy className="w-16 h-16 text-lsc-rose mx-auto" />
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Section Complete!
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {selectedSection?.location}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <StatCard
                label="Items Scanned"
                value={scanner.stats.totalScanned}
                icon={<CheckCircle className="w-5 h-5" />}
                color="text-status-success-600 dark:text-status-success-400"
              />
              <StatCard
                label="Missing"
                value={scanner.stats.totalMissing}
                icon={<XCircle className="w-5 h-5" />}
                color="text-status-danger-600 dark:text-status-danger-400"
              />
              <StatCard
                label="Out of Order"
                value={scanner.stats.totalOutOfOrder}
                icon={<ArrowUpDown className="w-5 h-5" />}
                color="text-status-warning-600 dark:text-status-warning-400"
              />
              <StatCard
                label="Time Taken"
                value={formatDuration(scanner.stats.elapsedMs)}
                icon={<Clock className="w-5 h-5" />}
              />
            </div>

            {scanner.missingItems.length > 0 && (
              <button
                onClick={() => setShowMissing(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/40 text-status-danger-700 dark:text-status-danger-300 font-medium"
              >
                <Eye className="w-4 h-4" />
                View {scanner.missingItems.length} Missing Items
              </button>
            )}

            <button
              onClick={() => {
                setViewState('section-picker')
                setSelectedSection(null)
                setActiveAuditId(null)
              }}
              className="w-full px-4 py-3 rounded-lg bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90"
            >
              Scan Another Section
            </button>
          </div>
        )}
      </main>

      {/* ==================== Bottom Action Bar ==================== */}
      {viewState === 'scanning' && !loadingItems && (
        <div className="fixed bottom-0 left-0 right-0 bg-lsc-white dark:bg-earth-800 border-t border-lsc-border dark:border-earth-700 z-40">
          <div className="max-w-lg mx-auto px-4 py-3 flex items-center gap-2">
            {/* Pause/Resume */}
            {scanner.isPaused ? (
              <button
                onClick={scanner.resumeSession}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-status-success-600 text-white font-medium hover:bg-status-success-700"
              >
                <Play className="w-5 h-5" />
                Resume
              </button>
            ) : (
              <button
                onClick={scanner.pauseSession}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium hover:bg-earth-300 dark:hover:bg-earth-600"
              >
                <Pause className="w-5 h-5" />
                Pause
              </button>
            )}

            {/* Complete */}
            <button
              onClick={handleComplete}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90"
            >
              <CheckCircle className="w-5 h-5" />
              Finish Section
            </button>
          </div>
        </div>
      )}

      {/* ==================== Modals ==================== */}
      {showFeed && (
        <ScanFeed
          records={scanner.session?.scanRecords ?? []}
          onClose={() => setShowFeed(false)}
        />
      )}

      {showMissing && (
        <MissingItemsPanel
          items={scanner.missingItems}
          onClose={() => setShowMissing(false)}
        />
      )}
    </div>
  </AdminShell>
  )
}
