/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Settings, Zap } from 'lucide-react'

import { ManageTab } from './search-embeddings/ManageTab'
import { ConfigTab } from './search-embeddings/ConfigTab'
import { SectionShell } from './SectionShell'

const TABS = [
  { id: 'manage', label: 'Manage Embeddings', icon: Zap },
  { id: 'config', label: 'Embedding Config', icon: Settings },
]

export function SearchEmbeddingsSection({ onBack }: { onBack: () => void }) {
  return (
    <SectionShell
      title="Search & Embeddings"
      description="Powers 'search by meaning' in the catalog. Embedding generation currently uses a cloud API (OpenAI). Search queries stay on your server."
      tabs={TABS}
      onBack={onBack}
    >
      {(activeTab) => (
        <>
          {activeTab === 'manage' && <ManageTab />}
          {activeTab === 'config' && <ConfigTab />}
        </>
      )}
    </SectionShell>
  )
}
