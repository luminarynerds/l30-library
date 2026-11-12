/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Code,
  Play,
  Loader2,
  Copy,
  Download,
  AlertCircle,
  CheckCircle,
  HelpCircle,
  Database,
  BookOpen,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/api/fetchApi'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface SPARQLResults {
  head: { vars: string[] }
  results: { bindings: Array<Record<string, { type: string; value: string }>> }
  error?: string
}

interface ExampleQuery {
  name: string
  description: string
  query: string
}

export default function StaffSPARQLPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [query, setQuery] = useState(`PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?work ?title ?type
WHERE {
  ?work a bf:Work ;
        bf:title/bf:mainTitle ?title ;
        bf:content ?type .
}
LIMIT 10`)
  const [results, setResults] = useState<SPARQLResults | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [prefixes, setPrefixes] = useState<Record<string, string>>({})
  const [examples, setExamples] = useState<ExampleQuery[]>([])
  const [showExamples, setShowExamples] = useState(false)

  useEffect(() => {
    if (!authLoading && (!user || !["staff", "admin", "super_admin"].includes(user.role))) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const fetchPrefixes = useCallback(async () => {
    try {
      const data = await fetchApi('/sparql/prefixes')
      setPrefixes(data.prefixes || {})
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [])

  const fetchExamples = useCallback(async () => {
    try {
      const data = await fetchApi('/sparql/examples')
      setExamples(data.examples || [])
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchPrefixes()
      fetchExamples()
    }
  }, [token, isAuthenticated, fetchPrefixes, fetchExamples])

  const executeQuery = async () => {
    if (!query.trim()) {
      toast.error(t('staffSPARQL.pleaseEnterASparqlQuery'))
      return
    }

    setIsExecuting(true)
    setError(null)
    setResults(null)

    try {
      // eslint-disable-next-line no-restricted-syntax -- SPARQL POST needs Content-Type: application/sparql-query, not JSON
      const response = await fetch(`${API_BASE}/sparql/query?format=json`, {
        method: "POST",
        headers: {
          "Content-Type": "application/sparql-query",
        },
        body: query,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Query failed" }))
        throw new Error(errorData.detail || "Query failed")
      }

      const data = await response.json()
      setResults(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Query execution failed"
      setError(message)
      toast.error(message)
    } finally {
      setIsExecuting(false)
    }
  }

  const handleCopyQuery = () => {
    navigator.clipboard.writeText(query)
    toast.success(t('staffSPARQL.queryCopiedToClipboard'))
  }

  const handleDownloadResults = () => {
    if (!results) return
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "sparql-results.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleLoadExample = (example: ExampleQuery) => {
    setQuery(example.query)
    setShowExamples(false)
    toast.success(t('toast.staffSPARQL.loadedName', { name: example.name }))
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!user || !["staff", "admin", "super_admin"].includes(user.role)) {
    return <></>
  }

  return (
    <AdminShell title="SPARQL Query Interface">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                SPARQL Query Interface
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Query linked data using SPARQL
              </p>
            </div>
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <BookOpen className="w-4 h-4" />
              Examples
            </button>
          </div>

          {/* Examples Panel */}
          {showExamples && examples.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                Example Queries
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {examples.map((example, index) => (
                  <button
                    key={index}
                    onClick={() => handleLoadExample(example)}
                    className="p-3 text-left border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
                  >
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">
                      {example.name}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {example.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Query Editor */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Code className="w-4 h-4" />
                Query Editor
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyQuery}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                  title="Copy query"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={executeQuery}
                  disabled={isExecuting}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {isExecuting ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Execute
                </button>
              </div>
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('staffSPARQL.enterYourSparqlQueryHere')}
              className="w-full h-64 p-4 font-mono text-sm bg-earth-50 dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream border-0 focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div role="alert" className="bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-status-danger-500 mt-0.5" />
                <div>
                  <p className="font-medium text-status-danger-800 dark:text-status-danger-300">Query Error</p>
                  <p className="text-sm text-status-danger-700 dark:text-status-danger-400 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {results && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-status-success-500" />
                  Results ({results.results.bindings.length} rows)
                </h3>
                <button
                  onClick={handleDownloadResults}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                >
                  <Download className="w-4 h-4" />
                  Download JSON
                </button>
              </div>
              {results.results.bindings.length === 0 ? (
                <div className="p-8 text-center">
                  <Database className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No results found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-lsc-cream dark:bg-earth-700">
                      <tr>
                        {results.head.vars.map((variable) => (
                          <th
                            key={variable}
                            className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase"
                          >
                            ?{variable}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                      {results.results.bindings.map((binding, index) => (
                        <tr key={index} className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20">
                          {results.head.vars.map((variable) => (
                            <td
                              key={variable}
                              className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream"
                            >
                              {binding[variable] ? (
                                binding[variable].type === "uri" ? (
                                  <a
                                    href={binding[variable].value}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-lsc-rose hover:underline break-all"
                                  >
                                    {binding[variable].value}
                                  </a>
                                ) : (
                                  <span className="break-all">{binding[variable].value}</span>
                                )
                              ) : (
                                <span className="text-lsc-dark/30 dark:text-lsc-cream/60">-</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Prefixes Reference */}
          {Object.keys(prefixes).length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                <HelpCircle className="w-4 h-4" />
                Available Prefixes
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 text-xs font-mono">
                {Object.entries(prefixes).map(([prefix, uri]) => (
                  <div key={prefix} className="text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={`${prefix}: <${uri}>`}>
                    <span className="text-lsc-rose">{prefix}:</span>{" "}
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">&lt;{uri}&gt;</span>
                  </div>
                ))}
              </div>
            </div>
          )}
    </AdminShell>
  )
}