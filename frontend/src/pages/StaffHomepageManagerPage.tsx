/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Homepage Manager Page
 * Route: /staff/homepage (staff only)
 * Manages homepage quick links and library hours (weekly schedule + overrides).
 */
import { useState, useCallback, useMemo } from 'react'
import FocusTrap from 'focus-trap-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Home, Plus, Pencil, Trash2, Eye, EyeOff, ArrowUp, ArrowDown, Loader2,
  AlertCircle, X, Clock, Link as LinkIcon, Check, ChevronRight,
  // Curated icon set for the picker
  Printer, Compass, CreditCard, Wifi, Calendar, Heart, MessageCircle,
  HelpCircle, BookOpen, Search, Phone, Users, Baby, Building2, Gavel,
  GraduationCap, Globe, Package, PenTool, Monitor, Cpu, MapPin,
  Coffee, Music, Palette, Bookmark, Shield, Truck, Utensils,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import {
  getAllQuickLinks, createQuickLink, updateQuickLink, deleteQuickLink, reorderQuickLinks,
  getLibraryHours, updateWeeklyHours, createHoursOverride, updateHoursOverride, deleteHoursOverride,
  type QuickLink, type QuickLinkCreate, type QuickLinkUpdate,
  type DayHours, type HoursOverride, type LibraryHoursResponse,
} from '@/api/domains/content/homepage-content-api'
import { AdminShell } from '../components/shells/AdminShell'
import { t, getCurrentLocale } from '@/i18n'

// ─── Icon registry ───────────────────────────────────────────────

const ICON_MAP: Record<string, LucideIcon> = {
  printer: Printer, compass: Compass, 'credit-card': CreditCard, wifi: Wifi,
  calendar: Calendar, heart: Heart, 'message-circle': MessageCircle,
  'help-circle': HelpCircle, 'book-open': BookOpen, search: Search,
  phone: Phone, users: Users, baby: Baby, 'building-2': Building2,
  gavel: Gavel, 'graduation-cap': GraduationCap, globe: Globe,
  package: Package, 'pen-tool': PenTool, monitor: Monitor, cpu: Cpu,
  'map-pin': MapPin, clock: Clock, coffee: Coffee, music: Music,
  palette: Palette, bookmark: Bookmark, shield: Shield, truck: Truck,
  utensils: Utensils,
}

const ICON_OPTIONS = Object.keys(ICON_MAP)

function IconPreview({ name, className }: { name: string; className?: string }) {
  const Comp = ICON_MAP[name]
  if (!Comp) return <span className={clsx('inline-block w-4 h-4', className)} />
  return <Comp className={clsx('w-4 h-4', className)} aria-hidden="true" />
}

// ─── Day helpers ─────────────────────────────────────────────────

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

// ─── Quick Link form state ───────────────────────────────────────

interface QLFormData {
  label: string
  icon: string
  url: string
  is_active: boolean
}

const EMPTY_QL: QLFormData = { label: '', icon: 'link', url: '', is_active: true }

// ─── Override form state ─────────────────────────────────────────

interface OverrideFormData {
  date: string
  open_time: string
  close_time: string
  is_closed: boolean
  reason: string
}

const EMPTY_OVERRIDE: OverrideFormData = { date: '', open_time: '09:00', close_time: '17:00', is_closed: false, reason: '' }

// ─── Toast component ─────────────────────────────────────────────

type ToastType = 'success' | 'error'

function Toast({ message, type, onDismiss }: { message: string; type: ToastType; onDismiss: () => void }) {
  return (
    <div
      role={type === 'success' ? 'status' : 'alert'}
      aria-live={type === 'success' ? 'polite' : 'assertive'}
      className={clsx(
        'fixed top-4 right-4 z-[60] flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium animate-in slide-in-from-right',
        type === 'success' ? 'bg-status-success-600 text-white' : 'bg-status-danger-600 text-white',
      )}>
      {type === 'success' ? <Check className="w-4 h-4" aria-hidden="true" /> : <AlertCircle className="w-4 h-4" aria-hidden="true" />}
      {message}
      <button onClick={onDismiss} className="ml-2 inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-white/20 rounded-lg" aria-label={t('aria.account.dismiss')}>
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════
//  Main component
// ═════════════════════════════════════════════════════════════════

type Tab = 'quick-links' | 'library-hours'

export default function StaffHomepageManagerPage(): React.ReactElement {
  const qc = useQueryClient()

  // ─── Global state ────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<Tab>('quick-links')
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null)

  const showToast = useCallback((message: string, type: ToastType) => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }, [])

  // ─── Quick Links state ───────────────────────────────────────
  const [qlModal, setQlModal] = useState(false)
  const [qlEditId, setQlEditId] = useState<number | null>(null)
  const [qlForm, setQlForm] = useState<QLFormData>(EMPTY_QL)
  const [qlDeleteId, setQlDeleteId] = useState<number | null>(null)
  const [iconPickerOpen, setIconPickerOpen] = useState(false)

  // ─── Library Hours state ─────────────────────────────────────
  const [weeklyEdits, setWeeklyEdits] = useState<DayHours[] | null>(null)
  const [overrideModal, setOverrideModal] = useState(false)
  const [overrideEditId, setOverrideEditId] = useState<number | null>(null)
  const [overrideForm, setOverrideForm] = useState<OverrideFormData>(EMPTY_OVERRIDE)
  const [overrideDeleteId, setOverrideDeleteId] = useState<number | null>(null)

  // ─── Queries ─────────────────────────────────────────────────

  const { data: quickLinks = [], isLoading: qlLoading, error: qlError } = useQuery<QuickLink[]>({
    queryKey: ['staff-quick-links'],
    queryFn: getAllQuickLinks,
  })

  const { data: hoursData, isLoading: hoursLoading, error: hoursError } = useQuery<LibraryHoursResponse>({
    queryKey: ['staff-library-hours'],
    queryFn: getLibraryHours,
  })

  const weekly = useMemo(() => weeklyEdits ?? hoursData?.weekly ?? [], [weeklyEdits, hoursData])
  const overrides = useMemo(() => hoursData?.overrides ?? [], [hoursData])

  // ─── Quick Links mutations ───────────────────────────────────

  const qlSaveMut = useMutation({
    mutationFn: async () => {
      const payload: QuickLinkCreate | QuickLinkUpdate = {
        label: qlForm.label,
        icon: qlForm.icon,
        url: qlForm.url,
        is_active: qlForm.is_active,
      }
      if (qlEditId) return updateQuickLink(qlEditId, payload)
      return createQuickLink(payload as QuickLinkCreate)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['staff-quick-links'] })
      closeQlModal()
      showToast(qlEditId ? 'Quick link updated' : 'Quick link created', 'success')
    },
    onError: () => showToast('Failed to save quick link', 'error'),
  })

  const qlDeleteMut = useMutation({
    mutationFn: (id: number) => deleteQuickLink(id),
    onMutate: async (deletedId) => {
      await qc.cancelQueries({ queryKey: ['staff-quick-links'] })
      const queryKey = ['staff-quick-links']
      const previous = qc.getQueryData<QuickLink[]>(queryKey)
      if (previous) {
        qc.setQueryData(queryKey, previous.filter(link => link.id !== deletedId))
      }
      return { previous, queryKey }
    },
    onSuccess: () => {
      setQlDeleteId(null)
      showToast('Quick link deleted', 'success')
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        qc.setQueryData(context.queryKey, context.previous)
      }
      showToast('Failed to delete quick link', 'error')
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['staff-quick-links'] })
    },
  })

  const qlReorderMut = useMutation({
    mutationFn: (items: { id: number; sort_order: number }[]) => reorderQuickLinks(items),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff-quick-links'] }),
    onError: () => showToast('Failed to reorder', 'error'),
  })

  // ─── Library Hours mutations ─────────────────────────────────

  const weeklySaveMut = useMutation({
    mutationFn: () => {
      const payload = weekly.map((d) => ({
        day_of_week: d.day_of_week,
        open_time: d.is_closed ? null : d.open_time,
        close_time: d.is_closed ? null : d.close_time,
        is_closed: d.is_closed,
        label: d.label,
      }))
      return updateWeeklyHours(payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['staff-library-hours'] })
      setWeeklyEdits(null)
      showToast('Weekly hours saved', 'success')
    },
    onError: () => showToast('Failed to save weekly hours', 'error'),
  })

  const overrideSaveMut = useMutation({
    mutationFn: async () => {
      const payload = {
        date: overrideForm.date,
        open_time: overrideForm.is_closed ? null : overrideForm.open_time || null,
        close_time: overrideForm.is_closed ? null : overrideForm.close_time || null,
        is_closed: overrideForm.is_closed,
        reason: overrideForm.reason || null,
      }
      if (overrideEditId) return updateHoursOverride(overrideEditId, payload)
      return createHoursOverride(payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['staff-library-hours'] })
      closeOverrideModal()
      showToast(overrideEditId ? 'Override updated' : 'Override created', 'success')
    },
    onError: () => showToast('Failed to save override', 'error'),
  })

  const overrideDeleteMut = useMutation({
    mutationFn: (id: number) => deleteHoursOverride(id),
    onMutate: async (deletedId) => {
      await qc.cancelQueries({ queryKey: ['staff-library-hours'] })
      const queryKey = ['staff-library-hours']
      const previous = qc.getQueryData<LibraryHoursResponse>(queryKey)
      if (previous) {
        qc.setQueryData(queryKey, {
          ...previous,
          overrides: previous.overrides.filter(override => override.id !== deletedId),
        })
      }
      return { previous, queryKey }
    },
    onSuccess: () => {
      setOverrideDeleteId(null)
      showToast('Override deleted', 'success')
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        qc.setQueryData(context.queryKey, context.previous)
      }
      showToast('Failed to delete override', 'error')
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['staff-library-hours'] })
    },
  })

  // ─── Quick Links handlers ────────────────────────────────────

  const closeQlModal = useCallback(() => {
    setQlModal(false)
    setQlEditId(null)
    setQlForm(EMPTY_QL)
    setIconPickerOpen(false)
  }, [])

  const openQlCreate = useCallback(() => {
    setQlForm(EMPTY_QL)
    setQlEditId(null)
    setQlModal(true)
  }, [])

  const openQlEdit = useCallback((link: QuickLink) => {
    setQlForm({ label: link.label, icon: link.icon, url: link.url, is_active: link.is_active })
    setQlEditId(link.id)
    setQlModal(true)
  }, [])

  const sortedLinks = useMemo(
    () => [...quickLinks].sort((a, b) => a.sort_order - b.sort_order),
    [quickLinks],
  )

  const moveLink = useCallback((linkId: number, direction: 'up' | 'down') => {
    const idx = sortedLinks.findIndex((l) => l.id === linkId)
    if (idx < 0) return
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1
    if (swapIdx < 0 || swapIdx >= sortedLinks.length) return
    const items = sortedLinks.map((l, i) => {
      if (i === idx) return { id: l.id, sort_order: swapIdx }
      if (i === swapIdx) return { id: l.id, sort_order: idx }
      return { id: l.id, sort_order: i }
    })
    qlReorderMut.mutate(items)
  }, [sortedLinks, qlReorderMut])

  // ─── Library Hours handlers ──────────────────────────────────

  const updateDay = useCallback((dayOfWeek: number, patch: Partial<DayHours>) => {
    setWeeklyEdits((prev) => {
      const base = prev ?? hoursData?.weekly ?? []
      return base.map((d) => (d.day_of_week === dayOfWeek ? { ...d, ...patch } : d))
    })
  }, [hoursData])

  const closeOverrideModal = useCallback(() => {
    setOverrideModal(false)
    setOverrideEditId(null)
    setOverrideForm(EMPTY_OVERRIDE)
  }, [])

  const openOverrideCreate = useCallback(() => {
    setOverrideForm(EMPTY_OVERRIDE)
    setOverrideEditId(null)
    setOverrideModal(true)
  }, [])

  const openOverrideEdit = useCallback((o: HoursOverride) => {
    setOverrideForm({
      date: o.date,
      open_time: o.open_time || '09:00',
      close_time: o.close_time || '17:00',
      is_closed: o.is_closed,
      reason: o.reason || '',
    })
    setOverrideEditId(o.id)
    setOverrideModal(true)
  }, [])

  const hasWeeklyChanges = weeklyEdits !== null

  // ─── Shared CSS helpers ──────────────────────────────────────

  const inputCls = 'w-full border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose/50'
  const labelCls = 'block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1'
  const btnPrimary = 'flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 text-sm'
  const btnSecondary = 'px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 rounded-lg transition-colors'

  // ─── Loading / error states ──────────────────────────────────

  const isLoading = activeTab === 'quick-links' ? qlLoading : hoursLoading
  const error = activeTab === 'quick-links' ? qlError : hoursError

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Error Loading</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Could not load homepage content. Please try again.</p>
      </div>
    )
  }

  // ═════════════════════════════════════════════════════════════
  //  Render
  // ═════════════════════════════════════════════════════════════

  return (

    <AdminShell title="Homepage Manager">    <div className="space-y-6">
      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <div>
        <h2 className="flex items-center gap-2 text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          <Home className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
          Homepage Content
        </h2>
        <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
          Manage homepage quick links and library hours
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 bg-lsc-cream/50 dark:bg-earth-800 rounded-lg p-1">
        <button
          onClick={() => setActiveTab('quick-links')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            activeTab === 'quick-links'
              ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
              : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream',
          )}
        >
          <LinkIcon className="w-4 h-4" />
          Quick Links
        </button>
        <button
          onClick={() => setActiveTab('library-hours')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            activeTab === 'library-hours'
              ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
              : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream',
          )}
        >
          <Clock className="w-4 h-4" />
          Library Hours
        </button>
      </div>

      {/* ─── Quick Links Tab ──────────────────────────────────── */}
      {activeTab === 'quick-links' && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">Quick Links</h2>
            <button onClick={openQlCreate} className={btnPrimary}>
              <Plus className="w-4 h-4" /> Add Quick Link
            </button>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-lsc-cream dark:bg-earth-700">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-12">Icon</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">Label</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">URL</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-20">Active</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-20">Order</th>
                    <th className="text-right px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-32">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {sortedLinks.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/50">
                        No quick links yet. Add your first one.
                      </td>
                    </tr>
                  ) : (
                    sortedLinks.map((link, idx) => (
                      <tr key={link.id} className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-lsc-cream dark:bg-earth-600">
                            <IconPreview name={link.icon} className="text-lsc-rose" />
                          </div>
                        </td>
                        <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">{link.label}</td>
                        <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/60">
                          <span className="line-clamp-1 max-w-xs" title={link.url}>{link.url}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={clsx(
                            'inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full',
                            link.is_active
                              ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-300'
                              : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-300',
                          )}>
                            {link.is_active ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                            {link.is_active ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => moveLink(link.id, 'up')}
                              disabled={idx === 0}
                              className="p-0.5 hover:bg-lsc-cream dark:hover:bg-earth-600 rounded disabled:opacity-30"
                              aria-label={t('aria.indieReadingList.moveUp')}
                            >
                              <ArrowUp className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/60" />
                            </button>
                            <button
                              onClick={() => moveLink(link.id, 'down')}
                              disabled={idx === sortedLinks.length - 1}
                              className="p-0.5 hover:bg-lsc-cream dark:hover:bg-earth-600 rounded disabled:opacity-30"
                              aria-label={t('aria.indieReadingList.moveDown')}
                            >
                              <ArrowDown className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/60" />
                            </button>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => openQlEdit(link)}
                              className="p-1.5 hover:bg-lsc-cream dark:hover:bg-earth-600 rounded-lg transition-colors"
                              aria-label={t('aria.staffEditorialManager.edit')}
                            >
                              <Pencil className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                            </button>
                            {qlDeleteId === link.id ? (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => qlDeleteMut.mutate(link.id)}
                                  className="text-xs px-2 py-1 bg-status-danger-500 text-white rounded"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => setQlDeleteId(null)}
                                  className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-600 rounded text-lsc-dark dark:text-lsc-cream"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setQlDeleteId(link.id)}
                                className="p-1.5 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors"
                                aria-label={t('aria.ui.delete')}
                              >
                                <Trash2 className="w-4 h-4 text-status-danger-500" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ─── Library Hours Tab ────────────────────────────────── */}
      {activeTab === 'library-hours' && (
        <>
          {/* Weekly Schedule */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Calendar className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                Weekly Schedule
              </h2>
              <button
                onClick={() => weeklySaveMut.mutate()}
                disabled={!hasWeeklyChanges || weeklySaveMut.isPending}
                className={btnPrimary}
              >
                {weeklySaveMut.isPending ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Save Weekly Hours
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-lsc-cream dark:bg-earth-700">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-36">Day</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">Open</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">Close</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-28">Closed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {weekly.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/50">
                        No weekly schedule configured yet.
                      </td>
                    </tr>
                  ) : (
                    [...weekly].sort((a, b) => a.day_of_week - b.day_of_week).map((day) => (
                      <tr key={day.day_of_week} className={clsx(day.is_closed && 'bg-status-danger-50/50 dark:bg-status-danger-900/10')}>
                        <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">
                          {DAY_NAMES[day.day_of_week] ?? `Day ${day.day_of_week}`}
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="time"
                            value={day.open_time || ''}
                            disabled={day.is_closed}
                            onChange={(e) => updateDay(day.day_of_week, { open_time: e.target.value || null })}
                            className={clsx(inputCls, 'max-w-[140px]', day.is_closed && 'opacity-40')}
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="time"
                            value={day.close_time || ''}
                            disabled={day.is_closed}
                            onChange={(e) => updateDay(day.day_of_week, { close_time: e.target.value || null })}
                            className={clsx(inputCls, 'max-w-[140px]', day.is_closed && 'opacity-40')}
                          />
                        </td>
                        <td className="px-4 py-3">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={day.is_closed}
                              onChange={(e) => updateDay(day.day_of_week, { is_closed: e.target.checked })}
                              className="rounded border-lsc-border dark:border-earth-600 text-status-danger-500 focus:ring-status-danger-500"
                            />
                            <span className={clsx('text-sm', day.is_closed ? 'text-status-danger-600 dark:text-status-danger-400 font-medium' : 'text-lsc-dark/70 dark:text-lsc-cream/60')}>
                              Closed
                            </span>
                          </label>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {hasWeeklyChanges && (
              <div className="px-4 py-2 bg-lsc-rose/10 dark:bg-lsc-rose/5 border-t border-lsc-border dark:border-earth-700">
                <p className="text-xs text-lsc-rose font-medium flex items-center gap-1">
                  <ChevronRight className="w-3 h-3" />
                  Unsaved changes. Click "Save Weekly Hours" to apply.
                </p>
              </div>
            )}
          </div>

          {/* Overrides */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Clock className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                Date Overrides
              </h2>
              <button onClick={openOverrideCreate} className={btnPrimary}>
                <Plus className="w-4 h-4" /> Add Override
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-lsc-cream dark:bg-earth-700">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">Date</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">Hours</th>
                    <th className="text-left px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">Reason</th>
                    <th className="text-right px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream w-32">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {overrides.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/50">
                        No date overrides. Use these for holidays and special hours.
                      </td>
                    </tr>
                  ) : (
                    [...overrides].sort((a, b) => a.date.localeCompare(b.date)).map((o) => (
                      <tr key={o.id} className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
                        <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream whitespace-nowrap">
                          {formatDate(o.date)}
                        </td>
                        <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {o.is_closed ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-300">
                              Closed
                            </span>
                          ) : (
                            <span>{formatTime(o.open_time)} - {formatTime(o.close_time)}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/60">{o.reason || '-'}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => openOverrideEdit(o)}
                              className="p-1.5 hover:bg-lsc-cream dark:hover:bg-earth-600 rounded-lg transition-colors"
                              aria-label={t('aria.staffEditorialManager.edit')}
                            >
                              <Pencil className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                            </button>
                            {overrideDeleteId === o.id ? (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => overrideDeleteMut.mutate(o.id)}
                                  className="text-xs px-2 py-1 bg-status-danger-500 text-white rounded"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => setOverrideDeleteId(null)}
                                  className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-600 rounded text-lsc-dark dark:text-lsc-cream"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setOverrideDeleteId(o.id)}
                                className="p-1.5 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors"
                                aria-label={t('aria.ui.delete')}
                              >
                                <Trash2 className="w-4 h-4 text-status-danger-500" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ─── Quick Link Modal ─────────────────────────────────── */}
      {qlModal && (
         
        // eslint-disable-next-line jsx-a11y/click-events-have-key-events
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={closeQlModal}>
          <FocusTrap active={qlModal} focusTrapOptions={{ escapeDeactivates: true }}>
          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
          <div
            role="dialog" aria-modal="true" aria-labelledby="ql-modal-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-lg max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-lsc-border dark:border-earth-700">
              <h2 id="ql-modal-title" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {qlEditId ? 'Edit Quick Link' : 'New Quick Link'}
              </h2>
              <button onClick={closeQlModal} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-cream dark:hover:bg-earth-600 rounded-lg" aria-label={t('aria.authModals.close')}>
                <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              {/* Label */}
              <div>
                <label className={labelCls}>Label *</label>
                <input
                  value={qlForm.label}
                  onChange={(e) => setQlForm({ ...qlForm, label: e.target.value })}
                  placeholder={t('placeholder.staffHomepageManager.egPrintServices')}
                  className={inputCls}
                />
              </div>

              {/* Icon picker */}
              <div>
                <label className={labelCls}>Icon *</label>
                <button
                  type="button"
                  onClick={() => setIconPickerOpen(!iconPickerOpen)}
                  className={clsx(inputCls, 'flex items-center gap-2 text-left cursor-pointer')}
                >
                  <IconPreview name={qlForm.icon} className="text-lsc-rose" />
                  <span className="flex-1">{qlForm.icon}</span>
                  <ChevronRight className={clsx('w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 transition-transform', iconPickerOpen && 'rotate-90')} />
                </button>
                {iconPickerOpen && (
                  <div className="mt-2 p-3 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-cream/50 dark:bg-earth-700/50 grid grid-cols-6 gap-2">
                    {ICON_OPTIONS.map((name) => (
                      <button
                        key={name}
                        type="button"
                        onClick={() => { setQlForm({ ...qlForm, icon: name }); setIconPickerOpen(false) }}
                        title={name}
                        className={clsx(
                          'flex flex-col items-center gap-1 p-2 rounded-lg transition-colors text-xs',
                          qlForm.icon === name
                            ? 'bg-lsc-rose text-white'
                            : 'hover:bg-lsc-cream dark:hover:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70',
                        )}
                      >
                        <IconPreview name={name} className={qlForm.icon === name ? 'text-white' : 'text-lsc-dark/70 dark:text-lsc-cream/60'} />
                        <span className="truncate w-full text-center leading-tight" title={name}>{name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* URL */}
              <div>
                <label className={labelCls}>URL *</label>
                <input
                  value={qlForm.url}
                  onChange={(e) => setQlForm({ ...qlForm, url: e.target.value })}
                  placeholder={t('placeholder.staffHomepageManager.egServicesprintingOrHttps')}
                  className={inputCls}
                />
              </div>

              {/* Active */}
              <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
                <input
                  type="checkbox"
                  checked={qlForm.is_active}
                  onChange={(e) => setQlForm({ ...qlForm, is_active: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                />
                Active (visible on homepage)
              </label>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-lsc-border dark:border-earth-700">
              <button onClick={closeQlModal} className={btnSecondary}>Cancel</button>
              <button
                onClick={() => qlSaveMut.mutate()}
                disabled={!qlForm.label || !qlForm.icon || !qlForm.url || qlSaveMut.isPending}
                className={btnPrimary}
              >
                {qlSaveMut.isPending ? 'Saving...' : qlEditId ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
          </FocusTrap>
        </div>
      )}

      {/* ─── Override Modal ───────────────────────────────────── */}
      {overrideModal && (
         
        // eslint-disable-next-line jsx-a11y/click-events-have-key-events
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={closeOverrideModal}>
          <FocusTrap active={overrideModal} focusTrapOptions={{ escapeDeactivates: true }}>
          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
          <div
            role="dialog" aria-modal="true" aria-labelledby="override-modal-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-lg max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-lsc-border dark:border-earth-700">
              <h2 id="override-modal-title" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {overrideEditId ? 'Edit Override' : 'New Override'}
              </h2>
              <button onClick={closeOverrideModal} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-cream dark:hover:bg-earth-600 rounded-lg" aria-label={t('aria.authModals.close')}>
                <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              {/* Date */}
              <div>
                <label className={labelCls}>Date *</label>
                <input
                  type="date"
                  value={overrideForm.date}
                  onChange={(e) => setOverrideForm({ ...overrideForm, date: e.target.value })}
                  className={inputCls}
                />
              </div>

              {/* Closed toggle */}
              <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
                <input
                  type="checkbox"
                  checked={overrideForm.is_closed}
                  onChange={(e) => setOverrideForm({ ...overrideForm, is_closed: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-600 text-status-danger-500 focus:ring-status-danger-500"
                />
                Closed all day
              </label>

              {/* Times (disabled when closed) */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Open Time</label>
                  <input
                    type="time"
                    value={overrideForm.open_time}
                    disabled={overrideForm.is_closed}
                    onChange={(e) => setOverrideForm({ ...overrideForm, open_time: e.target.value })}
                    className={clsx(inputCls, overrideForm.is_closed && 'opacity-40')}
                  />
                </div>
                <div>
                  <label className={labelCls}>Close Time</label>
                  <input
                    type="time"
                    value={overrideForm.close_time}
                    disabled={overrideForm.is_closed}
                    onChange={(e) => setOverrideForm({ ...overrideForm, close_time: e.target.value })}
                    className={clsx(inputCls, overrideForm.is_closed && 'opacity-40')}
                  />
                </div>
              </div>

              {/* Reason */}
              <div>
                <label className={labelCls}>Reason</label>
                <input
                  value={overrideForm.reason}
                  onChange={(e) => setOverrideForm({ ...overrideForm, reason: e.target.value })}
                  placeholder={t('placeholder.staffHomepageManager.egIndependenceDayStaff')}
                  className={inputCls}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-lsc-border dark:border-earth-700">
              <button onClick={closeOverrideModal} className={btnSecondary}>Cancel</button>
              <button
                onClick={() => overrideSaveMut.mutate()}
                disabled={!overrideForm.date || overrideSaveMut.isPending}
                className={btnPrimary}
              >
                {overrideSaveMut.isPending ? 'Saving...' : overrideEditId ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
          </FocusTrap>
        </div>
      )}
    </div>
  </AdminShell>
  )
}

// ─── Utility formatters ────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    const parts = iso.split('-').map(Number)
    const year = parts[0] ?? 0
    const month = parts[1] ?? 1
    const day = parts[2] ?? 1
    const d = new Date(year, month - 1, day)
    return d.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

function formatTime(time: string | null): string {
  if (!time) return '--:--'
  try {
    const parts = time.split(':').map(Number)
    const h = parts[0] ?? 0
    const m = parts[1] ?? 0
    const ampm = h >= 12 ? 'PM' : 'AM'
    const h12 = h % 12 || 12
    return `${h12}:${String(m).padStart(2, '0')} ${ampm}`
  } catch {
    return time
  }
}
