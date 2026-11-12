/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi } from '@/api/fetchApi';
import { useToast } from '@/hooks/useToast'
import {
  Play, Pause, Trash2, Eye, CheckCircle2,
  XCircle, AlertTriangle, Zap, GitBranch, Timer, Bell,
  ChevronDown, ChevronRight, RefreshCw, Settings2, Copy,
  ArrowRight, GripVertical,
} from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WorkflowStep {
  id: number
  order: number
  name: string
  step_type: 'action' | 'condition' | 'delay' | 'notification'
  action_type: string | null
  condition: string | null
  delay_duration: number | null
  delay_unit: string | null
  config: Record<string, unknown> | null
  on_success: string | null
  on_failure: string | null
}

interface Workflow {
  id: number
  name: string
  description: string | null
  trigger: 'event' | 'schedule' | 'manual'
  trigger_config: Record<string, unknown> | null
  active: boolean
  is_template: boolean
  template_name: string | null
  last_run: string | null
  run_count: number
  steps_count?: number
  steps?: WorkflowStep[]
  created_at: string | null
}

interface WorkflowExecution {
  id: number
  workflow_id: number
  triggered_by_id: number | null
  triggered_at: string | null
  completed_at: string | null
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  current_step: number | null
  context: Record<string, unknown> | null
  step_results: StepResult[] | null
  error_message: string | null
}

interface StepResult {
  step_id: number
  step_name: string
  step_type: string
  status: string
  message: string
  started_at: string
  completed_at: string
  condition_met?: boolean
  delay_minutes?: number
}

interface WorkflowTemplate {
  key: string
  name: string
  description: string
  trigger: string
  trigger_config: Record<string, unknown>
  steps_count: number
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API = `/staff/workflows`

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    return await fetchApi(path, options)
  } catch (err) {
    const message = (err as { message?: string })?.message || 'Request failed'
    throw new Error(message)
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const stepTypeIcons: Record<string, typeof Zap> = {
  action: Zap,
  condition: GitBranch,
  delay: Timer,
  notification: Bell,
}

const stepTypeColors: Record<string, string> = {
  action: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
  condition: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
  delay: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  notification: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300',
}

const statusColors: Record<string, string> = {
  running: 'text-lsc-rose dark:text-lsc-rose-light',
  completed: 'text-status-success-600 dark:text-status-success-400',
  failed: 'text-status-danger-600 dark:text-status-danger-400',
  cancelled: 'text-lsc-dark/70 dark:text-lsc-cream/70',
}

const statusIcons: Record<string, typeof CheckCircle2> = {
  running: RefreshCw,
  completed: CheckCircle2,
  failed: XCircle,
  cancelled: AlertTriangle,
}

function StepBadge({ stepType }: { stepType: string }) {
  const Icon = stepTypeIcons[stepType] || Zap
  const color = stepTypeColors[stepType] || 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      <Icon className="w-3 h-3" />
      {stepType}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const Icon = statusIcons[status] || AlertTriangle
  const color = statusColors[status] || 'text-lsc-dark/70 dark:text-lsc-cream/70'
  return (
    <span className={`inline-flex items-center gap-1 text-sm font-medium ${color}`}>
      <Icon className={`w-4 h-4 ${status === 'running' ? 'motion-safe:animate-spin' : ''}`} />
      {status}
    </span>
  )
}

function TriggerBadge({ trigger }: { trigger: string }) {
  const colors: Record<string, string> = {
    event: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
    schedule: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light',
    manual: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors[trigger] || colors.manual}`}>
      {trigger}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Step palette (drag-and-drop step builder)
// ---------------------------------------------------------------------------

const PALETTE_ITEMS = [
  { step_type: 'action', label: 'Action', icon: Zap, desc: 'Send email, update status, assign task...' },
  { step_type: 'condition', label: 'Condition', icon: GitBranch, desc: 'Check a field value to branch logic' },
  { step_type: 'delay', label: 'Delay', icon: Timer, desc: 'Wait hours or days before continuing' },
  { step_type: 'notification', label: 'Notification', icon: Bell, desc: 'Send email, SMS, or in-app alert' },
]

function StepPalette({ onAdd }: { onAdd: (stepType: string) => void }) {
  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 bg-earth-50 dark:bg-earth-900">
      <h4 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Step Palette</h4>
      <div className="grid grid-cols-2 gap-2">
        {PALETTE_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.step_type}
              onClick={() => onAdd(item.step_type)}
              className="flex items-start gap-2 p-2 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-earth-400 dark:hover:border-earth-500 hover:bg-lsc-white dark:bg-earth-800 dark:hover:bg-earth-800 transition-colors text-left"
            >
              <Icon className="w-4 h-4 mt-0.5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <div>
                <div className="text-xs font-medium text-earth-800 dark:text-earth-200">{item.label}</div>
                <div className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70">{item.desc}</div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Workflow detail panel
// ---------------------------------------------------------------------------

function WorkflowDetail({
  workflow,
  onClose: _onClose,
  onRun,
  onToggle,
}: {
  workflow: Workflow
  onClose: () => void
  onRun: () => void
  onToggle: () => void
}) {
  const { data: execData } = useQuery({
    queryKey: ['workflow-executions', workflow.id],
    queryFn: () => apiFetch<{ executions: WorkflowExecution[] }>(`${API}/${workflow.id}/executions`),
  })

  const { data: previewData } = useQuery({
    queryKey: ['workflow-preview', workflow.id],
    queryFn: () => apiFetch<{ estimated_affected_items: number; description: string }>(`${API}/${workflow.id}/preview`),
  })

  const [expandedExec, setExpandedExec] = useState<number | null>(null)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{workflow.name}</h2>
          {workflow.description && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{workflow.description}</p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <TriggerBadge trigger={workflow.trigger} />
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{workflow.steps?.length || 0} steps</span>
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{workflow.run_count} runs</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onToggle}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              workflow.active
                ? 'bg-status-success-100 text-status-success-700 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:text-status-success-300'
                : 'bg-earth-100 text-earth-600 hover:bg-earth-200 dark:hover:bg-earth-600 dark:bg-earth-800 dark:text-earth-300'
            }`}
          >
            {workflow.active ? <><Pause className="w-3.5 h-3.5 inline mr-1" /> Active</> : <><Play className="w-3.5 h-3.5 inline mr-1" /> Inactive</>}
          </button>
          <button
            onClick={onRun}
            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
          >
            <Play className="w-3.5 h-3.5 inline mr-1" />
            Run Now
          </button>
        </div>
      </div>

      {/* Live preview */}
      {previewData && previewData.estimated_affected_items > 0 && (
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
            <span className="text-sm font-medium text-earth-800 dark:text-lsc-rose-light/80">Live Preview</span>
          </div>
          <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mt-1">
            If this workflow ran today, it would affect{' '}
            <strong>{previewData.estimated_affected_items} items</strong>.{' '}
            {previewData.description}
          </p>
        </div>
      )}

      {/* Steps visual builder */}
      <div>
        <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Workflow Steps</h3>
        <div className="space-y-2">
          {workflow.steps?.map((step, idx) => (
            <div key={step.id} className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-full bg-earth-200 dark:bg-earth-700 flex items-center justify-center text-xs font-bold text-lsc-dark/70 dark:text-lsc-cream/70">
                  {idx + 1}
                </div>
                {idx < (workflow.steps?.length || 0) - 1 && (
                  <div className="w-0.5 h-6 bg-earth-200 dark:bg-earth-700" />
                )}
              </div>
              <div className="flex-1 border border-lsc-border dark:border-earth-700 rounded-lg p-3 bg-lsc-white dark:bg-earth-800">
                <div className="flex items-center gap-2 mb-1">
                  <GripVertical className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-grab" />
                  <StepBadge stepType={step.step_type} />
                  <span className="text-sm font-medium text-earth-800 dark:text-earth-200">
                    {step.name || `Step ${idx + 1}`}
                  </span>
                </div>
                {step.action_type && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-6">
                    Action: {step.action_type.replace(/_/g, ' ')}
                  </p>
                )}
                {step.condition && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-6 font-mono">
                    if {step.condition}
                  </p>
                )}
                {step.delay_duration && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-6">
                    Wait {step.delay_duration} {step.delay_unit || 'minutes'}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Execution history */}
      <div>
        <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Execution History</h3>
        {execData?.executions?.length === 0 && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No executions yet</p>
        )}
        <div className="space-y-2">
          {execData?.executions?.map((exec) => (
            <div key={exec.id} className="border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedExec(expandedExec === exec.id ? null : exec.id)}
                aria-expanded={expandedExec === exec.id}
                aria-controls={`workflow-exec-panel-${exec.id}`}
                className="w-full flex items-center justify-between p-3 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge status={exec.status} />
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {exec.triggered_at ? new Date(exec.triggered_at).toLocaleString() : 'Unknown'}
                  </span>
                  {exec.step_results && (
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {exec.step_results.length} steps executed
                    </span>
                  )}
                </div>
                {expandedExec === exec.id ? (
                  <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                )}
              </button>
              {expandedExec === exec.id && exec.step_results && (
                <div id={`workflow-exec-panel-${exec.id}`} className="border-t border-lsc-border dark:border-earth-700 p-3 bg-earth-50 dark:bg-earth-900 space-y-2">
                  {exec.step_results.map((sr, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <span className={`mt-0.5 ${
                        sr.status === 'success' ? 'text-status-success-500' :
                        sr.status === 'failed' ? 'text-status-danger-500' :
                        sr.status === 'skipped' ? 'text-lsc-dark/70 dark:text-lsc-cream/70' :
                        'text-earth-600'
                      }`}>
                        {sr.status === 'success' ? <CheckCircle2 className="w-3.5 h-3.5" /> :
                         sr.status === 'failed' ? <XCircle className="w-3.5 h-3.5" /> :
                         <ArrowRight className="w-3.5 h-3.5" />}
                      </span>
                      <div>
                        <span className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                          {sr.step_name || `Step ${i + 1}`}
                        </span>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70 ml-2">{sr.message}</span>
                      </div>
                    </div>
                  ))}
                  {exec.error_message && (
                    <div className="mt-2 p-2 bg-status-danger-50 dark:bg-status-danger-900/20 rounded text-xs text-status-danger-700 dark:text-status-danger-300">
                      Error: {exec.error_message}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Templates panel
// ---------------------------------------------------------------------------

function TemplatesPanel({ onInstantiate }: { onInstantiate: (key: string) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: () => apiFetch<{ templates: WorkflowTemplate[] }>(`${API}/templates/available`),
  })

  if (isLoading) return <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading templates...</div>

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Pre-built Templates</h3>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        Start with a proven workflow and customize it for your library.
      </p>
      {data?.templates?.map((tmpl) => (
        <div
          key={tmpl.key}
          className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 bg-lsc-white dark:bg-earth-800 hover:border-lsc-border dark:hover:border-earth-600 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-earth-800 dark:text-earth-200">{tmpl.name}</h4>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{tmpl.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <TriggerBadge trigger={tmpl.trigger} />
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{tmpl.steps_count} steps</span>
              </div>
            </div>
            <button
              onClick={() => onInstantiate(tmpl.key)}
              className="ml-3 px-3 py-1.5 rounded-lg text-xs font-medium bg-earth-800 text-white hover:bg-earth-700 dark:bg-earth-200 dark:text-earth-900 dark:hover:bg-earth-300 transition-colors flex items-center gap-1"
            >
              <Copy className="w-3 h-3" />
              Use Template
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function StaffWorkflowsPage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [tab, setTab] = useState<'workflows' | 'templates'>('workflows')
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  // Fetch all workflows
  const { data: wfData, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => apiFetch<{ workflows: Workflow[] }>(API),
  })

  // Fetch detail for selected
  const { data: detailData } = useQuery({
    queryKey: ['workflow-detail', selectedId],
    queryFn: () => apiFetch<{ workflow: Workflow }>(`${API}/${selectedId}`),
    enabled: !!selectedId,
  })

  // Mutations
  const runMutation = useMutation({
    mutationFn: (id: number) => apiFetch(`${API}/${id}/run`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      queryClient.invalidateQueries({ queryKey: ['workflow-executions', selectedId] })
      queryClient.invalidateQueries({ queryKey: ['workflow-detail', selectedId] })
      toast({ message: 'Workflow run started', type: 'success' })
    },
    onError: () => {
      toast({ message: 'Failed to run workflow', type: 'error' })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (id: number) => apiFetch(`${API}/${id}/toggle`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      queryClient.invalidateQueries({ queryKey: ['workflow-detail', selectedId] })
      toast({ message: 'Workflow status updated', type: 'success' })
    },
    onError: () => {
      toast({ message: 'Failed to update workflow status', type: 'error' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiFetch(`${API}/${id}`, { method: 'DELETE' }),
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({ queryKey: ['workflows'] })
      const queryKey = ['workflows']
      const previous = queryClient.getQueryData<{ workflows: Workflow[] }>(queryKey)
      if (previous) {
        queryClient.setQueryData(queryKey, {
          ...previous,
          workflows: previous.workflows.filter(w => w.id !== deletedId),
        })
      }
      return { previous, queryKey }
    },
    onSuccess: () => {
      setSelectedId(null)
      toast({ message: 'Workflow deleted', type: 'success' })
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(context.queryKey, context.previous)
      }
      toast({ message: 'Failed to delete workflow', type: 'error' })
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    },
  })

  const instantiateMutation = useMutation({
    mutationFn: (key: string) =>
      apiFetch(`${API}/templates/${key}/instantiate`, { method: 'POST' }),
    onSuccess: () => {
      setTab('workflows')
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      toast({ message: 'Workflow created from template', type: 'success' })
    },
    onError: () => {
      toast({ message: 'Failed to create workflow from template', type: 'error' })
    },
  })

  const workflows = wfData?.workflows || []
  const selectedWorkflow = detailData?.workflow || null

  return (

    <AdminShell title="Workflow Automation" subtitle="Create automated multi-step processes that run without manual intervention.">    <PageContainer width="wide" className="py-8">
      {/* Page header */}
      <div className="mb-8">
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-4 border-b border-lsc-border dark:border-earth-700 mb-6">
        <button
          onClick={() => setTab('workflows')}
          className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'workflows'
              ? 'border-earth-800 text-earth-900 dark:border-lsc-border dark:text-earth-100'
              : 'border-transparent text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300'
          }`}
        >
          My Workflows ({workflows.length})
        </button>
        <button
          onClick={() => setTab('templates')}
          className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'templates'
              ? 'border-earth-800 text-earth-900 dark:border-lsc-border dark:text-earth-100'
              : 'border-transparent text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300'
          }`}
        >
          Templates
        </button>
      </div>

      {tab === 'templates' ? (
        <TemplatesPanel onInstantiate={(key) => instantiateMutation.mutate(key)} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflow list */}
          <div className="lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Workflows</h3>
            </div>

            {isLoading && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p>}
            {!isLoading && workflows.length === 0 && (
              <div className="text-center py-8 border border-dashed border-lsc-border dark:border-earth-700 rounded-xl">
                <Settings2 className="w-8 h-8 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-2" />
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No workflows yet</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Start from a template or create a custom workflow
                </p>
                <button
                  onClick={() => setTab('templates')}
                  className="mt-3 px-3 py-1.5 rounded-lg text-xs font-medium bg-earth-800 text-white hover:bg-earth-700 dark:bg-earth-200 dark:text-earth-900 transition-colors"
                >
                  Browse Templates
                </button>
              </div>
            )}

            {workflows.map((w) => (
              <button
                key={w.id}
                onClick={() => setSelectedId(w.id)}
                className={`w-full text-left border rounded-xl p-4 transition-colors ${
                  selectedId === w.id
                    ? 'border-earth-400 bg-earth-50 dark:border-earth-700 dark:bg-earth-800'
                    : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-600'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-earth-800 dark:text-earth-200 truncate" title={w.name}>
                    {w.name}
                  </span>
                  <span className={`w-2 h-2 rounded-full ${w.active ? 'bg-status-success-500' : 'bg-earth-400'}`} />
                </div>
                <div className="flex items-center gap-2">
                  <TriggerBadge trigger={w.trigger} />
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{w.steps_count || 0} steps</span>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{w.run_count} runs</span>
                </div>
                {w.last_run && (
                  <p className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    Last run: {new Date(w.last_run).toLocaleString()}
                  </p>
                )}
              </button>
            ))}

            {/* Step palette */}
            <div className="mt-4">
              <StepPalette onAdd={(_stepType) => {
                // In a full implementation this would open a step config modal
                // For now, it serves as a visual reference
              }} />
            </div>
          </div>

          {/* Detail pane */}
          <div className="lg:col-span-2">
            {selectedWorkflow ? (
              <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-6 bg-lsc-white dark:bg-earth-800/50">
                <WorkflowDetail
                  workflow={selectedWorkflow}
                  onClose={() => setSelectedId(null)}
                  onRun={() => runMutation.mutate(selectedWorkflow.id)}
                  onToggle={() => toggleMutation.mutate(selectedWorkflow.id)}
                />

                {/* Delete button */}
                <div className="mt-6 pt-4 border-t border-lsc-border dark:border-earth-700">
                  {confirmDeleteId === selectedWorkflow.id ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-status-danger-600 dark:text-status-danger-400">Delete this workflow?</span>
                      <button
                        onClick={() => { deleteMutation.mutate(selectedWorkflow.id); setConfirmDeleteId(null) }}
                        className="text-xs px-2 py-1 bg-status-danger-600 text-white rounded hover:bg-status-danger-700"
                      >
                        Yes, delete
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-xs px-2 py-1 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded hover:bg-earth-300 dark:hover:bg-earth-600"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmDeleteId(selectedWorkflow.id)}
                      className="text-xs text-status-danger-600 hover:text-status-danger-700 dark:text-status-danger-300 dark:hover:text-status-danger-400 flex items-center gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete workflow
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-lsc-border dark:border-earth-700 rounded-xl p-12 flex flex-col items-center justify-center text-center">
                <GitBranch className="w-12 h-12 text-earth-300 dark:text-earth-300 mb-3" />
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Select a workflow to view its steps and execution history
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </PageContainer>
  </AdminShell>
  )
}