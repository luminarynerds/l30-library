/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Zap } from 'lucide-react'

import { useTranslation } from '@/i18n'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import {
  NumberField,
  SettingsCard,
  SettingsGrid,
  TextField,
} from '@/components/admin'

interface EmbeddingConfig extends Record<string, unknown> {
  embedding_api_url: string
  embedding_model: string
  embedding_dimension: number
}

const DEFAULT_CONFIG: EmbeddingConfig = {
  embedding_api_url: 'https://api.openai.com/v1/embeddings',
  embedding_model: 'text-embedding-3-small',
  embedding_dimension: 1536,
}

export function ConfigTab() {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save, dirty } =
    useConfigurationSection<EmbeddingConfig>('search_engine', DEFAULT_CONFIG, {
      successMessage: 'Embedding configuration updated',
      errorMessage: 'Failed to update embedding configuration',
      defaultReason: 'Admin update via AI settings UI',
    })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <SettingsCard title="Embedding Configuration" icon={Zap}>
        <TextField
          label="Embedding API URL"
          value={config.embedding_api_url}
          onChange={(v) => setField('embedding_api_url', v)}
          help={t('admin.adminSearchEngineSettings.openaiCompatibleEndpointWorksWith')}
        />
        <SettingsGrid cols={2}>
          <TextField
            label="Embedding Model"
            value={config.embedding_model}
            onChange={(v) => setField('embedding_model', v)}
          />
          <NumberField
            label="Embedding Dimension"
            min={64}
            max={4096}
            value={config.embedding_dimension}
            onChange={(v) => setField('embedding_dimension', v)}
            help={t('admin.adminSearchEngineSettings.mustMatchTheModelS')}
          />
        </SettingsGrid>
      </SettingsCard>

      <div className="flex justify-end">
        <button
          onClick={() => save()}
          disabled={saving || !dirty}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors shadow-sm"
        >
          {saving ? (
            <><Loader2 className="w-4 h-4 motion-safe:animate-spin" /> Saving...</>
          ) : (
            'Save Configuration'
          )}
        </button>
      </div>
    </div>
  )
}
