/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, Database } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  SettingsFormPage,
  SettingsCard,
  SettingsGrid,
  SelectField,
  TextField,
  ToggleRow,
  InfoBanner,
} from '@/components/admin'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'

interface SearchEngineConfig extends Record<string, unknown> {
  search_engine: string
  elasticsearch_url: string
  elasticsearch_index_prefix: string
  elasticsearch_enabled: boolean
}

const DEFAULT_SEARCH_ENGINE_CONFIG: SearchEngineConfig = {
  search_engine: 'postgres',
  elasticsearch_url: '',
  elasticsearch_index_prefix: 'lsc_',
  elasticsearch_enabled: false,
}

export default function AdminSearchEngineSettingsPage() {
  const { t } = useTranslation()
  const { value: config, setField, loading, saving, save } =
    useConfigurationSection<SearchEngineConfig>('search_engine', DEFAULT_SEARCH_ENGINE_CONFIG, {
      successMessage: t('admin.adminSearchEngineSettings.searchEngineSettingsUpdatedSuccessfully'),
      errorMessage: t('toast.adminSearchEngineSettings.failedToUpdateSearchEngine'),
      defaultReason: 'Admin update via search engine settings UI',
    })

  const SEARCH_ENGINE_OPTIONS = [
    { value: 'postgres', label: t('admin.adminSearchEngineSettings.postgresqlFullTextSearchDefault') },
    { value: 'elasticsearch', label: 'Elasticsearch' },
  ]

  return (
      <SettingsFormPage
        title="Search Engine Settings"
        icon={Search}
        loading={loading}
        saving={saving}
        onSave={() => save()}
        banner={
          <InfoBanner tone="info">
            Configure the search backend for the catalog. PostgreSQL full-text search is the default
            and requires no additional infrastructure. Elasticsearch provides advanced features like
            fuzzy matching and faceted search.
          </InfoBanner>
        }
      >
        <SettingsCard title="Search Backend" icon={Database}>
          <SelectField
            label="Search Engine"
            value={config.search_engine}
            onChange={(v) => setField('search_engine', v)}
            options={SEARCH_ENGINE_OPTIONS}
          />
          {config.search_engine === 'elasticsearch' && (
            <>
              <ToggleRow
                label="Elasticsearch Enabled"
                description={t('admin.adminSearchEngineSettings.activateElasticsearchIndexingAndQueries')}
                checked={config.elasticsearch_enabled}
                onChange={(v) => setField('elasticsearch_enabled', v)}
              />
              <SettingsGrid cols={2}>
                <TextField
                  label="Elasticsearch URL"
                  value={config.elasticsearch_url}
                  onChange={(v) => setField('elasticsearch_url', v)}
                  placeholder={t('placeholder.adminSearchEngineSettings.httpelasticsearch9200')}
                />
                <TextField
                  label="Index Prefix"
                  value={config.elasticsearch_index_prefix}
                  onChange={(v) => setField('elasticsearch_index_prefix', v)}
                  placeholder={t('placeholder.adminSearchEngineSettings.lsc')}
                  help={t('admin.adminSearchEngineSettings.prefixForAllElasticsearchIndex')}
                />
              </SettingsGrid>
            </>
          )}
        </SettingsCard>
      </SettingsFormPage>
  )
}
