/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Bot, Brain, Search, Sparkles, Cpu, GraduationCap,
} from 'lucide-react'
import api from '@/api/api'
import { AIStatusCard } from './AIStatusCard'

export type SectionId = 'tools' | 'agents' | 'search' | 'recommendations' | 'models' | 'training'

interface DashboardStatus {
  ollamaConnected: boolean
  modelsLoaded: number
}

interface AIDashboardProps {
  onSelectSection: (id: SectionId) => void
}

export function AIDashboard({ onSelectSection }: AIDashboardProps) {
  const [status, setStatus] = useState<DashboardStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [ollamaRes] = await Promise.allSettled([
          api.get('/api/v1/admin/ai/ollama/status'),
        ])
        setStatus({
          ollamaConnected: ollamaRes.status === 'fulfilled' && ollamaRes.value?.connected,
          modelsLoaded: ollamaRes.status === 'fulfilled' ? ollamaRes.value?.models?.length || 0 : 0,
        })
      } catch {
        setStatus({ ollamaConnected: false, modelsLoaded: 0 })
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  if (loading) {
    return (
      <div
        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
        aria-busy="true"
        aria-label="Loading AI dashboard"
      >
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-48 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
        ))}
      </div>
    )
  }

  const cards: {
    id: SectionId
    icon: React.ReactNode
    title: string
    description: string
    locality: 'local' | 'cloud' | 'mixed'
    statusItems: { label: string; value: string | number; ok?: boolean | undefined }[]
  }[] = [
    {
      id: 'tools',
      icon: <Bot className="w-5 h-5 text-lsc-rose" />,
      title: 'AI Tools & Chatbots',
      description: "AI assistants that run on your library's own server. No patron conversations leave the building.",
      locality: 'local',
      statusItems: [
        { label: 'Server', value: status?.ollamaConnected ? 'Connected' : 'Disconnected', ok: status?.ollamaConnected },
      ],
    },
    {
      id: 'agents',
      icon: <Brain className="w-5 h-5 text-lsc-rose" />,
      title: 'Library Agents',
      description: "Specialized AI personalities for your library -- reader's advisory, gardening help, etc. Fully private.",
      locality: 'local',
      statusItems: [],
    },
    {
      id: 'search',
      icon: <Search className="w-5 h-5 text-lsc-rose" />,
      title: 'Search & Embeddings',
      description: 'Powers "search by meaning" in the catalog. Embedding generation currently uses a cloud API (OpenAI). Search queries stay on your server.',
      locality: 'cloud',
      statusItems: [],
    },
    {
      id: 'recommendations',
      icon: <Sparkles className="w-5 h-5 text-lsc-rose" />,
      title: 'Recommendations',
      description: 'Suggests similar books based on catalog data. Runs locally using your existing embeddings.',
      locality: 'local',
      statusItems: [],
    },
    {
      id: 'models',
      icon: <Cpu className="w-5 h-5 text-lsc-rose" />,
      title: 'Models & Server',
      description: 'Manage the AI server and which models are available. Everything runs on hardware you control.',
      locality: 'local',
      statusItems: [
        { label: 'Server', value: status?.ollamaConnected ? 'Connected' : 'Disconnected', ok: status?.ollamaConnected },
        { label: 'Models', value: status?.modelsLoaded || 0 },
      ],
    },
    {
      id: 'training',
      icon: <GraduationCap className="w-5 h-5 text-lsc-rose" />,
      title: 'Training Pipeline',
      description: 'Review and approve training data before it is used. You control what the AI learns.',
      locality: 'local',
      statusItems: [],
    },
  ]

  return (
    <nav aria-label="AI settings sections">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {cards.map((card) => (
          <AIStatusCard
            key={card.id}
            id={card.id}
            icon={card.icon}
            title={card.title}
            description={card.description}
            locality={card.locality}
            statusItems={card.statusItems}
            onClick={onSelectSection as (id: string) => void}
          />
        ))}
      </div>
    </nav>
  )
}
