/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Network, ShieldCheck, AlertTriangle } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { clsx } from '@/utils/helpers'

type Audience = 'patron' | 'staff' | 'admin'
type LeavesNetwork = 'no' | 'yes' | 'planned'

interface ToolRow {
  tool: string
  audience: Audience
  model: string
  runsWhere: string
  leavesNetwork: LeavesNetwork
  retention: string
  optOut: string
}

function PillNo({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-status-success-100 text-status-success-800 dark:bg-status-success-900/40 dark:text-status-success-300">
      <ShieldCheck aria-hidden="true" className="w-3.5 h-3.5" />
      {label}
    </span>
  )
}

function PillYes({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/40 dark:text-status-warning-200">
      <AlertTriangle aria-hidden="true" className="w-3.5 h-3.5" />
      {label}
    </span>
  )
}

function PillPlanned({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-cream text-lsc-dark dark:bg-earth-700 dark:text-lsc-cream border border-lsc-border dark:border-earth-600">
      {label}
    </span>
  )
}

function LeavesCell({ value, t }: { value: LeavesNetwork; t: (k: string, d?: string) => string }) {
  if (value === 'no') return <PillNo label={t('aITools.matrixLeavesNo', 'No')} />
  if (value === 'yes') return <PillYes label={t('aITools.matrixLeavesYes', 'Yes')} />
  return <PillPlanned label={t('aITools.matrixLeavesPlanned', 'Not yet built')} />
}

interface MatrixTableProps {
  captionId: string
  caption: string
  summary: string
  rows: ToolRow[]
  t: (k: string, d?: string) => string
}

function MatrixTable({ captionId, caption, summary, rows, t }: MatrixTableProps): React.ReactElement {
  return (
    <div className="overflow-x-auto rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800">
      <table
        aria-describedby={captionId}
        className="w-full min-w-[720px] text-sm text-left"
      >
        <caption id={captionId} className="sr-only">
          {caption}. {summary}
        </caption>
        <thead className="bg-lsc-cream dark:bg-earth-700/50 text-lsc-dark dark:text-lsc-cream">
          <tr>
            <th scope="col" className="px-4 py-3 font-semibold">
              {t('aITools.matrixColTool', 'Tool')}
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              {t('aITools.matrixColModel', 'Model')}
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              {t('aITools.matrixColRunsWhere', 'Runs where')}
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              {t('aITools.matrixColLeaves', 'Leaves our network?')}
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              {t('aITools.matrixColRetention', 'Retention')}
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              {t('aITools.matrixColOptOut', 'Opt-out')}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
          {rows.map((row, i) => (
            <tr
              key={row.tool}
              className={clsx(
                'align-top',
                i % 2 === 1 && 'bg-lsc-cream/30 dark:bg-earth-700/20',
              )}
            >
              <th
                scope="row"
                className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream whitespace-normal"
              >
                {row.tool}
              </th>
              <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{row.model}</td>
              <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{row.runsWhere}</td>
              <td className="px-4 py-3">
                <LeavesCell value={row.leavesNetwork} t={t} />
              </td>
              <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{row.retention}</td>
              <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{row.optOut}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DataFlowMatrix(): React.ReactElement {
  const { t } = useTranslation()

  const localOllama = t('aITools.matrixRunsLocal', 'In our building (Ollama on the R720)')
  const localEmbeddings = t(
    'aITools.matrixRunsLocalEmbeddings',
    'In our building (OpenAI-compatible API, pointed at our local Ollama in prod)',
  )
  const vendorOpenAIOrLocal = t(
    'aITools.matrixRunsOpenAIOrLocal',
    'OpenAI API if a key is set, otherwise local Ollama',
  )

  const retentionSession = t(
    'aITools.matrixRetentionSession',
    'Session only; cleared when you close the tab',
  )
  const retentionEmbeddings = t(
    'aITools.matrixRetentionEmbeddings',
    'Embedding vectors cached locally; source text not sent off-network',
  )

  const optOutNotUse = t('aITools.matrixOptOutNotUse', "Don't use it; nothing else is affected")
  const optOutStaffOff = t(
    'aITools.matrixOptOutStaffOff',
    'Staff can turn the tool off per-library in admin settings',
  )
  const optOutAdminOff = t(
    'aITools.matrixOptOutAdminOff',
    'Admin can skip this step in setup; enter values manually',
  )

  const patronRows: ToolRow[] = [
    {
      tool: t('aITools.matrixToolReader', "What Should I Read Next? (reader's advisory)"),
      audience: 'patron',
      model: 'Llama 3.2 (3B)',
      runsWhere: localOllama,
      leavesNetwork: 'no',
      retention: retentionSession,
      optOut: optOutNotUse,
    },
    {
      tool: t('aITools.matrixToolWriter', 'AI Writing Assistant (in-library only)'),
      audience: 'patron',
      model: 'Llama 3.2 (3B)',
      runsWhere: localOllama,
      leavesNetwork: 'no',
      retention: retentionSession,
      optOut: optOutNotUse,
    },
    {
      tool: t('aITools.matrixToolTranslation', 'On-the-fly UI translation'),
      audience: 'patron',
      model: 'Llama 3.2 (3B)',
      runsWhere: localOllama,
      leavesNetwork: 'no',
      retention: t(
        'aITools.matrixRetentionTranslation',
        'Translated phrase cached locally for 7 days; nothing personal',
      ),
      optOut: t('aITools.matrixOptOutTranslation', 'Keep your language set to English'),
    },
    {
      tool: t('aITools.matrixToolSemantic', 'Semantic catalog search'),
      audience: 'patron',
      model: t('aITools.matrixModelEmbeddings', 'Local embeddings model'),
      runsWhere: localEmbeddings,
      leavesNetwork: 'no',
      retention: retentionEmbeddings,
      optOut: t(
        'aITools.matrixOptOutSemantic',
        'Use plain keyword search instead (top of the catalog page)',
      ),
    },
    {
      tool: t('aITools.matrixToolWhisper', 'Meeting / event audio transcription'),
      audience: 'patron',
      model: t('aITools.matrixDash', '—'),
      runsWhere: t(
        'aITools.matrixWhisperPlanned',
        'Planned: Whisper running on the R720. Not yet built.',
      ),
      leavesNetwork: 'planned',
      retention: t('aITools.matrixDash', '—'),
      optOut: t('aITools.matrixDash', '—'),
    },
  ]

  const staffRows: ToolRow[] = [
    {
      tool: t('aITools.matrixToolCatalogEnrich', 'Catalog enrichment (book summaries, subjects)'),
      audience: 'staff',
      model: 'Llama 3.2 (3B)',
      runsWhere: localOllama,
      leavesNetwork: 'no',
      retention: t(
        'aITools.matrixRetentionEnrich',
        'Generated text is stored on the catalog record',
      ),
      optOut: optOutStaffOff,
    },
    {
      tool: t('aITools.matrixToolMarketing', 'Marketing copy assistant (social, newsletters)'),
      audience: 'staff',
      model: 'Llama 3.2 (3B)',
      runsWhere: localOllama,
      leavesNetwork: 'no',
      retention: t(
        'aITools.matrixRetentionMarketing',
        'Draft is saved with the campaign; never auto-published',
      ),
      optOut: optOutStaffOff,
    },
    {
      tool: t('aITools.matrixToolBookClub', 'Book club discussion-question helper'),
      audience: 'staff',
      model: 'Llama 3.2 (3B)',
      runsWhere: localOllama,
      leavesNetwork: 'no',
      retention: t(
        'aITools.matrixRetentionBookClub',
        'Suggested questions saved with the meeting',
      ),
      optOut: optOutStaffOff,
    },
    {
      tool: t('aITools.matrixToolPolicyExtract', 'Policy extraction at setup time (admin)'),
      audience: 'admin',
      model: t('aITools.matrixModelOpenAIOrLocal', 'OpenAI (configurable) or local Llama'),
      runsWhere: vendorOpenAIOrLocal,
      leavesNetwork: 'yes',
      retention: t(
        'aITools.matrixRetentionPolicyExtract',
        'Extracted values land in your library config; the document is not stored off-network',
      ),
      optOut: optOutAdminOff,
    },
  ]

  return (
    <section
      id="data-flow"
      className="scroll-mt-24 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6"
    >
      <div className="flex items-center gap-2 mb-2">
        <Network aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('aITools.dataFlowHeading', 'Where each tool sends your data')}
        </h2>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t(
          'aITools.dataFlowLead',
          "The promise above is in plain language. This is the per-tool receipt. \"Leaves our network\" means the request travels over the public internet to an AI vendor; \"In our building\" means it stops at our server.",
        )}
      </p>

      <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
        {t('aITools.dataFlowPatronHeading', 'Tools you can use')}
      </h3>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        {t(
          'aITools.dataFlowPatronLead',
          'Everything on the public site runs on the library server. Nothing in this table leaves our network.',
        )}
      </p>
      <MatrixTable
        captionId="data-flow-patron-caption"
        caption={t(
          'aITools.dataFlowPatronCaption',
          'Patron-facing AI tools and where their data flows',
        )}
        summary={t(
          'aITools.dataFlowPatronSummary',
          'All rows show local processing; no data leaves the library network.',
        )}
        rows={patronRows}
        t={t}
      />

      <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-8 mb-3">
        {t('aITools.dataFlowStaffHeading', 'Tools staff use')}
      </h3>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        {t(
          'aITools.dataFlowStaffLead',
          "Some staff-only tools send data to outside AI providers. We list them here so the picture is complete -- patron content doesn't flow into them.",
        )}
      </p>
      <MatrixTable
        captionId="data-flow-staff-caption"
        caption={t(
          'aITools.dataFlowStaffCaption',
          'Staff and admin AI tools and where their data flows',
        )}
        summary={t(
          'aITools.dataFlowStaffSummary',
          'Mixed: some tools run locally, some call outside AI vendors. Each row is labelled.',
        )}
        rows={staffRows}
        t={t}
      />

      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-6">
        {t(
          'aITools.dataFlowFootnote',
          'Sourced from the live backend code. If a tool is missing, ask Stevie -- it probably means we haven\'t built it yet.',
        )}
      </p>
    </section>
  )
}
