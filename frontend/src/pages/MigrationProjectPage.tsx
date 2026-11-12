/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Multi-phase library migration project wizard.
 *
 * Shows 6 phases as a stepper: Assessment → Catalog → Holdings → Patrons →
 * Active Circulation → Historical Data. Each phase has upload, validate,
 * dry-run, execute, and rollback steps.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  BarChart3,
  CheckCircle,
  ChevronRight,
  Lock,
  Plus,
  RefreshCw,
  Upload,
  XCircle,
} from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import {
  migrationProjectApi,
  type MigrationProjectData,
} from '@/api/migration-project-api'
import { t } from '@/i18n'
import ConfirmDialog from '@/components/ConfirmDialog'

// ── Constants ─────────────────────────────────────────────────────────────

const PHASES = [
  { key: 'assessment', label: 'Assessment', desc: 'Upload sample data for analysis' },
  { key: 'catalog', label: 'Catalog', desc: 'Import MARC records / bibliographic data' },
  { key: 'holdings', label: 'Holdings', desc: 'Import physical copies with barcodes' },
  { key: 'patrons', label: 'Patrons', desc: 'Import patron accounts' },
  { key: 'active_circulation', label: 'Active Circ', desc: 'Import checkouts, holds, fines' },
  { key: 'historical_data', label: 'History', desc: 'Import circulation history (optional)' },
]

const SOURCE_SYSTEMS = [
  { value: 'koha', label: 'Koha' },
  { value: 'sierra', label: 'Sierra / Millennium' },
  { value: 'evergreen', label: 'Evergreen' },
  { value: 'folio', label: 'FOLIO' },
  { value: 'sirsi', label: 'SirsiDynix Symphony' },
  { value: 'generic', label: 'Other / Generic' },
]

const CUTOVER_OPTIONS = [
  { value: 'big_bang', label: 'Big Bang (weekend cutover)' },
  { value: 'parallel_run', label: 'Parallel Run (2-4 weeks)' },
]

// ── Status helpers ────────────────────────────────────────────────────────

function phaseStatusIcon(status: string) {
  switch (status) {
    case 'locked':
      return <Lock className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
    case 'ready':
      return <div className="w-5 h-5 rounded-full border-2 border-status-info-500" />
    case 'uploading':
    case 'validating':
    case 'executing':
      return <RefreshCw className="w-5 h-5 text-lsc-rose motion-safe:animate-spin" />
    case 'validated':
    case 'dry_run':
      return <CheckCircle className="w-5 h-5 text-status-warning-500" />
    case 'completed':
      return <CheckCircle className="w-5 h-5 text-status-success-500" />
    case 'failed':
      return <XCircle className="w-5 h-5 text-status-danger-500" />
    case 'rolled_back':
      return <RefreshCw className="w-5 h-5 text-lsc-dark/70" />
    default:
      return <div className="w-5 h-5 rounded-full border-2 border-lsc-border" />
  }
}

function phaseStatusColor(status: string): string {
  switch (status) {
    case 'completed': return 'bg-status-success-100 dark:bg-status-success-900 text-status-success-800 dark:text-status-success-200'
    case 'failed': return 'bg-status-danger-100 dark:bg-status-danger-900 text-status-danger-800 dark:text-status-danger-200'
    case 'executing': return 'bg-status-warning-100 dark:bg-status-warning-900 text-status-warning-800 dark:text-status-warning-200'
    case 'validated': return 'bg-status-warning-100 dark:bg-status-warning-900 text-status-warning-800 dark:text-status-warning-200'
    case 'ready': return 'bg-status-info-100 dark:bg-status-info-900 text-status-info-800 dark:text-status-info-200'
    default: return 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
  }
}

// ── Main Component ────────────────────────────────────────────────────────

export default function MigrationProjectPage() {
  const [project, setProject] = useState<MigrationProjectData | null>(null)
  const [projects, setProjects] = useState<MigrationProjectData[]>([])
  const [activePhase, setActivePhase] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Create form state
  const [formName, setFormName] = useState('')
  const [formSource, setFormSource] = useState('generic')
  const [formCutover, setFormCutover] = useState('big_bang')
  const [formCatalogSize, setFormCatalogSize] = useState('')
  const [formPatronCount, setFormPatronCount] = useState('')

  // File upload state
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  // ── Load projects ───────────────────────────────────────────────────────

  const loadProjects = useCallback(async () => {
    try {
      setLoading(true)
      const data = await migrationProjectApi.listProjects(50, 0)
      setProjects(data.items)
      // Auto-select most recent in-progress project
      const active = data.items.find(p => p.status === 'in_progress' || p.status === 'created')
      if (active) {
        setProject(active)
        const firstReady = active.phases.find(p => p.status !== 'completed' && p.status !== 'locked')
        setActivePhase(firstReady?.phase || active.phases[0]?.phase || null)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadProjects()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [loadProjects])

  // ── Polling for executing phases ────────────────────────────────────────

  const startPolling = useCallback((projectId: number) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const updated = await migrationProjectApi.getProject(projectId)
        setProject(updated)
        const isExecuting = updated.phases.some(p => p.status === 'executing')
        if (!isExecuting && pollRef.current) {
          clearInterval(pollRef.current)
          pollRef.current = null
          setExecuting(false)
        }
      } catch { /* ignore polling errors */ }
    }, 2000)
  }, [])

  // ── Create project ──────────────────────────────────────────────────────

  const handleCreate = async () => {
    if (!formName.trim()) {
      setError('Project name is required')
      return
    }
    try {
      setLoading(true)
      const newProject = await migrationProjectApi.createProject({
        name: formName,
        source_system_type: formSource,
        cutover_strategy: formCutover,
        estimated_catalog_size: formCatalogSize ? parseInt(formCatalogSize) : undefined,
        estimated_patron_count: formPatronCount ? parseInt(formPatronCount) : undefined,
      })
      setProject(newProject)
      setActivePhase('assessment')
      setShowCreate(false)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  // ── Phase actions ───────────────────────────────────────────────────────

  const handleUpload = async () => {
    if (!project || !activePhase || !file) return
    try {
      setUploading(true)
      setError(null)
      await migrationProjectApi.uploadPhaseFile(project.id, activePhase, file)
      const updated = await migrationProjectApi.getProject(project.id)
      setProject(updated)
      setFile(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleExecute = async () => {
    if (!project || !activePhase) return
    try {
      setExecuting(true)
      setError(null)
      await migrationProjectApi.executePhase(project.id, activePhase)
      startPolling(project.id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Execution failed')
      setExecuting(false)
    }
  }

  const handleDryRun = async () => {
    if (!project || !activePhase) return
    try {
      setError(null)
      await migrationProjectApi.dryRunPhase(project.id, activePhase)
      // Refresh project to see updated state
      const updated = await migrationProjectApi.getProject(project.id)
      setProject(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Dry run failed')
    }
  }

  const handleRollback = async () => {
    if (!project || !activePhase) return
    setConfirmOpen(true)
    return
  }

  const executeRollback = async () => {
    if (!project || !activePhase) return
    try {
      setError(null)
      await migrationProjectApi.rollbackPhase(project.id, activePhase)
      const updated = await migrationProjectApi.getProject(project.id)
      setProject(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Rollback failed')
    }
  }

  // ── Get current phase data ──────────────────────────────────────────────

  const currentPhase = project?.phases.find(p => p.phase === activePhase)
  const phaseConfig = PHASES.find(p => p.key === activePhase)

  // ── Render ──────────────────────────────────────────────────────────────

  if (loading && !project) {
    return (
      <AdminShell title="Library Migration">
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
        </div>
        <ConfirmDialog isOpen={confirmOpen} title="Rollback phase?" message={`Are you sure you want to rollback the ${activePhase} phase? This will delete all records created in this phase and re-lock subsequent phases.`} confirmText="Rollback" confirmVariant="danger" onConfirm={() => { executeRollback(); setConfirmOpen(false) }} onCancel={() => setConfirmOpen(false)} />
    </AdminShell>
    )
  }

  return (
    <AdminShell title="Library Migration" subtitle="Migrate your catalog, patrons, and circulation from any ILS">
      <div className="space-y-6">
        {/* Error Alert */}
        {error && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-700 p-4 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-status-danger-800 dark:text-status-danger-200 font-medium">Error</p>
              <p className="text-status-danger-700 dark:text-status-danger-300 text-sm mt-1">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="text-status-danger-600 dark:text-status-danger-400 hover:underline text-sm">
              Dismiss
            </button>
          </div>
        )}

        {/* No project — show create or project list */}
        {!project ? (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div></div>
              <button
                onClick={() => setShowCreate(true)}
                className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600 flex items-center gap-2"
              >
                <Plus className="w-5 h-5" />
                New Migration
              </button>
            </div>

            {/* Create form */}
            {showCreate && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-6 space-y-4">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Create Migration Project</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Project Name *
                    </label>
                    <input
                      type="text"
                      value={formName}
                      onChange={e => setFormName(e.target.value)}
                      placeholder={t('placeholder.migrationProject.egSpringfieldPublicLibrary')}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Source System
                    </label>
                    <select
                      value={formSource}
                      onChange={e => setFormSource(e.target.value)}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    >
                      {SOURCE_SYSTEMS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Cutover Strategy
                    </label>
                    <select
                      value={formCutover}
                      onChange={e => setFormCutover(e.target.value)}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    >
                      {CUTOVER_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Est. Catalog Size
                    </label>
                    <input
                      type="number"
                      value={formCatalogSize}
                      onChange={e => setFormCatalogSize(e.target.value)}
                      placeholder={t('placeholder.migrationProject.eg50000')}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Est. Patron Count
                    </label>
                    <input
                      type="number"
                      value={formPatronCount}
                      onChange={e => setFormPatronCount(e.target.value)}
                      placeholder={t('placeholder.migrationProject.eg15000')}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
                <div className="flex gap-3 pt-2">
                  <button onClick={handleCreate} className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600">
                    Create Project
                  </button>
                  <button onClick={() => setShowCreate(false)} className="px-6 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Project list */}
            {projects.length > 0 && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
                <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Previous Projects</h3>
                </div>
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {projects.map(p => (
                    <button
                      key={p.id}
                      onClick={() => {
                        setProject(p)
                        const first = p.phases.find(ph => ph.status !== 'completed' && ph.status !== 'locked')
                        setActivePhase(first?.phase || p.phases[0]?.phase || null)
                      }}
                      className="w-full px-6 py-4 flex items-center justify-between hover:bg-lsc-cream dark:hover:bg-earth-700 text-left"
                    >
                      <div>
                        <div className="font-medium text-lsc-dark dark:text-lsc-cream">{p.name}</div>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {p.source_system_name || p.source_system_type || 'Unknown source'} &middot;{' '}
                          {p.phases.filter(ph => ph.status === 'completed').length}/{p.phases.length} phases complete
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${phaseStatusColor(p.status)}`}>
                          {p.status}
                        </span>
                        <ChevronRight className="w-5 h-5 text-lsc-dark/70" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Project view with phase stepper */
          <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
              <div>
                <button
                  onClick={() => { setProject(null); loadProjects() }}
                  className="text-sm text-lsc-rose hover:underline mb-1"
                >
                  &larr; All Projects
                </button>
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{project.name}</h2>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                  {project.source_system_type && `Source: ${project.source_system_type}`}
                  {project.cutover_strategy && ` · Strategy: ${project.cutover_strategy.replace('_', ' ')}`}
                </p>
              </div>
              <span className={`px-4 py-1.5 rounded-full text-sm font-medium ${phaseStatusColor(project.status)}`}>
                {project.status}
              </span>
            </div>

            {/* Phase Stepper */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                {PHASES.map((phase, i) => {
                  const phaseData = project.phases.find(p => p.phase === phase.key)
                  const status = phaseData?.status || 'locked'
                  const isActive = activePhase === phase.key
                  const isClickable = status !== 'locked'

                  return (
                    <React.Fragment key={phase.key}>
                      {i > 0 && (
                        <div className={`flex-1 h-0.5 mx-2 ${
                          status === 'completed' ? 'bg-status-success-500' :
                          status !== 'locked' ? 'bg-lsc-rose' :
                          'bg-earth-200 dark:bg-earth-700'
                        }`} />
                      )}
                      <button
                        onClick={() => isClickable && setActivePhase(phase.key)}
                        disabled={!isClickable}
                        className={`flex flex-col items-center min-w-[80px] transition ${
                          isClickable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                        } ${isActive ? 'scale-110' : ''}`}
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          isActive ? 'ring-2 ring-lsc-rose ring-offset-2 dark:ring-offset-gray-800' : ''
                        } ${
                          status === 'completed' ? 'bg-status-success-100 dark:bg-status-success-900' :
                          status === 'failed' ? 'bg-status-danger-100 dark:bg-status-danger-900' :
                          status !== 'locked' ? 'bg-status-warning-100 dark:bg-status-warning-900' :
                          'bg-lsc-cream dark:bg-earth-700'
                        }`}>
                          {phaseStatusIcon(status)}
                        </div>
                        <span className={`text-xs mt-1.5 font-medium ${
                          isActive ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                        }`}>
                          {phase.label}
                        </span>
                      </button>
                    </React.Fragment>
                  )
                })}
              </div>
            </div>

            {/* Active Phase Panel */}
            {currentPhase && phaseConfig && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                      {phaseConfig.label}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{phaseConfig.desc}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${phaseStatusColor(currentPhase.status)}`}>
                    {currentPhase.status}
                  </span>
                </div>

                {/* READY — show upload */}
                {(currentPhase.status === 'ready' || currentPhase.status === 'rolled_back' || currentPhase.status === 'failed') && (
                  <div className="space-y-4">
                    {currentPhase.status === 'failed' && currentPhase.error_records > 0 && (
                      <div className="bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-700 p-3 rounded-lg text-sm text-status-danger-700 dark:text-status-danger-300">
                        Previous attempt failed with {currentPhase.error_records} errors. Upload a corrected file to retry.
                      </div>
                    )}

                    <div
                      onClick={() => fileInputRef.current?.click()}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInputRef.current?.click(); } }}
                      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
                        file ? 'border-status-success-400 bg-status-success-50 dark:bg-status-success-900' : 'border-lsc-border dark:border-earth-600 hover:border-lsc-rose'
                      }`}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".csv,.tsv,.mrc,.xml,.marcxml,.json"
                        onChange={e => setFile(e.target.files?.[0] || null)}
                      />
                      {file ? (
                        <div className="space-y-2">
                          <CheckCircle className="w-8 h-8 text-status-success-500 mx-auto" />
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{file.name}</p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <Upload className="w-8 h-8 text-lsc-dark/70 mx-auto" />
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            Drop your file here or click to browse
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            CSV, TSV, MARC (.mrc, .xml), or JSON
                          </p>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={handleUpload}
                      disabled={!file || uploading}
                      className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {uploading ? <RefreshCw className="w-4 h-4 motion-safe:animate-spin" /> : <Upload className="w-4 h-4" />}
                      {uploading ? 'Uploading & Validating...' : 'Upload & Validate'}
                    </button>
                  </div>
                )}

                {/* VALIDATED — show stats and action buttons */}
                {currentPhase.status === 'validated' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-lsc-cream dark:bg-earth-700 p-4 rounded-lg">
                        <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                          {currentPhase.total_records.toLocaleString()}
                        </div>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Records</div>
                      </div>
                      <div className="bg-status-danger-50 dark:bg-status-danger-900 p-4 rounded-lg">
                        <div className="text-2xl font-bold text-status-danger-700 dark:text-status-danger-300">
                          {currentPhase.error_records}
                        </div>
                        <div className="text-sm text-status-danger-600 dark:text-status-danger-400">Errors</div>
                      </div>
                      <div className="bg-status-success-50 dark:bg-status-success-900 p-4 rounded-lg">
                        <div className="text-2xl font-bold text-status-success-700 dark:text-status-success-300">
                          {currentPhase.total_records - currentPhase.error_records}
                        </div>
                        <div className="text-sm text-status-success-600 dark:text-status-success-400">Valid</div>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={handleDryRun}
                        className="px-6 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                      >
                        Dry Run
                      </button>
                      <button
                        onClick={handleExecute}
                        disabled={executing}
                        className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600 disabled:opacity-50 flex items-center gap-2"
                      >
                        {executing ? <RefreshCw className="w-4 h-4 motion-safe:animate-spin" /> : null}
                        Execute Import
                      </button>
                    </div>
                  </div>
                )}

                {/* EXECUTING — show progress */}
                {currentPhase.status === 'executing' && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Importing records...</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {currentPhase.progress_percent}%
                        </span>
                      </div>
                      <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-3 overflow-hidden">
                        <div
                          className="bg-lsc-rose h-full transition-all duration-500"
                          style={{ width: `${currentPhase.progress_percent}%` }}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Created:</span>
                        <div className="font-bold text-status-success-600 dark:text-status-success-400">{currentPhase.created_records}</div>
                      </div>
                      <div>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Errors:</span>
                        <div className="font-bold text-status-danger-600 dark:text-status-danger-400">{currentPhase.error_records}</div>
                      </div>
                      <div>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Skipped:</span>
                        <div className="font-bold text-lsc-dark/70 dark:text-lsc-cream/70">{currentPhase.skipped_records}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* COMPLETED — show success */}
                {currentPhase.status === 'completed' && (
                  <div className="space-y-4">
                    <div className="bg-status-success-50 dark:bg-status-success-900 border border-status-success-200 dark:border-status-success-700 p-4 rounded-lg flex items-center gap-3">
                      <CheckCircle className="w-6 h-6 text-status-success-500" />
                      <div>
                        <p className="font-medium text-status-success-800 dark:text-status-success-200">Phase Complete</p>
                        <p className="text-sm text-status-success-700 dark:text-status-success-300">
                          {currentPhase.created_records.toLocaleString()} records created
                          {currentPhase.skipped_records > 0 && `, ${currentPhase.skipped_records} skipped`}
                          {currentPhase.error_records > 0 && `, ${currentPhase.error_records} errors`}
                        </p>
                      </div>
                    </div>

                    {/* Assessment report */}
                    {activePhase === 'assessment' && project.assessment_report && (
                      <div className="bg-lsc-cream dark:bg-earth-700 p-4 rounded-lg space-y-3">
                        <h4 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                          <BarChart3 className="w-4 h-4" />
                          Assessment Report
                        </h4>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                          <p>Format: {String(project.assessment_report.file_format || 'unknown')}</p>
                          <p>Records: {String(project.assessment_report.total_rows || 0)}</p>
                          <p>Readiness: <span className="font-medium">{String(project.assessment_report.readiness_score || 'unknown')}</span></p>
                        </div>
                        {Array.isArray(project.assessment_report.warnings) && (project.assessment_report.warnings as string[]).length > 0 && (
                          <div className="text-sm text-status-warning-700 dark:text-status-warning-300">
                            <p className="font-medium">Warnings:</p>
                            <ul className="list-disc pl-5">
                              {(project.assessment_report.warnings as string[]).map((w, i) => (
                                <li key={i}>{w}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    <button
                      onClick={handleRollback}
                      className="text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline"
                    >
                      Rollback this phase
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Summary cards for all phases */}
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              {project.phases.map(p => {
                const config = PHASES.find(ph => ph.key === p.phase)
                if (!config || p.status === 'locked') return null
                return (
                   
                  <div
                    key={p.phase}
                    className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4 cursor-pointer hover:ring-2 hover:ring-lsc-rose transition"
                    onClick={() => setActivePhase(p.phase)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setActivePhase(p.phase); } }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{config.label}</span>
                      {phaseStatusIcon(p.status)}
                    </div>
                    <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {p.created_records.toLocaleString()}
                    </div>
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">records created</div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
      <ConfirmDialog isOpen={confirmOpen} title="Rollback phase?" message={`Are you sure you want to rollback the ${activePhase} phase? This will delete all records created in this phase and re-lock subsequent phases.`} confirmText="Rollback" confirmVariant="danger" onConfirm={() => { executeRollback(); setConfirmOpen(false) }} onCancel={() => setConfirmOpen(false)} />
    </AdminShell>
  )
}
