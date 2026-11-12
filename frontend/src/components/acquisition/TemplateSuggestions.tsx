/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import {
  Loader2,
  FileText,
  DollarSign,
  Package,
  Zap,
  CheckCircle,
  Star,
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from '@/api/fetchApi'
import { createOrderTemplate } from '@/api/domains/admin/order-templates-api'
import { t } from '@/i18n'

interface TemplateSuggestion {
  name: string
  description: string
  item_count: number
  estimated_total: number
  items?: SuggestedItem[]
}

interface SuggestedItem {
  title: string
  author: string | null
  isbn: string | null
  estimated_price: number
  suggested_quantity?: number
}

interface Props {
  token: string
  onTemplateCreated: () => void
}

export default function TemplateSuggestions({ token, onTemplateCreated }: Props) {
  const [suggestions, setSuggestions] = useState<TemplateSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState<Record<number, boolean>>({})
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)

  const fetchSuggestions = async () => {
    setLoading(true)
    try {
      const data = await fetchApi('/acquisition/templates/suggestions')
      setSuggestions(Array.isArray(data) ? data : data.suggestions || [])
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToLoadTemplateSuggestions'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    fetchSuggestions()
  }, [token])

  const createTemplate = async (suggestion: TemplateSuggestion, index: number) => {
    setCreating((prev) => ({ ...prev, [index]: true }))
    try {
      await createOrderTemplate({
        name: suggestion.name,
        description: suggestion.description,
        template_items: (suggestion.items || []).map((it) => ({
          title: it.title,
          author: it.author,
          isbn: it.isbn,
          quantity: it.suggested_quantity ?? 1,
        })),
      })
      toast.success(t('toast.acquisition.templateNameCreatedSuccessfully', { name: suggestion.name }))
      onTemplateCreated()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToCreateTemplate'))
    } finally {
      setCreating((prev) => ({ ...prev, [index]: false }))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (suggestions.length === 0) {
    return (
      <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60">
        <FileText className="w-10 h-10 mx-auto mb-2 opacity-40" />
        <p>No template suggestions available at this time.</p>
        <button
          onClick={fetchSuggestions}
          className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
        >
          <Zap className="w-3.5 h-3.5" />
          Refresh Suggestions
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Smart Template Suggestions
        </h3>
        <button
          onClick={fetchSuggestions}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
        >
          <Zap className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {suggestions.map((suggestion, index) => {
          const isExpanded = expandedIndex === index
          const isCreating = creating[index]

          return (
            <div
              key={index}
              className="border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 overflow-hidden"
            >
              <div className="p-4">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Star className="w-4 h-4 text-lsc-rose flex-shrink-0" />
                    <h4 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={suggestion.name}>
                      {suggestion.name}
                    </h4>
                  </div>
                </div>

                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3 line-clamp-2" title={suggestion.description}>
                  {suggestion.description}
                </p>

                <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  <span className="inline-flex items-center gap-1">
                    <Package className="w-3.5 h-3.5" />
                    {suggestion.item_count} item{suggestion.item_count !== 1 ? "s" : ""}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <DollarSign className="w-3.5 h-3.5" />
                    Est. ${(suggestion.estimated_total ?? 0).toFixed(2)}
                  </span>
                </div>

                {suggestion.items && suggestion.items.length > 0 && (
                  <button
                    onClick={() => setExpandedIndex(isExpanded ? null : index)}
                    className="text-xs text-lsc-rose hover:text-lsc-rose/80 font-medium mb-3 transition-colors"
                  >
                    {isExpanded ? "Hide items" : `View ${suggestion.items.length} items`}
                  </button>
                )}

                {isExpanded && suggestion.items && (
                  <div className="mb-3 space-y-2 max-h-48 overflow-y-auto">
                    {suggestion.items.map((item, itemIdx) => (
                      <div
                        key={itemIdx}
                        className="flex items-center justify-between text-xs bg-earth-50 dark:bg-earth-700/50 rounded-lg px-3 py-2"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>
                            {item.title}
                          </p>
                          {item.author && (
                            <p className="text-lsc-dark/70 dark:text-lsc-cream/60 truncate" title={item.author ?? ''}>
                              {item.author}
                            </p>
                          )}
                        </div>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 ml-2">
                          ${(item.estimated_price ?? 0).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => createTemplate(suggestion, index)}
                  disabled={isCreating}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium text-sm hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  Create Template
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
