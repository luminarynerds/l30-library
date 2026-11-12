/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// frontend/src/pages/StaffBlogPage.tsx
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Plus, Search, Edit2, Trash2, Eye, EyeOff, Clock, BarChart3, CheckSquare, Square, RotateCcw } from "lucide-react"
import toast from "react-hot-toast"
import { t } from "@/i18n"
import { useAuth } from "@/contexts/AuthContext"
import { AdminShell } from "@/components/shells/AdminShell"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import {
  getAdminPosts,
  getBlogAnalytics,
  deleteBlogPost,
  restoreBlogPost,
  publishBlogPost,
  unpublishBlogPost,
  scheduleBlogPost,
  type BlogPostListItem,
  type BlogPostListResponse,
  type BlogAnalytics,
} from "@/services/blog-api"
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { StatusVariant } from '@/components/ui/StatusBadge'

function AnalyticsPanel({ analytics }: { analytics: BlogAnalytics }) {
  const maxDayCount = Math.max(...analytics.views_by_day.map((d) => d.count), 1)
  const topFive = analytics.top_posts.slice(0, 5)

  return (
    <div className="space-y-4 rounded-xl border border-lsc-border dark:border-earth-700 p-4 bg-lsc-white dark:bg-earth-800">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
          Reading Analytics
        </h2>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl bg-lsc-cream dark:bg-earth-700 p-3 text-center">
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {analytics.total_views.toLocaleString()}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Total Views</p>
        </div>
        <div className="rounded-xl bg-lsc-cream dark:bg-earth-700 p-3 text-center">
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {analytics.views_last_7_days.toLocaleString()}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">This Week</p>
        </div>
        <div className="rounded-xl bg-lsc-cream dark:bg-earth-700 p-3 text-center">
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {analytics.views_last_30_days.toLocaleString()}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">This Month</p>
        </div>
        <div className="rounded-xl bg-lsc-cream dark:bg-earth-700 p-3 text-center">
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {analytics.published_posts}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Published</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Views chart */}
        {analytics.views_by_day.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Views (Last 30 Days)
            </h3>
            <div className="flex items-end gap-px h-24">
              {analytics.views_by_day.map((day) => (
                <div
                  key={day.date}
                  className="flex-1 bg-lsc-rose/80 hover:bg-lsc-rose rounded-t transition-colors cursor-default relative group"
                  style={{ height: `${Math.max((day.count / maxDayCount) * 100, 4)}%` }}
                  title={`${day.date}: ${day.count} views`}
                >
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-1.5 py-0.5 text-[10px] bg-lsc-dark text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    {day.count}
                  </span>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/40">
                {analytics.views_by_day[0]?.date}
              </span>
              <span className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/40">
                {analytics.views_by_day[analytics.views_by_day.length - 1]?.date}
              </span>
            </div>
          </div>
        )}

        {/* Top posts */}
        {topFive.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Most Read Posts
            </h3>
            <ol className="space-y-1.5">
              {topFive.map((post, i) => (
                <li key={post.id} className="flex items-center gap-2 text-sm">
                  <span className="text-xs font-bold text-lsc-rose w-4 text-right">{i + 1}.</span>
                  <span className="truncate flex-1 text-lsc-dark dark:text-lsc-cream">{post.title}</span>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 tabular-nums">
                    {post.view_count.toLocaleString()} views
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

    </div>
  )
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ""
  const diffSec = Math.floor((Date.now() - then) / 1000)
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 30) return `${diffDay}d ago`
  return new Date(iso).toLocaleDateString()
}

export default function StaffBlogPage(): React.ReactElement {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const inTrashView = statusFilter === "trash"
  const [postsData, setPostsData] = useState<BlogPostListResponse | null>(null)
  const [analytics, setAnalytics] = useState<BlogAnalytics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [showAnalytics, setShowAnalytics] = useState(true)
  const [deleteConfirm, setDeleteConfirm] = useState<BlogPostListItem | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false)
  const [scheduleConfirm, setScheduleConfirm] = useState<BlogPostListItem | null>(null)
  const [scheduleDate, setScheduleDate] = useState<string>("")
  const [restoringIds, setRestoringIds] = useState<Set<number>>(new Set())

  const loadPosts = useCallback(
    async (page = 1) => {
      if (!token) return
      setIsLoading(true)
      try {
        const data = await getAdminPosts(token, {
          status: statusFilter || undefined,
          q: searchQuery || undefined,
          page,
          per_page: 20,
        })
        setPostsData(data)
        setSelectedIds(new Set())
      } catch {
        toast.error("Failed to load posts")
      } finally {
        setIsLoading(false)
      }
    },
    [token, searchQuery, statusFilter]
  )

  const loadAnalytics = useCallback(async () => {
    if (!token) return
    try {
      const data = await getBlogAnalytics(token, 30)
      setAnalytics(data)
    } catch {
      // Analytics are non-critical, fail silently
    }
  }, [token])

  useEffect(() => {
    loadPosts()
    loadAnalytics()
  }, [loadPosts, loadAnalytics])

  const handlePublish = async (post: BlogPostListItem) => {
    if (!token) return
    try {
      await publishBlogPost(token, post.id)
      toast.success("Post published")
      loadPosts()
    } catch {
      toast.error("Failed to publish")
    }
  }

  const handleUnpublish = async (post: BlogPostListItem) => {
    if (!token) return
    try {
      await unpublishBlogPost(token, post.id)
      toast.success("Post unpublished")
      loadPosts()
    } catch {
      toast.error("Failed to unpublish")
    }
  }

  const handleSchedule = async () => {
    if (!token || !scheduleConfirm || !scheduleDate) return
    try {
      const utcDate = new Date(scheduleDate).toISOString()
      await scheduleBlogPost(token, scheduleConfirm.id, utcDate)
      toast.success("Post scheduled")
      setScheduleConfirm(null)
      setScheduleDate("")
      loadPosts()
    } catch {
      toast.error("Failed to schedule")
    }
  }

  const handleDelete = async () => {
    if (!token || !deleteConfirm) return
    try {
      await deleteBlogPost(token, deleteConfirm.id)
      toast.success("Post deleted")
      setDeleteConfirm(null)
      loadPosts()
    } catch {
      toast.error("Failed to delete")
    }
  }

  const handleRestore = async (post: BlogPostListItem) => {
    if (!token || restoringIds.has(post.id)) return
    setRestoringIds((prev) => new Set(prev).add(post.id))
    try {
      await restoreBlogPost(token, post.id)
      toast.success("Post restored")
      await loadPosts()
    } catch {
      toast.error("Failed to restore")
    } finally {
      setRestoringIds((prev) => {
        const next = new Set(prev)
        next.delete(post.id)
        return next
      })
    }
  }

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (!postsData) return
    if (selectedIds.size === postsData.items.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(postsData.items.map((p) => p.id)))
    }
  }

  const handleBulkPublish = async () => {
    if (!token || selectedIds.size === 0) return
    try {
      await Promise.all(Array.from(selectedIds).map((id) => publishBlogPost(token, id)))
      toast.success(`${selectedIds.size} post(s) published`)
      loadPosts()
    } catch {
      toast.error("Failed to publish some posts")
    }
  }

  const handleBulkDelete = async () => {
    if (!token || selectedIds.size === 0) return
    try {
      await Promise.all(Array.from(selectedIds).map((id) => deleteBlogPost(token, id)))
      toast.success(`${selectedIds.size} post(s) deleted`)
      setBulkDeleteConfirm(false)
      loadPosts()
    } catch {
      toast.error("Failed to delete some posts")
    }
  }

  const draftCount = postsData?.draft_count ?? 0
  const publishedCount = postsData?.published_count ?? 0
  const scheduledCount = postsData?.scheduled_count ?? 0

  return (
    <AdminShell title="Blog Management">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Blog Management
          </h1>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
            {postsData?.total ?? 0} total posts &middot; {publishedCount} published &middot; {scheduledCount} scheduled &middot; {draftCount} drafts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAnalytics(!showAnalytics)}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium transition-colors ${
              showAnalytics
                ? "border-lsc-rose text-lsc-rose bg-lsc-rose/5"
                : "border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/60"
            }`}
            aria-label="Toggle analytics"
          >
            <BarChart3 className="w-4 h-4" aria-hidden="true" />
            Analytics
          </button>
          <button
            onClick={() => navigate("/staff/blog/new")}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 transition-colors"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            New Post
          </button>
        </div>
      </div>

      {/* Analytics */}
      {showAnalytics && analytics && <AnalyticsPanel analytics={analytics} />}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            loadPosts()
          }}
          className="flex gap-2 flex-1"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70" aria-hidden="true" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search posts..."
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              aria-label="Search posts"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium">
            Search
          </button>
        </form>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          <option value="draft">Drafts</option>
          <option value="published">Published</option>
          <option value="scheduled">Scheduled</option>
          <option value="trash">Trash</option>
        </select>
      </div>

      {/* Bulk action bar */}
      {!inTrashView && selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-lsc-cream dark:bg-earth-800 border border-lsc-rose/30">
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {selectedIds.size} selected
          </span>
          <button
            onClick={handleBulkPublish}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-xl bg-forest-600 text-white hover:bg-forest-700 transition-colors"
          >
            <Eye className="w-3.5 h-3.5" aria-hidden="true" />
            Publish selected
          </button>
          <button
            onClick={() => setBulkDeleteConfirm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-xl bg-status-danger-500 text-white hover:bg-status-danger-600 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
            Move selected to Trash
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose"
          >
            Clear
          </button>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="motion-safe:animate-pulse space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-14 bg-lsc-cream dark:bg-earth-800 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-lsc-border dark:border-earth-700">
          <table className="w-full">
            <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
              <tr>
                {!inTrashView && (
                  <th className="px-4 py-3 w-10">
                    <button onClick={toggleSelectAll} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] rounded-lg" aria-label="Select all">
                      {postsData && selectedIds.size === postsData.items.length ? (
                        <CheckSquare className="w-4 h-4 text-lsc-rose" />
                      ) : (
                        <Square className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/40" />
                      )}
                    </button>
                  </th>
                )}
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/60">
                  Title
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/60">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/60">
                  Views
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/60">
                  Date
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-lsc-dark/70 dark:text-lsc-cream/60">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {postsData?.items.map((post) => (
                <tr key={post.id} className={`hover:bg-lsc-cream/30 dark:hover:bg-earth-800/50 ${selectedIds.has(post.id) ? "bg-lsc-rose/5" : ""}`}>
                  {!inTrashView && (
                    <td className="px-4 py-3">
                      <button onClick={() => toggleSelect(post.id)} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] rounded-lg" aria-label={`Select ${post.title}`}>
                        {selectedIds.has(post.id) ? (
                          <CheckSquare className="w-4 h-4 text-lsc-rose" />
                        ) : (
                          <Square className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/40" />
                        )}
                      </button>
                    </td>
                  )}
                  <td className="px-4 py-3">
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{post.title}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-0.5">
                      {post.author_name} &middot; {post.read_time_minutes} min read
                    </p>
                    {inTrashView && post.deleted_at && (
                      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/50 mt-0.5">
                        Deleted {formatRelativeTime(post.deleted_at)}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge variant={
                      (post.status === "published" ? "success"
                      : post.status === "scheduled" ? "info"
                      : "warning") as StatusVariant
                    }>
                      {post.status}
                    </StatusBadge>
                    {post.status === "scheduled" && post.scheduled_at && (
                      <p className="text-xs text-status-info-600 dark:text-status-info-400 mt-0.5">
                        {new Date(post.scheduled_at).toLocaleString()}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-sm tabular-nums text-lsc-dark/70 dark:text-lsc-cream/60">
                    {(post.view_count ?? 0).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                    {post.status === "scheduled" && post.scheduled_at
                      ? new Date(post.scheduled_at).toLocaleDateString()
                      : post.published_at
                      ? new Date(post.published_at).toLocaleDateString()
                      : new Date(post.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {inTrashView ? (
                        <button
                          onClick={() => handleRestore(post)}
                          disabled={restoringIds.has(post.id)}
                          className="inline-flex items-center gap-1 px-2 py-1.5 text-sm rounded-lg hover:bg-forest-50 dark:hover:bg-forest-900/30 transition-colors text-forest-600 dark:text-forest-400 disabled:opacity-50 disabled:cursor-not-allowed"
                          aria-label={`Restore ${post.title}`}
                        >
                          <RotateCcw className="w-4 h-4" aria-hidden="true" />
                          Restore
                        </button>
                      ) : (
                      <>
                      <button
                        onClick={() => navigate(`/staff/blog/${post.id}/edit`)}
                        className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                        aria-label={`Edit ${post.title}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      {post.status === "draft" ? (
                        <>
                          <button
                            onClick={() => handlePublish(post)}
                            className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-forest-600"
                            aria-label={`Publish ${post.title}`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => { setScheduleConfirm(post); setScheduleDate("") }}
                            className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-status-info-600"
                            aria-label={`Schedule ${post.title}`}
                          >
                            <Clock className="w-4 h-4" />
                          </button>
                        </>
                      ) : post.status === "scheduled" ? (
                        <>
                          <button
                            onClick={() => handlePublish(post)}
                            className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-forest-600"
                            aria-label={`Publish ${post.title} now`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleUnpublish(post)}
                            className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-status-warning-600"
                            aria-label={`Unschedule ${post.title}`}
                          >
                            <EyeOff className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleUnpublish(post)}
                          className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-status-warning-600"
                          aria-label={`Unpublish ${post.title}`}
                        >
                          <EyeOff className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => setDeleteConfirm(post)}
                        className="p-1.5 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors text-status-danger-500"
                        aria-label={`Move ${post.title} to Trash`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {postsData && postsData.items.length === 0 && (
            <p className="px-4 py-8 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              {inTrashView ? "No deleted posts." : "No posts found."}
            </p>
          )}
        </div>
      )}

      {/* Schedule dialog */}
      {scheduleConfirm && (
        <ModalBackdrop onClose={() => { setScheduleConfirm(null); setScheduleDate("") }} title="Schedule post">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-sm mx-4 space-y-4">
            <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Schedule post</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Choose when to publish &ldquo;{scheduleConfirm.title}&rdquo;.
            </p>
            <input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              aria-label={t('aria.staffBlog.publishDateAndTime', 'Publish date and time')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              min={new Date().toISOString().slice(0, 16)}
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setScheduleConfirm(null); setScheduleDate("") }}
                className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSchedule}
                disabled={!scheduleDate}
                className="px-4 py-2 text-sm rounded-xl bg-status-info-600 text-white hover:bg-status-info-700 disabled:opacity-50"
              >
                Schedule
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Delete confirmation dialog */}
      {deleteConfirm && (
        <ModalBackdrop onClose={() => setDeleteConfirm(null)} title="Move post to Trash?">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-sm mx-4 space-y-4">
            <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Move post to Trash?</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              &ldquo;{deleteConfirm.title}&rdquo; will be moved to Trash. You can restore it from the Trash view.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm rounded-xl bg-status-danger-500 text-white hover:bg-status-danger-600"
              >
                Move to Trash
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
      {/* Bulk delete confirmation */}
      {bulkDeleteConfirm && (
        <ModalBackdrop onClose={() => setBulkDeleteConfirm(false)} title="Move posts to Trash?">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-sm mx-4 space-y-4">
            <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Move {selectedIds.size} post(s) to Trash?</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              The selected posts will be moved to Trash. You can restore them from the Trash view.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setBulkDeleteConfirm(false)}
                className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                className="px-4 py-2 text-sm rounded-xl bg-status-danger-500 text-white hover:bg-status-danger-600"
              >
                Move to Trash
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}
