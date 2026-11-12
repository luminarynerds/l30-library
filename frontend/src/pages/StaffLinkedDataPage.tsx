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
  Link2,
  Search,
  RefreshCw,
  Loader2,
  Database,
  FileText,
  Globe,
  ChevronRight,
  Download,
  Upload,
  Code,
  Book,
  Users,
  Tag,
  ExternalLink,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/api/fetchApi'
import { getAccessToken } from '@/utils/tokenStore'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface BibframeWork {
  id: number
  uri?: string
  title: string
  work_type: string
  language?: string
  contributors?: Array<{ id: number; name: string }>
  subjects?: Array<{ id: number; label: string }>
  instance_count?: number
  created_at: string
}

interface BibframeInstance {
  id: number
  work_id: number
  title: string
  instance_type: string
  isbn_13?: string
  publisher?: string
  publication_year?: number
  item_count?: number
}

interface LinkedDataStats {
  total_works: number
  total_instances: number
  total_items: number
  total_contributors: number
  total_subjects: number
  authority_links: number
}

export default function StaffLinkedDataPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<LinkedDataStats | null>(null)
  const [works, setWorks] = useState<BibframeWork[]>([])
  const [instances, setInstances] = useState<BibframeInstance[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [viewMode, setViewMode] = useState<"overview" | "works" | "instances" | "import">("overview")
  const [selectedWork, setSelectedWork] = useState<BibframeWork | null>(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    if (!authLoading && (!user || !["staff", "admin", "super_admin"].includes(user.role))) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/linked-data/stats')
      setStats(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  const fetchWorks = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: "20",
      })
      if (searchQuery) params.set("q", searchQuery)

      const data = await fetchApi(`/linked-data/works?${params}`)
      setWorks(data.items || [])
    } catch (_error: unknown) {
      toast.error(t('staffLinkedData.failedToLoadBibframeWorks'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, page, searchQuery])

  const fetchInstances = useCallback(async (workId?: number) => {
    if (!token) return
    try {
      const params = new URLSearchParams({ per_page: "20" })
      if (workId) params.set("work_id", String(workId))

      const data = await fetchApi(`/linked-data/instances?${params}`)
      setInstances(data.items || [])
    } catch (_error: unknown) {
      toast.error(t('staffLinkedData.failedToLoadInstances'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchStats()
      if (viewMode === "works") {
        fetchWorks()
      } else if (viewMode === "instances") {
        fetchInstances()
      }
    }
  }, [token, isAuthenticated, viewMode, fetchStats, fetchWorks, fetchInstances])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchWorks()
  }

  const handleSelectWork = (work: BibframeWork) => {
    setSelectedWork(work)
    fetchInstances(work.id)
    setViewMode("instances")
  }

  const handleExportRdf = async (format: "jsonld" | "turtle") => {
    if (!token || !selectedWork) return
    try {
      // Raw fetch retained: this export needs custom Accept headers
      // (application/ld+json or text/turtle) and reads as text/blob, not the
      // JSON contract fetchApi enforces.
      const accessToken = getAccessToken()
      // eslint-disable-next-line no-restricted-syntax -- RDF export needs custom Accept + blob response
      const response = await fetch(`${API_BASE}/linked-data/works/${selectedWork.id}`, {
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          Accept: format === "jsonld" ? "application/ld+json" : "text/turtle",
        },
      })
      if (!response.ok) throw new Error("Failed to export")
      const content = format === "jsonld" ? await response.json() : await response.text()
      const blob = new Blob([format === "jsonld" ? JSON.stringify(content, null, 2) : content], {
        type: format === "jsonld" ? "application/ld+json" : "text/turtle",
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `work-${selectedWork.id}.${format === "jsonld" ? "jsonld" : "ttl"}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(t('toast.staffLinkedData.exportedSuccessfully'))
    } catch (_error: unknown) {
      toast.error(t('toast.staffLinkedData.failedToExport'))
    }
  }

  const getWorkTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "text":
        return <Book className="w-4 h-4" />
      case "spoken_word":
        return <Users className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
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
    <AdminShell title="Linked Data / BIBFRAME">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Linked Data / BIBFRAME
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Manage BIBFRAME entities and linked data
              </p>
            </div>
            <button
              onClick={() => {
                fetchStats()
                if (viewMode === "works") fetchWorks()
                else if (viewMode === "instances") fetchInstances()
              }}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit">
            {(["overview", "works", "instances", "import"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors capitalize ${
                  viewMode === mode
                    ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                }`}
              >
                {mode === "overview" && <Database className="w-4 h-4" />}
                {mode === "works" && <Book className="w-4 h-4" />}
                {mode === "instances" && <FileText className="w-4 h-4" />}
                {mode === "import" && <Upload className="w-4 h-4" />}
                {mode}
              </button>
            ))}
          </div>

          {viewMode === "overview" && (
            <>
              {/* Stats */}
              {stats && (
                <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Book className="w-4 h-4" />
                      <span className="text-xs uppercase">Works</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.total_works.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <FileText className="w-4 h-4" />
                      <span className="text-xs uppercase">Instances</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.total_instances.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Database className="w-4 h-4" />
                      <span className="text-xs uppercase">Items</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.total_items.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Users className="w-4 h-4" />
                      <span className="text-xs uppercase">Contributors</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.total_contributors.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Tag className="w-4 h-4" />
                      <span className="text-xs uppercase">Subjects</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.total_subjects.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Link2 className="w-4 h-4" />
                      <span className="text-xs uppercase">Authority Links</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.authority_links.toLocaleString()}
                    </p>
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Quick Actions
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button
                    onClick={() => setViewMode("works")}
                    className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors text-left"
                  >
                    <Book className="w-8 h-8 text-lsc-rose mb-2" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">Browse Works</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Search and manage BIBFRAME works
                    </p>
                  </button>
                  <button
                    onClick={() => setViewMode("import")}
                    className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors text-left"
                  >
                    <Upload className="w-8 h-8 text-lsc-rose mb-2" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">Import Records</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Import from Library of Congress
                    </p>
                  </button>
                  <button
                    onClick={() => navigate("/staff/sparql")}
                    className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors text-left"
                  >
                    <Code className="w-8 h-8 text-lsc-rose mb-2" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">SPARQL Query</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Query linked data with SPARQL
                    </p>
                  </button>
                </div>
              </div>
            </>
          )}

          {viewMode === "works" && (
            <>
              {/* Search */}
              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t('staffLinkedData.searchWorksByTitleContributor')}
                    aria-label={t('staffLinkedData.searchWorksByTitleContributor2')}
                    className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <button
                  type="submit"
                  className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                >
                  Search
                </button>
              </form>

              {/* Works List */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                  </div>
                ) : works.length === 0 ? (
                  <div className="p-8 text-center">
                    <Book className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No works found</p>
                  </div>
                ) : (
                  <div className="divide-y divide-lsc-border dark:divide-earth-700">
                    {works.map((work) => (
                      <button
                        key={work.id}
                        onClick={() => handleSelectWork(work)}
                        className="w-full p-4 flex items-center justify-between hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors text-left"
                      >
                        <div className="flex items-start gap-3">
                          {getWorkTypeIcon(work.work_type)}
                          <div>
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {work.title}
                            </p>
                            <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                              {work.contributors && work.contributors.length > 0 && (
                                <span>{work.contributors.map((c) => c.name).join(", ")}</span>
                              )}
                              <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded">
                                {work.work_type}
                              </span>
                              {work.language && <span>{work.language}</span>}
                            </div>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                              {work.instance_count || 0} instance(s)
                            </p>
                          </div>
                        </div>
                        <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {viewMode === "instances" && (
            <>
              {selectedWork && (
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        Showing instances for:
                      </p>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {selectedWork.title}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleExportRdf("jsonld")}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                      >
                        <Download className="w-4 h-4" />
                        JSON-LD
                      </button>
                      <button
                        onClick={() => handleExportRdf("turtle")}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                      >
                        <Download className="w-4 h-4" />
                        Turtle
                      </button>
                      <button
                        onClick={() => {
                          setSelectedWork(null)
                          fetchInstances()
                        }}
                        className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:underline"
                      >
                        Show all
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
                {instances.length === 0 ? (
                  <div className="p-8 text-center">
                    <FileText className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No instances found</p>
                  </div>
                ) : (
                  <div className="divide-y divide-lsc-border dark:divide-earth-700">
                    {instances.map((instance) => (
                      <div key={instance.id} className="p-4">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {instance.title}
                        </p>
                        <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {instance.publisher && <span>{instance.publisher}</span>}
                          {instance.publication_year && <span>{instance.publication_year}</span>}
                          {instance.isbn_13 && <span>ISBN: {instance.isbn_13}</span>}
                          <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded">
                            {instance.instance_type}
                          </span>
                        </div>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {instance.item_count || 0} item(s)
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {viewMode === "import" && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                Import from Library of Congress
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                Search and import bibliographic records from the Library of Congress linked data service.
              </p>
              <div className="p-8 border-2 border-dashed border-lsc-border dark:border-earth-700 rounded-lg text-center">
                <Globe className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Use the cataloging interface to search and import records from Library of Congress
                </p>
                <button
                  onClick={() => navigate("/staff/cataloging")}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                >
                  <ExternalLink className="w-4 h-4" />
                  Go to Cataloging
                </button>
              </div>
            </div>
          )}
    </AdminShell>
  )
}