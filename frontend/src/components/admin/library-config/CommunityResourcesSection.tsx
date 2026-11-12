/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link2, Plus, Trash2, Loader2, ChevronDown, ChevronRight, Sparkles, FolderPlus } from 'lucide-react'
import {
  getAdminCommunityResources,
  createCommunityResource,
  updateCommunityResource,
  deleteCommunityResource,
  discoverCommunityResources,
  saveDiscoveredResources,
  type CommunityResourceLink,
  type DiscoverySuggestion,
} from '@/api/domains/admin/community-resources-api'
import toast from 'react-hot-toast'
import { SectionShell } from '../ai-settings/SectionShell'

const PAGE_CONTEXT_OPTIONS = [
  { value: 'community', label: 'Community' },
  { value: 'life_situations', label: 'Life Situations' },
  { value: 'business', label: 'Business' },
  { value: 'makerspace', label: 'Makerspace' },
] as const

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button type="button" role="switch" aria-checked={checked} disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'} ${checked ? 'bg-lsc-rose' : 'bg-earth-200 dark:bg-earth-700'}`}>
      <span className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  )
}

const TABS = [
  { id: 'resources', label: 'Resources', icon: Link2 },
  { id: 'discover', label: 'AI Discovery', icon: Sparkles },
] as const

interface CommunityResourcesSectionProps {
  onBack: () => void
}

export function CommunityResourcesSection({ onBack }: CommunityResourcesSectionProps) {
  const queryClient = useQueryClient()
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [newResourceName, setNewResourceName] = useState('')
  const [newResourceUrl, setNewResourceUrl] = useState('')
  const [newResourceCategory, setNewResourceCategory] = useState('')
  const [discoverQuery, setDiscoverQuery] = useState('')
  const [suggestions, setSuggestions] = useState<DiscoverySuggestion[]>([])
  const [discovering, setDiscovering] = useState(false)
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set())

  const { data: resources = [], isLoading } = useQuery({
    queryKey: ['admin-community-resources'],
    queryFn: getAdminCommunityResources,
  })

  const createMutation = useMutation({
    mutationFn: createCommunityResource,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-community-resources'] }); toast.success('Resource added') },
    onError: () => toast.error('Failed to add resource'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CommunityResourceLink> }) => updateCommunityResource(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-community-resources'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteCommunityResource,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-community-resources'] }); toast.success('Resource deleted') },
  })

  const handleAddResource = () => {
    if (!newResourceName.trim()) return
    const cat = newResourceCategory.trim() || 'general'
    createMutation.mutate({ name: newResourceName.trim(), url: newResourceUrl.trim() || null, category: cat, category_label: cat.charAt(0).toUpperCase() + cat.slice(1), page_contexts: [], is_active: true })
    setNewResourceName('')
    setNewResourceUrl('')
    setNewResourceCategory('')
  }

  const handleDiscover = async () => {
    if (!discoverQuery.trim()) return
    try {
      setDiscovering(true)
      const response = await discoverCommunityResources()
      setSuggestions(response.suggestions)
    } catch {
      toast.error('Discovery failed')
    } finally {
      setDiscovering(false)
    }
  }

  const handleSaveDiscovered = async () => {
    const selected = suggestions.filter((_, i) => selectedSuggestions.has(i))
    if (selected.length === 0) return
    try {
      await saveDiscoveredResources(selected)
      queryClient.invalidateQueries({ queryKey: ['admin-community-resources'] })
      toast.success(`Added ${selected.length} resource${selected.length !== 1 ? 's' : ''}`)
      setSuggestions([])
      setSelectedSuggestions(new Set())
    } catch {
      toast.error('Failed to save discovered resources')
    }
  }

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }

  const categories = [...new Set(resources.map((r) => r.category || 'Uncategorized'))]

  if (isLoading) return null

  return (
    <SectionShell
      title="Community Resources"
      description="Links to local organizations, services, and agencies shown on public pages. Curated by staff or discovered by AI."
      tabs={[...TABS]}
      defaultTab="resources"
      backLabel="Back to Library Configuration"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          {activeTab === 'resources' && (
            <>
              {/* Add Resource */}
              <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Add Resource</h4>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <input type="text" value={newResourceName} onChange={(e) => setNewResourceName(e.target.value)}
                    placeholder="Resource name" className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm" />
                  <input type="text" value={newResourceUrl} onChange={(e) => setNewResourceUrl(e.target.value)}
                    placeholder="URL (optional)" className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm" />
                  <input type="text" value={newResourceCategory} onChange={(e) => setNewResourceCategory(e.target.value)}
                    placeholder="Category" className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm" />
                  <button onClick={handleAddResource} disabled={!newResourceName.trim() || createMutation.isPending}
                    className="flex items-center justify-center gap-1 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 text-sm font-medium">
                    <Plus className="w-4 h-4" /> Add
                  </button>
                </div>
              </div>

              {/* Resources by Category */}
              <div className="space-y-3">
                {categories.map((category) => {
                  const categoryResources = resources.filter((r) => (r.category || 'Uncategorized') === category)
                  const isExpanded = expandedCategories.has(category)
                  return (
                    <div key={category} className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg">
                      <button onClick={() => toggleCategory(category)}
                        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-lsc-cream/30 dark:hover:bg-earth-700/50 transition-colors rounded-lg">
                        <div className="flex items-center gap-2">
                          {isExpanded ? <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" /> : <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />}
                          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{category}</span>
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">({categoryResources.length})</span>
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-4 space-y-2">
                          {categoryResources.map((resource) => (
                            <div key={resource.id} className="flex items-center gap-3 py-2 border-b border-earth-100 dark:border-earth-700 last:border-b-0">
                              <Toggle checked={resource.is_active} onChange={(v) => updateMutation.mutate({ id: resource.id, data: { is_active: v } })} />
                              <div className="flex-1 min-w-0">
                                <span className="text-sm text-lsc-dark dark:text-lsc-cream">{resource.name}</span>
                                {resource.url && <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2 truncate">{resource.url}</span>}
                              </div>
                              <div className="flex gap-1">
                                {PAGE_CONTEXT_OPTIONS.map((ctx) => (
                                  <button key={ctx.value}
                                    onClick={() => {
                                      const contexts = resource.page_contexts || []
                                      const updated = contexts.includes(ctx.value)
                                        ? contexts.filter((c) => c !== ctx.value)
                                        : [...contexts, ctx.value]
                                      updateMutation.mutate({ id: resource.id, data: { page_contexts: updated } })
                                    }}
                                    className={`px-2 py-0.5 text-xs rounded-full border ${(resource.page_contexts || []).includes(ctx.value)
                                      ? 'bg-lsc-rose/10 border-lsc-rose text-lsc-rose'
                                      : 'border-lsc-border dark:border-earth-600 text-earth-600 dark:text-earth-400'}`}>
                                    {ctx.label}
                                  </button>
                                ))}
                              </div>
                              <button onClick={() => deleteMutation.mutate(resource.id)}
                                className="p-1 text-status-danger-500 hover:text-status-danger-700" aria-label={`Delete ${resource.name}`}>
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {activeTab === 'discover' && (
            <div className="space-y-4">
              <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">AI Resource Discovery</h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Describe what kinds of community resources you're looking for and AI will suggest relevant local organizations.</p>
                <div className="flex gap-3">
                  <input type="text" value={discoverQuery} onChange={(e) => setDiscoverQuery(e.target.value)}
                    placeholder="e.g., mental health services, food banks, job training..."
                    className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm" />
                  <button onClick={handleDiscover} disabled={discovering || !discoverQuery.trim()}
                    className="flex items-center gap-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 text-sm font-medium">
                    {discovering ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    Discover
                  </button>
                </div>
              </div>

              {suggestions.length > 0 && (
                <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Suggestions ({suggestions.length})</h4>
                    <button onClick={handleSaveDiscovered} disabled={selectedSuggestions.size === 0}
                      className="flex items-center gap-1 px-3 py-1.5 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 text-sm font-medium">
                      <FolderPlus className="w-4 h-4" /> Save Selected ({selectedSuggestions.size})
                    </button>
                  </div>
                  <div className="space-y-2">
                    {suggestions.map((suggestion, idx) => (
                      <label key={idx} className="flex items-start gap-3 p-3 border border-earth-100 dark:border-earth-700 rounded-lg cursor-pointer hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                        <input type="checkbox" checked={selectedSuggestions.has(idx)}
                          onChange={() => {
                            setSelectedSuggestions((prev) => {
                              const next = new Set(prev)
                              if (next.has(idx)) next.delete(idx)
                              else next.add(idx)
                              return next
                            })
                          }}
                          className="mt-1 rounded border-lsc-border" />
                        <div>
                          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{suggestion.name}</span>
                          {suggestion.url && <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">{suggestion.url}</span>}
                          {suggestion.description && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{suggestion.description}</p>}
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </SectionShell>
  )
}
