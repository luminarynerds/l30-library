/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Library migration wizard - 7-step guided import process.
 *
 * Steps: Upload → Analyzing → Map Fields → Preview → Dry Run → Executing → Done
 */
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle, CheckCircle, Upload, RefreshCw } from 'lucide-react'
import { migrationApi, type AnalysisReport, type DryRunReport, type MigrationJob } from '../api/migration-api'
import { AdminShell } from '../components/shells'
import { useTranslation} from '@/i18n'
import { parsePlan } from '@/lib/setup-plan'

type WizardStep = 'upload' | 'analyzing' | 'map' | 'preview' | 'dry_run' | 'executing' | 'done'

/**
 * Merge a saved setup-plan field mapping against the columns actually detected
 * in the uploaded file. Applies plan entries only for columns present in the
 * file, and reports drift in both directions so nothing is silently dropped.
 */
export function mergeMappingFromPlan(
  detectedColumns: string[],
  planMapping: Record<string, string>,
): { mapping: Record<string, string>; missingFromFile: string[]; unmappedColumns: string[] } {
  const mapping: Record<string, string> = {}
  for (const col of detectedColumns) {
    if (planMapping[col]) mapping[col] = planMapping[col]
  }
  const missingFromFile = Object.keys(planMapping).filter((c) => !detectedColumns.includes(c))
  const unmappedColumns = detectedColumns.filter((c) => !mapping[c])
  return { mapping, missingFromFile, unmappedColumns }
}

const SOURCE_SYSTEMS = [
  { value: 'sirsi', label: 'Sirsi/Symphony' },
  { value: 'koha', label: 'Koha ILS' },
  { value: 'csv', label: 'Generic CSV' },
]

const STEP_LABELS: Record<WizardStep, string> = {
  upload: 'Upload File',
  analyzing: 'Analyzing',
  map: 'Map Fields',
  preview: 'Preview',
  dry_run: 'Dry Run',
  executing: 'Executing',
  done: 'Done',
}

const STEP_SEQUENCE: WizardStep[] = ['upload', 'analyzing', 'map', 'preview', 'dry_run', 'executing', 'done']

export default function MigrationWizardPage() {
  const { t } = useTranslation()
  // Wizard state
  const [step, setStep] = useState<WizardStep>('upload')
  const [job, setJob] = useState<MigrationJob | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisReport | null>(null)
  const [dryRunResult, setDryRunResult] = useState<DryRunReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Upload state
  const [sourceSystem, setSourceSystem] = useState('sirsi')
  const [file, setFile] = useState<File | null>(null)

  // Field mapping state
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({})
  const [planDrift, setPlanDrift] = useState<{ missingFromFile: string[]; unmappedColumns: string[] } | null>(null)
  const [planError, setPlanError] = useState<string | null>(null)

  // Poll ref
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const clearError = () => setError(null)

  // ── Upload Step ────────────────────────────────────────────────────────

  const handleFileSelect = (selectedFile: File | null) => {
    setFile(selectedFile)
    clearError()
  }

  const handleUpload = useCallback(async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    try {
      setStep('analyzing')
      const newJob = await migrationApi.uploadFile(file, sourceSystem)
      setJob(newJob)

      // Immediately get analysis
      const previewRes = await migrationApi.getPreview(newJob.id)
      setAnalysis(previewRes.analysis_report)
      setFieldMapping(previewRes.analysis_report.suggested_mapping || {})

      setStep('map')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setStep('upload')
    }
  }, [file, sourceSystem])

  // ── Map Fields Step ────────────────────────────────────────────────────

  const handleFieldMappingChange = (sourceCol: string, lscField: string) => {
    setFieldMapping((prev) => ({
      ...prev,
      [sourceCol]: lscField,
    }))
  }

  const handleImportPlanMapping = async (planFile: File | null) => {
    if (!planFile || !analysis) return
    setPlanError(null)
    setPlanDrift(null)
    const res = parsePlan(await planFile.text())
    if (!res.ok) {
      setPlanError(res.reason)
      return
    }
    const { mapping, missingFromFile, unmappedColumns } = mergeMappingFromPlan(
      analysis.detected_columns,
      res.plan.ils.field_mapping,
    )
    setFieldMapping(mapping)
    setPlanDrift({ missingFromFile, unmappedColumns })
  }

  const handleContinueMapping = async () => {
    if (!job) return

    try {
      const updated = await migrationApi.configure(job.id, fieldMapping, {})
      setJob(updated)
      setStep('preview')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Configuration failed')
    }
  }

  // ── Dry Run Step ────────────────────────────────────────────────────

  const handleDryRun = async () => {
    if (!job) return

    try {
      setStep('dry_run')
      const result = await migrationApi.dryRun(job.id)
      setDryRunResult(result.dry_run_report)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Dry run failed')
    }
  }

  // ── Execute Step ────────────────────────────────────────────────────

  const handleExecute = async () => {
    if (!job) return

    try {
      setStep('executing')
      await migrationApi.execute(job.id)

      // Start polling progress
      const poll = setInterval(async () => {
        try {
          const progress = await migrationApi.getStatus(job.id)
          if (progress.is_complete) {
            clearInterval(poll)
            setJob({ ...job, ...progress, progress_percent: progress.progress_percent })
            setStep('done')
          }
        } catch (err) {
          Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
        }
      }, 1000)
      pollRef.current = poll
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Execution failed')
    }
  }

  // ── Progress bar ────────────────────────────────────────────────────

  const stepIndex = STEP_SEQUENCE.indexOf(step)
  const progressPercent = ((stepIndex + 1) / STEP_SEQUENCE.length) * 100

  // ── Rendering ────────────────────────────────────────────────────────

  const renderUploadStep = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-earth-300 mb-3">
          Select source ILS system:
        </label>
        <div className="grid grid-cols-3 gap-4">
          {SOURCE_SYSTEMS.map((sys) => (
            <button
              key={sys.value}
              onClick={() => setSourceSystem(sys.value)}
              className={`p-4 border-2 rounded-lg transition ${
                sourceSystem === sys.value
                  ? 'border-lsc-rose bg-status-warning-50 dark:bg-status-warning-900'
                  : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border'
              }`}
            >
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">{sys.label}</div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-earth-300 mb-3">
          Upload your data file:
        </label>
        <FileUploadZone file={file} onFileSelect={handleFileSelect} />
      </div>

      <button
        onClick={handleUpload}
        disabled={!file}
        className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Upload & Analyze
      </button>
    </div>
  )

  const renderAnalyzingStep = () => (
    <div className="flex flex-col items-center justify-center py-12">
      <RefreshCw className="w-12 h-12 text-lsc-rose motion-safe:animate-spin mb-4" />
      <p className="text-lsc-dark/70 dark:text-earth-300">Analyzing your file...</p>
      <p className="text-sm text-lsc-dark/70 dark:text-earth-400 mt-2">
        {job && `File: ${job.original_filename}`}
      </p>
    </div>
  )

  const renderMapStep = () => (
    <div className="space-y-6">
      {analysis && (
        <>
          <div className="bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-600 p-4 rounded-lg">
            <p className="text-sm text-earth-800 dark:text-lsc-rose-light/80">
              Found <strong>{analysis.detected_columns.length}</strong> columns across{' '}
              <strong>{analysis.total_rows}</strong> rows
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-earth-300 mb-2">
              {t('migrationWizard.importMappingFromPlan', 'Import mapping from a saved setup plan')}
            </label>
            <input
              type="file"
              accept=".json,application/json"
              aria-label={t('migrationWizard.importMappingFromPlan', 'Import mapping from a saved setup plan')}
              onChange={(e) => handleImportPlanMapping(e.target.files?.[0] ?? null)}
              className="block text-sm text-lsc-dark/70 dark:text-earth-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-lsc-rose file:text-white hover:file:bg-status-warning-600"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-earth-400 mt-1">
              {t('migrationWizard.importMappingHint', 'Upload your l30-setup-plan.json to reuse the field mapping you confirmed during setup.')}
            </p>
          </div>

          {planError && (
            <div role="alert" className="bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-700 p-4 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-status-danger-600 dark:text-status-danger-300">{planError}</p>
            </div>
          )}

          {planDrift && (planDrift.missingFromFile.length > 0 || planDrift.unmappedColumns.length > 0) && (
            <div role="alert" className="bg-status-warning-50 dark:bg-status-warning-900 border border-status-warning-200 dark:border-status-warning-700 p-4 rounded-lg">
              <h4 className="font-medium text-status-warning-800 dark:text-status-warning-200 mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {t('migrationWizard.planDriftHeading', 'Plan does not fully match this file')}
              </h4>
              {planDrift.missingFromFile.length > 0 && (
                <p className="text-sm text-status-warning-700 dark:text-status-warning-300">
                  {t('migrationWizard.planColumnsMissingFromFile', 'In the plan but not in this file:')}{' '}
                  <strong>{planDrift.missingFromFile.join(', ')}</strong>
                </p>
              )}
              {planDrift.unmappedColumns.length > 0 && (
                <p className="text-sm text-status-warning-700 dark:text-status-warning-300 mt-1">
                  {t('migrationWizard.fileColumnsUnmapped', 'In this file with no plan mapping:')}{' '}
                  <strong>{planDrift.unmappedColumns.join(', ')}</strong>
                </p>
              )}
            </div>
          )}

          <div className="space-y-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('migrationWizard.mapSourceColumnsToLsc')}</h3>
            {analysis.detected_columns.map((col) => (
              <div key={col} className="flex gap-4 items-center">
                <div className="flex-1">
                  <label className="text-sm font-medium text-lsc-dark/70 dark:text-earth-300">{col}</label>
                </div>
                <div className="flex-1">
                  <input
                    type="text"
                    value={fieldMapping[col] || ''}
                    onChange={(e) => handleFieldMappingChange(col, e.target.value)}
                    placeholder={t('placeholder.migrationWizard.l30FieldName')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={handleContinueMapping}
            className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600"
          >
            Continue to Preview
          </button>
        </>
      )}
    </div>
  )

  const renderPreviewStep = () => (
    <div className="space-y-6">
      {analysis && (
        <>
          <div className="bg-earth-50 dark:bg-earth-800 p-4 rounded-lg">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">File summary:</h3>
            <ul className="text-sm text-lsc-dark/70 dark:text-earth-300 space-y-1">
              <li>
                <strong>Source system:</strong> {analysis.source_system_detected}
              </li>
              <li>
                <strong>Total rows:</strong> {analysis.total_rows}
              </li>
              <li>
                <strong>Columns detected:</strong> {analysis.detected_columns.length}
              </li>
            </ul>
          </div>

          {analysis.warnings.length > 0 && (
            <div className="bg-status-warning-50 dark:bg-status-warning-900 border border-status-warning-200 dark:border-status-warning-700 p-4 rounded-lg">
              <h4 className="font-medium text-status-warning-800 dark:text-status-warning-200 mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Warnings
              </h4>
              <ul className="text-sm text-status-warning-700 dark:text-status-warning-300 space-y-1">
                {analysis.warnings.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={handleDryRun}
            className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600"
          >
            Run Dry-Run Test
          </button>
        </>
      )}
    </div>
  )

  const renderDryRunStep = () => (
    <div className="space-y-6">
      {dryRunResult && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-status-success-50 dark:bg-status-success-900 p-4 rounded-lg">
              <div className="text-2xl font-bold text-status-success-700 dark:text-status-success-300">
                {dryRunResult.would_create}
              </div>
              <div className="text-sm text-status-success-600 dark:text-status-success-400">Would create</div>
            </div>
            <div className="bg-earth-50 dark:bg-earth-900 p-4 rounded-lg">
              <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {dryRunResult.would_update}
              </div>
              <div className="text-sm text-lsc-rose dark:text-lsc-rose-light">Would update</div>
            </div>
            <div className="bg-earth-50 dark:bg-earth-800 p-4 rounded-lg">
              <div className="text-2xl font-bold text-lsc-dark/70 dark:text-earth-300">
                {dryRunResult.would_skip}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-earth-400">Would skip</div>
            </div>
          </div>

          {dryRunResult.validation_errors.length > 0 && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-700 p-4 rounded-lg">
              <h4 className="font-medium text-status-danger-800 dark:text-status-danger-200 mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Validation Errors ({dryRunResult.validation_errors.length})
              </h4>
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300">
                Please review the mappings and try again.
              </p>
            </div>
          )}

          <button
            onClick={handleExecute}
            className="bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600"
          >
            Execute Import
          </button>
        </>
      )}
    </div>
  )

  const renderExecutingStep = () => (
    <div className="space-y-6">
      {job && (
        <>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-lsc-dark/70 dark:text-earth-300">Progress</span>
              <span className="font-medium text-lsc-dark dark:text-lsc-cream">{job.progress_percent}%</span>
            </div>
            <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-lsc-rose h-full transition-all duration-300"
                style={{ width: `${job.progress_percent}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-lsc-dark/70 dark:text-earth-400">Processed:</span>
              <div className="font-bold text-lsc-dark dark:text-lsc-cream">
                {job.processed_rows} / {job.total_rows}
              </div>
            </div>
            <div>
              <span className="text-lsc-dark/70 dark:text-earth-400">Failed:</span>
              <div className="font-bold text-status-danger-600 dark:text-status-danger-400">{job.failed_rows}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-earth-300">
            <RefreshCw className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" />
            Import in progress...
          </div>
        </>
      )}
    </div>
  )

  const renderDoneStep = () => (
    <div className="space-y-6">
      {job && (
        <>
          <div className="flex flex-col items-center justify-center py-8">
            <CheckCircle className="w-16 h-16 text-status-success-500 mb-4" />
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Migration Complete!</h2>
            <p className="text-lsc-dark/70 dark:text-earth-400 mt-2">{t('migrationWizard.yourDataHasBeenSuccessfully')}</p>
          </div>

          <div className="bg-earth-50 dark:bg-earth-800 p-4 rounded-lg space-y-2">
            <div className="text-sm">
              <span className="text-lsc-dark/70 dark:text-earth-400">Records processed:</span>
              <div className="font-bold text-lsc-dark dark:text-lsc-cream">{job.processed_rows}</div>
            </div>
            <div className="text-sm">
              <span className="text-lsc-dark/70 dark:text-earth-400">Failed rows:</span>
              <div className="font-bold text-lsc-dark dark:text-lsc-cream">{job.failed_rows}</div>
            </div>
            <div className="text-sm">
              <span className="text-lsc-dark/70 dark:text-earth-400">Completed:</span>
              <div className="font-bold text-lsc-dark dark:text-lsc-cream">
                {job.completed_at ? new Date(job.completed_at).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>

          <button
            onClick={() => window.location.href = '/staff/admin'}
            className="w-full bg-lsc-rose text-white px-6 py-2 rounded-lg hover:bg-status-warning-600"
          >
            Return to Admin Dashboard
          </button>
        </>
      )}
    </div>
  )

  return (
    <AdminShell title="Migration Wizard">
      <div className="max-w-2xl mx-auto">

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between mb-3">
            {STEP_SEQUENCE.map((s, i) => (
              <div
                key={s}
                className={`text-center text-sm font-medium ${
                  STEP_SEQUENCE.indexOf(step) >= i
                    ? 'text-lsc-rose'
                    : 'text-lsc-dark/70 dark:text-earth-600'
                }`}
              >
                <div className="text-xs">{STEP_LABELS[s]}</div>
              </div>
            ))}
          </div>
          <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2">
            <div
              className="bg-lsc-rose h-full rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-status-danger-50 dark:bg-status-danger-900 border border-status-danger-200 dark:border-status-danger-700 p-4 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-status-danger-800 dark:text-status-danger-200 font-medium">Error</p>
              <p className="text-status-danger-700 dark:text-status-danger-300 text-sm mt-1">{error}</p>
              <button
                onClick={clearError}
                className="text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline mt-2"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Content Card */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8">
          {step === 'upload' && renderUploadStep()}
          {step === 'analyzing' && renderAnalyzingStep()}
          {step === 'map' && renderMapStep()}
          {step === 'preview' && renderPreviewStep()}
          {step === 'dry_run' && renderDryRunStep()}
          {step === 'executing' && renderExecutingStep()}
          {step === 'done' && renderDoneStep()}
        </div>
      </div>
    </AdminShell>
  )
}

// ── File Upload Zone Component ────────────────────────────────────────────

interface FileUploadZoneProps {
  file: File | null
  onFileSelect: (file: File | null) => void
}

function FileUploadZone({ file, onFileSelect }: FileUploadZoneProps) {
  const { t } = useTranslation();
  const [dragActive, setDragActive] = useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files && files[0]) {
      onFileSelect(files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files[0]) {
      onFileSelect(files[0])
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); inputRef.current?.click(); } }}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
        dragActive
          ? 'border-lsc-rose bg-status-warning-50 dark:bg-status-warning-900'
          : 'border-lsc-border dark:border-earth-600 hover:border-earth-400'
      }`}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        onChange={handleChange}
        className="hidden"
        accept=".csv,.tsv,.mrc,.xml"
      />

      {file ? (
        <div className="space-y-2">
          <CheckCircle className="w-8 h-8 text-status-success-500 mx-auto" />
          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{file.name}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-earth-400">
            {(file.size / 1024 / 1024).toFixed(2)} MB
          </p>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onFileSelect(null)
            }}
            className="text-sm text-lsc-rose hover:underline"
          >
            Choose different file
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <Upload className="w-8 h-8 text-lsc-dark/70 mx-auto" />
          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t('migrationWizard.dragYourFileHereOr')}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-earth-400">
            Supported formats: CSV, TSV, MARC (.mrc, .xml)
          </p>
        </div>
      )}
    </div>
  )
}
