/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Scale,
  Users,
  FileText,
  BookOpen,
  MapPin,
  Calculator,
  Star,
  BarChart3,
  Plus,
  Search,
  Edit,
  Clock,
  Loader2,
  AlertCircle,
  Calendar,
  Phone,
  Globe,
  Eye,
  ClipboardCheck,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useRequireRole } from '@/hooks/useRequireRole'
import toast from 'react-hot-toast'
import {
  getLegalClinics, createLegalClinic, updateLegalClinic, getLegalClinic,
  getLegalProviders, createLegalProvider, updateLegalProvider, getLegalProvider,
  getLegalForms, createLegalForm, updateLegalForm, getLegalForm,
  getLegalGuides, createLegalGuide, updateLegalGuide, publishLegalGuide, getLegalGuide,
  getLegalCourts, createCourt, updateCourt, getLegalCourt,
  getDeadlineRules,
  getLegalGlossaryTerms,
  getLegalReviewCycles,
  getLegalTopics,
  createGlossaryTerm,
} from '@/api/legal-api'
import type { LegalClinic, LegalProvider, LegalForm, LegalGuide, CourtLocation } from '@/api/legal-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import { AdminShell } from '../components/shells'
import { parseDate } from '@/utils/format-utils'
import { ClinicFormModal } from '../components/legal/ClinicFormModal'
import { GuideFormModal } from '../components/legal/GuideFormModal'
import { ProviderFormModal } from '../components/legal/ProviderFormModal'
import { CourtFormModal } from '../components/legal/CourtFormModal'
import { FormFormModal } from '../components/legal/FormFormModal'
import { LegalCalculatorsTab } from '../components/legal/LegalCalculatorsTab'
import { LegalEligibilityTab } from '../components/legal/LegalEligibilityTab'
import { LegalReviewsTab } from '../components/legal/LegalReviewsTab'
import { LegalReportingTab } from '../components/legal/LegalReportingTab'

type AdminTab =
  | 'overview'
  | 'clinics'
  | 'providers'
  | 'eligibility'
  | 'forms'
  | 'guides'
  | 'courts'
  | 'calculators'
  | 'reviews'
  | 'reporting'

const TABS: { id: AdminTab; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'clinics', label: 'Clinics', icon: <Calendar className="w-4 h-4" /> },
  { id: 'providers', label: 'Providers', icon: <Users className="w-4 h-4" /> },
  { id: 'eligibility', label: 'Eligibility', icon: <ClipboardCheck className="w-4 h-4" /> },
  { id: 'forms', label: 'Forms', icon: <FileText className="w-4 h-4" /> },
  { id: 'guides', label: 'Guides', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'courts', label: 'Courts', icon: <MapPin className="w-4 h-4" /> },
  { id: 'calculators', label: 'Calculators', icon: <Calculator className="w-4 h-4" /> },
  { id: 'reviews', label: 'Reviews', icon: <Star className="w-4 h-4" /> },
  { id: 'reporting', label: 'Reporting', icon: <BarChart3 className="w-4 h-4" /> },
]

export default function AdminLegalPage(): React.ReactElement {
  const { t } = useTranslation()
  const { authLoading, isAuthorized } = useRequireRole('staffKnowledge')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<AdminTab>('overview')
  const [searchQuery, setSearchQuery] = useState('')

  // Modal open/close state
  const [showClinicModal, setShowClinicModal] = useState(false)
  const [editClinic, setEditClinic] = useState<LegalClinic | undefined>()
  const [showGuideModal, setShowGuideModal] = useState(false)
  const [editGuide, setEditGuide] = useState<LegalGuide | undefined>()
  const [showProviderModal, setShowProviderModal] = useState(false)
  const [editProvider, setEditProvider] = useState<LegalProvider | undefined>()
  const [showCourtModal, setShowCourtModal] = useState(false)
  const [editCourt, setEditCourt] = useState<CourtLocation | undefined>()
  const [showFormModal, setShowFormModal] = useState(false)
  const [editForm, setEditForm] = useState<LegalForm | undefined>()

  useEffect(() => {
    if (!authLoading && !isAuthorized) {
      navigate('/account')
    }
  }, [authLoading, isAuthorized, navigate])

  const { data: topicsData } = useQuery({
    queryKey: ['legal-topics-admin'],
    queryFn: () => getLegalTopics({ limit: 100 }),
  })

  const { data: clinicsData, isLoading: clinicsLoading } = useQuery({
    queryKey: ['legal-clinics-admin'],
    queryFn: () => getLegalClinics({ limit: 50 }),
    enabled: activeTab === 'clinics' || activeTab === 'overview',
  })

  const { data: providersData, isLoading: providersLoading } = useQuery({
    queryKey: ['legal-providers-admin'],
    queryFn: () => getLegalProviders({ limit: 50 }),
    enabled:
      activeTab === 'providers' ||
      activeTab === 'overview' ||
      activeTab === 'eligibility',
  })

  const { data: formsData, isLoading: formsLoading } = useQuery({
    queryKey: ['legal-forms-admin', searchQuery],
    queryFn: () => getLegalForms(clean({ query: searchQuery || undefined, limit: 50 })),
    enabled: activeTab === 'forms' || activeTab === 'overview',
  })

  const { data: guidesData, isLoading: guidesLoading } = useQuery({
    queryKey: ['legal-guides-admin'],
    queryFn: () => getLegalGuides({ limit: 50 }),
    enabled: activeTab === 'guides' || activeTab === 'overview',
  })

  const { data: courtsData, isLoading: courtsLoading } = useQuery({
    queryKey: ['legal-courts-admin'],
    queryFn: () => getLegalCourts({ limit: 50 }),
    enabled: activeTab === 'courts' || activeTab === 'overview',
  })

  const { data: deadlineRules, isLoading: rulesLoading } = useQuery({
    queryKey: ['legal-deadline-rules'],
    queryFn: () => getDeadlineRules(),
    enabled: activeTab === 'calculators',
  })

  const { data: glossaryData } = useQuery({
    queryKey: ['legal-glossary-admin'],
    queryFn: () => getLegalGlossaryTerms({ limit: 50 }),
    enabled: activeTab === 'reviews',
  })

  const { data: reviewCyclesData, isLoading: reviewsLoading } = useQuery({
    queryKey: ['legal-review-cycles'],
    queryFn: () => getLegalReviewCycles({ limit: 50 }),
    enabled: activeTab === 'reviews',
  })

  // ---- Clinic mutations ----
  const createClinicMutation = useMutation({
    mutationFn: (data: Parameters<typeof createLegalClinic>[0]) => createLegalClinic(data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.clinicScheduledSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['legal-clinics-admin'] })
      setShowClinicModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToScheduleClinic')),
  })

  const updateClinicMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateLegalClinic>[1] }) =>
      updateLegalClinic(id, data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.clinicUpdated'))
      queryClient.invalidateQueries({ queryKey: ['legal-clinics-admin'] })
      setEditClinic(undefined)
      setShowClinicModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToUpdateClinic')),
  })

  // ---- Guide mutations ----
  const createGuideMutation = useMutation({
    mutationFn: (data: Parameters<typeof createLegalGuide>[0]) => createLegalGuide(data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.guideCreatedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['legal-guides-admin'] })
      setShowGuideModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToCreateGuide')),
  })

  const updateGuideMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateLegalGuide>[1] }) =>
      updateLegalGuide(id, data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.guideUpdated'))
      queryClient.invalidateQueries({ queryKey: ['legal-guides-admin'] })
      setEditGuide(undefined)
      setShowGuideModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToUpdateGuide')),
  })

  const publishGuideMutation = useMutation({
    mutationFn: (guideId: number) => publishLegalGuide(guideId),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.guidePublished'))
      queryClient.invalidateQueries({ queryKey: ['legal-guides-admin'] })
    },
    onError: () => toast.error(t('admin.adminLegal.failedToPublishGuide')),
  })

  // ---- Provider mutations ----
  const createProviderMutation = useMutation({
    mutationFn: (data: Parameters<typeof createLegalProvider>[0]) => createLegalProvider(data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.providerAdded'))
      queryClient.invalidateQueries({ queryKey: ['legal-providers-admin'] })
      setShowProviderModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToAddProvider')),
  })

  const updateProviderMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateLegalProvider>[1] }) =>
      updateLegalProvider(id, data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.providerUpdated'))
      queryClient.invalidateQueries({ queryKey: ['legal-providers-admin'] })
      setEditProvider(undefined)
      setShowProviderModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToUpdateProvider')),
  })

  // ---- Court mutations ----
  const createCourtMutation = useMutation({
    mutationFn: (data: Parameters<typeof createCourt>[0]) => createCourt(data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.courtAdded'))
      queryClient.invalidateQueries({ queryKey: ['legal-courts-admin'] })
      setShowCourtModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToAddCourt')),
  })

  const updateCourtMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateCourt>[1] }) =>
      updateCourt(id, data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.courtUpdated'))
      queryClient.invalidateQueries({ queryKey: ['legal-courts-admin'] })
      setEditCourt(undefined)
      setShowCourtModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToUpdateCourt')),
  })

  // ---- Form mutations ----
  const createFormMutation = useMutation({
    mutationFn: (data: Parameters<typeof createLegalForm>[0]) => createLegalForm(data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.formAdded'))
      queryClient.invalidateQueries({ queryKey: ['legal-forms-admin'] })
      setShowFormModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToAddForm')),
  })

  const updateFormMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateLegalForm>[1] }) =>
      updateLegalForm(id, data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.formUpdated'))
      queryClient.invalidateQueries({ queryKey: ['legal-forms-admin'] })
      setEditForm(undefined)
      setShowFormModal(false)
    },
    onError: () => toast.error(t('admin.adminLegal.failedToUpdateForm')),
  })

  // ---- Glossary mutation ----
  const createGlossaryTermMutation = useMutation({
    mutationFn: (data: Parameters<typeof createGlossaryTerm>[0]) => createGlossaryTerm(data),
    onSuccess: () => {
      toast.success(t('toast.adminLegal.glossaryTermAdded'))
      queryClient.invalidateQueries({ queryKey: ['legal-glossary-admin'] })
    },
    onError: () => toast.error(t('admin.adminLegal.failedToAddGlossaryTerm')),
  })

  if (!authLoading && !isAuthorized) {
    return <></>
  }

  const topics = topicsData?.topics || []
  const clinics = clinicsData?.clinics || []
  const providers = providersData?.providers || []
  const forms = formsData?.forms || []
  const guides = guidesData?.guides || []
  const courts = courtsData?.courts || []
  const reviewCycles = reviewCyclesData?.review_cycles || []

  const formatDate = (dateStr: string) => {
    return parseDate(dateStr)?.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' }) ?? '-'
  }

  // Fetch full record before opening edit modal to avoid blanking summary-absent fields
  const openEditClinic = async (id: number) => {
    try { setEditClinic(await getLegalClinic(id)); setShowClinicModal(true) }
    catch { toast.error(t('admin.adminLegal.failedToLoadRecord')) }
  }
  const openEditProvider = async (id: number) => {
    try { setEditProvider(await getLegalProvider(id)); setShowProviderModal(true) }
    catch { toast.error(t('admin.adminLegal.failedToLoadRecord')) }
  }
  const openEditCourt = async (id: number) => {
    try { setEditCourt(await getLegalCourt(id)); setShowCourtModal(true) }
    catch { toast.error(t('admin.adminLegal.failedToLoadRecord')) }
  }
  const openEditForm = async (id: number) => {
    try { setEditForm(await getLegalForm(id)); setShowFormModal(true) }
    catch { toast.error(t('admin.adminLegal.failedToLoadRecord')) }
  }
  const openEditGuide = async (id: number) => {
    try { setEditGuide(await getLegalGuide(id)); setShowGuideModal(true) }
    catch { toast.error(t('admin.adminLegal.failedToLoadRecord')) }
  }

  const renderOverview = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Clinics Scheduled', value: clinicsData?.total ?? 0, icon: <Calendar className="w-5 h-5" />, color: 'text-lsc-rose dark:text-lsc-rose-light' },
          { label: 'Service Providers', value: providersData?.total ?? 0, icon: <Users className="w-5 h-5" />, color: 'text-status-success-600' },
          { label: 'Legal Forms', value: formsData?.total ?? 0, icon: <FileText className="w-5 h-5" />, color: 'text-category-600' },
          { label: 'Guides Published', value: (guidesData?.guides || []).filter(g => g.is_published).length, icon: <BookOpen className="w-5 h-5" />, color: 'text-lsc-rose' },
        ].map(stat => (
          <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <div className={`${stat.color} mb-2`}>{stat.icon}</div>
            <p className="text-2xl font-bold text-lsc-dark dark:text-earth-50">{stat.value}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50 mb-4">Quick Actions</h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
          <button
            onClick={() => { setActiveTab('clinics'); setShowClinicModal(true) }}
            className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Schedule Clinic
          </button>
          <button
            onClick={() => { setActiveTab('guides'); setShowGuideModal(true) }}
            className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            New Guide
          </button>
          <a
            href="/legal/wizard"
            className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm font-medium"
          >
            <Eye className="w-4 h-4" />
            View Public Page
          </a>
          <a
            href="/legal/calculators"
            className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm font-medium"
          >
            <Calculator className="w-4 h-4" />
            Test Calculators
          </a>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Upcoming Clinics</h2>
          <button
            onClick={() => setActiveTab('clinics')}
            aria-label={t('aria.adminLegal.viewAllClinics')}
            className="text-sm text-lsc-rose hover:underline"
          >
            View all
          </button>
        </div>
        {clinicsLoading ? (
          <div role="status" aria-label={t('aria.adminLegal.loadingClinics')} className="flex items-center justify-center py-6">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : clinics.length > 0 ? (
          <div className="space-y-3">
            {clinics.slice(0, 5).map(clinic => (
              <div key={clinic.id} className="flex items-center justify-between p-3 bg-lsc-cream dark:bg-earth-900/50 rounded-lg">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-earth-50 text-sm">{clinic.title}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(clinic.date)} &bull; {clinic.spots_available} spots left</p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${clinic.is_virtual ? 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light' : 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'}`}>
                  {clinic.is_virtual ? 'Virtual' : 'In-Person'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4 text-center">{t('admin.adminLegal.noClinicsScheduledYet')}</p>
        )}
      </div>

      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-status-danger-800 dark:text-status-danger-200 text-sm">Emergency Legal Services</p>
            <p className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-1">
              For emergency legal situations, patrons should be directed to the Legal Aid Hotline (1-800-555-5555) or the Emergency Legal Services page.
              Ensure all clinic and provider information is current.
            </p>
          </div>
        </div>
      </div>
    </div>
  )

  const renderClinics = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Legal Aid Clinics ({clinicsData?.total ?? 0})</h2>
        <button
          onClick={() => { setEditClinic(undefined); setShowClinicModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Schedule Clinic
        </button>
      </div>
      {clinicsLoading ? (
        <div role="status" aria-label={t('aria.adminLegal.loadingClinics')} className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : clinics.length > 0 ? (
        <div className="space-y-3">
          {clinics.map(clinic => (
            <div key={clinic.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-lsc-dark dark:text-earth-50">{clinic.title}</h3>
                    {clinic.is_virtual && (
                      <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded text-xs">Virtual</span>
                    )}
                    <span className={`px-2 py-0.5 rounded text-xs ${clinic.status === 'scheduled' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : 'bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                      {clinic.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(clinic.date)}</span>
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{clinic.start_time} - {clinic.end_time}</span>
                    {clinic.location_name && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{clinic.location_name}</span>}
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {clinic.current_registrations}/{clinic.capacity} registered
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEditClinic(clinic.id)}
                    aria-label={t('aria.adminLegal.editClinicNamed', { name: clinic.title })}
                    className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Calendar className="w-12 h-12 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark dark:text-earth-50 font-medium">No clinics scheduled</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminLegal.scheduleTheFirstLegalAid')}</p>
        </div>
      )}
    </div>
  )

  const renderProviders = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Legal Service Providers ({providersData?.total ?? 0})</h2>
        <button
          onClick={() => { setEditProvider(undefined); setShowProviderModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Provider
        </button>
      </div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <input
          type="text"
          placeholder={t('placeholder.adminLegal.searchProviders')}
          aria-label={t('aria.adminLegal.searchProviders')}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm"
        />
      </div>
      {providersLoading ? (
        <div role="status" aria-label={t('aria.adminLegal.loadingProviders')} className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : providers.length > 0 ? (
        <div className="grid gap-3">
          {providers
            .filter(p => !searchQuery || p.name.toLowerCase().includes(searchQuery.toLowerCase()))
            .map(provider => (
            <div key={provider.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-lsc-dark dark:text-earth-50">{provider.name}</h3>
                    <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-900/50 text-lsc-dark/70 dark:text-lsc-cream/70 rounded text-xs">{provider.provider_type}</span>
                    {provider.is_active ? (
                      <span className="px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded text-xs">Active</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded text-xs">Inactive</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {provider.city && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{provider.city}, {provider.state}</span>}
                    {provider.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{provider.phone}</span>}
                    {provider.virtual_services && <span className="flex items-center gap-1"><Globe className="w-3 h-3" />Virtual Services</span>}
                    {provider.accepts_walkins && <span className="text-status-success-600 dark:text-status-success-400">Walk-ins OK</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEditProvider(provider.id)}
                    aria-label={t('aria.adminLegal.editProviderNamed', { name: provider.name })}
                    className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Users className="w-12 h-12 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark dark:text-earth-50 font-medium">No providers listed</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminLegal.addLegalAidOrganizationsTo')}</p>
        </div>
      )}
    </div>
  )

  const renderForms = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Legal Forms Library ({formsData?.total ?? 0})</h2>
        <button
          onClick={() => { setEditForm(undefined); setShowFormModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Form
        </button>
      </div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <input
          type="text"
          placeholder={t('admin.adminLegal.searchFormsByTitleOr')}
          aria-label={t('admin.adminLegal.searchFormsByTitleOr2')}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm"
        />
      </div>
      {formsLoading ? (
        <div role="status" aria-label={t('aria.adminLegal.loadingForms')} className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : forms.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Form</th>
                <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Number</th>
                <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Jurisdiction</th>
                <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Difficulty</th>
                <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
              </tr>
            </thead>
            <tbody>
              {forms.map(form => (
                <tr key={form.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/50 dark:hover:bg-earth-900/30">
                  <td className="py-3 px-3">
                    <p className="font-medium text-lsc-dark dark:text-earth-50">{form.plain_language_title || form.title}</p>
                    {form.topic_name && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{form.topic_name}</p>}
                  </td>
                  <td className="py-3 px-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">{form.form_number || '-'}</td>
                  <td className="py-3 px-3 text-lsc-dark/70 dark:text-lsc-cream/70">{form.jurisdiction}</td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${form.difficulty_level === 'simple' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : form.difficulty_level === 'moderate' ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300' : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'}`}>
                      {form.difficulty_level}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${form.status === 'active' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : 'bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                      {form.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => openEditForm(form.id)}
                      aria-label={t('aria.adminLegal.editForm')}
                      className="p-1 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark dark:text-earth-50 font-medium">{t('admin.adminLegal.noFormsInLibrary')}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminLegal.uploadLegalFormsForPatrons')}</p>
        </div>
      )}
    </div>
  )

  const renderGuides = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Legal Guides ({guidesData?.total ?? 0})</h2>
        <button
          onClick={() => { setEditGuide(undefined); setShowGuideModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          New Guide
        </button>
      </div>
      {guidesLoading ? (
        <div role="status" aria-label={t('aria.adminLegal.loadingGuides')} className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : guides.length > 0 ? (
        <div className="space-y-3">
          {guides.map(guide => (
            <div key={guide.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-lsc-dark dark:text-earth-50">{guide.title}</h3>
                    {guide.is_featured && (
                      <span className="px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded text-xs">Featured</span>
                    )}
                    {guide.is_published ? (
                      <span className="px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded text-xs">Published</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70 rounded text-xs">Draft</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {guide.topic_name && <span>{guide.topic_name}</span>}
                    <span>Level: {guide.reading_level}</span>
                  </div>
                  {guide.summary && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2" title={guide.summary}>{guide.summary}</p>}
                </div>
                <div className="flex items-center gap-2">
                  {!guide.is_published && (
                    <button
                      onClick={() => publishGuideMutation.mutate(guide.id)}
                      disabled={publishGuideMutation.isPending}
                      aria-label={t('aria.adminLegal.publishGuideNamed', { name: guide.title })}
                      className="px-3 py-1.5 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 text-xs font-medium"
                    >
                      Publish
                    </button>
                  )}
                  <button
                    onClick={() => openEditGuide(guide.id)}
                    aria-label={t('aria.adminLegal.editGuide')}
                    className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <BookOpen className="w-12 h-12 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark dark:text-earth-50 font-medium">No guides created</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminLegal.createPlainLanguageLegalGuides')}</p>
        </div>
      )}
    </div>
  )

  const renderCourts = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Court Locations ({courtsData?.total ?? 0})</h2>
        <button
          onClick={() => { setEditCourt(undefined); setShowCourtModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Court
        </button>
      </div>
      {courtsLoading ? (
        <div role="status" aria-label={t('aria.adminLegal.loadingCourts')} className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : courts.length > 0 ? (
        <div className="grid gap-3">
          {courts.map(court => (
            <div key={court.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-lsc-dark dark:text-earth-50">{court.name}</h3>
                    <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-900/50 text-lsc-dark/70 dark:text-lsc-cream/70 rounded text-xs">{court.court_type}</span>
                    {court.is_active ? (
                      <span className="px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded text-xs">Active</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded text-xs">Inactive</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{court.city}, {court.state}</span>
                    {court.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{court.phone}</span>}
                    {court.has_self_help_center && <span className="text-lsc-rose dark:text-lsc-rose-light">Self-Help Center</span>}
                    {court.e_filing_available && <span className="text-status-success-600 dark:text-status-success-400">E-Filing</span>}
                  </div>
                </div>
                <button
                  onClick={() => openEditCourt(court.id)}
                  aria-label={t('aria.adminLegal.editCourt')}
                  className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  <Edit className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <MapPin className="w-12 h-12 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark dark:text-earth-50 font-medium">{t('admin.adminLegal.noCourtsInDirectory')}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminLegal.addCourtLocationsToHelp')}</p>
        </div>
      )}
    </div>
  )

  const TAB_CONTENT: Record<AdminTab, React.ReactNode> = {
    overview: renderOverview(),
    clinics: renderClinics(),
    providers: renderProviders(),
    eligibility: <LegalEligibilityTab providers={providers} />,
    forms: renderForms(),
    guides: renderGuides(),
    courts: renderCourts(),
    calculators: <LegalCalculatorsTab deadlineRules={deadlineRules} rulesLoading={rulesLoading} />,
    reviews: <LegalReviewsTab reviewCycles={reviewCycles} reviewsLoading={reviewsLoading} glossaryData={glossaryData} formatDate={formatDate} onAddGlossaryTerm={data => createGlossaryTermMutation.mutate(data)} savingGlossaryTerm={createGlossaryTermMutation.isPending} />,
    reporting: <LegalReportingTab formsTotal={formsData?.total ?? 0} clinicsTotal={clinicsData?.total ?? 0} providersTotal={providersData?.total ?? 0} guidesTotal={guidesData?.total ?? 0} courtsTotal={courtsData?.total ?? 0} />,
  }

  return (
    <AdminShell
      title="Legal Resource Admin"
      subtitle="Manage clinics, providers, forms, guides, and legal aid services"
      icon={<Scale className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />}
    >
        <div className="flex gap-6">
          <nav className="hidden md:flex flex-col w-48 flex-shrink-0 gap-1" aria-label={t('aria.adminLegal.legalAdminNavigation')}>
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? 'page' : undefined}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
                  activeTab === tab.id
                    ? 'bg-lsc-rose text-white'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="md:hidden w-full mb-4 -mx-4 px-4">
            <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1" role="tablist" aria-label={t('aria.adminLegal.legalAdminNavigation')}>
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap flex-shrink-0 transition-colors ${
                    activeTab === tab.id
                      ? 'bg-lsc-rose text-white'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 min-w-0">
            {TAB_CONTENT[activeTab]}
          </div>
        </div>

      {showClinicModal && (
        <ClinicFormModal
          onClose={() => { setShowClinicModal(false); setEditClinic(undefined) }}
          onSave={(data) => {
            if (editClinic) {
              updateClinicMutation.mutate({ id: editClinic.id, data: data as Parameters<typeof updateLegalClinic>[1] })
            } else {
              createClinicMutation.mutate(data as unknown as Parameters<typeof createLegalClinic>[0])
            }
          }}
          topics={topics}
          saving={editClinic ? updateClinicMutation.isPending : createClinicMutation.isPending}
          initial={editClinic}
        />
      )}

      {showGuideModal && (
        <GuideFormModal
          onClose={() => { setShowGuideModal(false); setEditGuide(undefined) }}
          onSave={(data) => {
            if (editGuide) {
              updateGuideMutation.mutate({ id: editGuide.id, data: data as Parameters<typeof updateLegalGuide>[1] })
            } else {
              createGuideMutation.mutate(data as unknown as Parameters<typeof createLegalGuide>[0])
            }
          }}
          topics={topics}
          saving={editGuide ? updateGuideMutation.isPending : createGuideMutation.isPending}
          initial={editGuide}
        />
      )}

      {showProviderModal && (
        <ProviderFormModal
          onClose={() => { setShowProviderModal(false); setEditProvider(undefined) }}
          onSave={(data) => {
            if (editProvider) {
              updateProviderMutation.mutate({ id: editProvider.id, data: data as Parameters<typeof updateLegalProvider>[1] })
            } else {
              createProviderMutation.mutate(data as unknown as Parameters<typeof createLegalProvider>[0])
            }
          }}
          saving={editProvider ? updateProviderMutation.isPending : createProviderMutation.isPending}
          initial={editProvider}
        />
      )}

      {showCourtModal && (
        <CourtFormModal
          onClose={() => { setShowCourtModal(false); setEditCourt(undefined) }}
          onSave={(data) => {
            if (editCourt) {
              updateCourtMutation.mutate({ id: editCourt.id, data: data as Parameters<typeof updateCourt>[1] })
            } else {
              createCourtMutation.mutate(data as unknown as Parameters<typeof createCourt>[0])
            }
          }}
          saving={editCourt ? updateCourtMutation.isPending : createCourtMutation.isPending}
          initial={editCourt}
        />
      )}

      {showFormModal && (
        <FormFormModal
          onClose={() => { setShowFormModal(false); setEditForm(undefined) }}
          onSave={(data) => {
            if (editForm) {
              updateFormMutation.mutate({ id: editForm.id, data: data as Parameters<typeof updateLegalForm>[1] })
            } else {
              createFormMutation.mutate(data as unknown as Parameters<typeof createLegalForm>[0])
            }
          }}
          topics={topics}
          saving={editForm ? updateFormMutation.isPending : createFormMutation.isPending}
          initial={editForm}
        />
      )}
    </AdminShell>
  )
}
