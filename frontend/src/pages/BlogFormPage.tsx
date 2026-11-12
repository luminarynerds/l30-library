/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// frontend/src/pages/BlogFormPage.tsx
import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeft,
  Save,
  Eye,
  Clock,
  Loader2,
  History,
  RotateCcw,
  X,
  Maximize2,
  Minimize2,
} from "lucide-react"
import toast from "react-hot-toast"
import DOMPurify from "dompurify"
import { useAuth } from "@/contexts/AuthContext"
import { AdminShell } from "@/components/shells/AdminShell"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { useAutoSave } from "@/hooks/useAutoSave"
import AutoSaveIndicator from "@/components/AutoSaveIndicator"
import RichTextEditor, { type RichTextEditorHandle } from "@/components/editor/RichTextEditor"
import MediaLibraryPanel from "@/components/blog/MediaLibraryPanel"
import ConfirmDialog from "@/components/ConfirmDialog"
import { validateBlogBodyImages } from "@/lib/blog-image-validation"
import {
  createBlogPost,
  updateBlogPost,
  scheduleBlogPost,
  getAdminPost,
  getPostVersions,
  getPostVersion,
  restorePostVersion,
  uploadBlogMedia,
  type BlogPostFormData,
  type BlogPostVersionListItem,
  type BlogPostVersionResponse,
  getBlogTags,
  type BlogTag,
} from "@/services/blog-api"

export default function BlogFormPage(): React.ReactElement {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const { token } = useAuth()
  const isEdit = !!id

  const [formData, setFormData] = useState<BlogPostFormData>({
    title: "",
    slug: "",
    body: "",
    tldr: "",
    meta_description: "",
    featured_image: "",
    author_name: "Marlene W., Director",
    author_role: "Director",
    status: "draft",
    series_name: "",
    series_order: undefined,
    tags: [],
  })
  const [tagInput, setTagInput] = useState("")
  const [isSaving, setIsSaving] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [allTags, setAllTags] = useState<BlogTag[]>([])
  const [showTagSuggestions, setShowTagSuggestions] = useState(false)
  const [showPublishChecklist, setShowPublishChecklist] = useState(false)
  const initialFormRef = useRef<string>("")
  const [showPreview, setShowPreview] = useState(false)
  const [scheduleDate, setScheduleDate] = useState<string>("")
  const [loadingPost, setLoadingPost] = useState(false)
  const [showVersions, setShowVersions] = useState(false)
  const [versions, setVersions] = useState<BlogPostVersionListItem[]>([])
  const [selectedVersion, setSelectedVersion] = useState<BlogPostVersionResponse | null>(null)
  const [loadingVersions, setLoadingVersions] = useState(false)
  const [versionToRestore, setVersionToRestore] = useState<number | null>(null)
  const [focusMode, setFocusMode] = useState(false)
  const [showMediaLibrary, setShowMediaLibrary] = useState(false)
  // Tracks which post id has been loaded into the form, so switching posts
  // in place (route param change without unmount) reloads instead of leaving
  // the previous post's content in the form (which autosave would then write
  // to the new id).
  const loadedIdRef = useRef<string | undefined>(undefined)
  const rteRef = useRef<RichTextEditorHandle>(null)

  const handleBodyChange = useCallback((html: string) => {
    setFormData((prev) => ({ ...prev, body: html }))
  }, [])

  const blogImageUpload = useCallback(async (file: File) => {
    if (!token) throw new Error("Not signed in")
    const result = await uploadBlogMedia(token, file)
    return { url: result.url }
  }, [token])

  // Load existing post for editing
  useEffect(() => {
    if (!isEdit || !id || !token || loadedIdRef.current === id) return
    setLoadingPost(true)
    getAdminPost(token, parseInt(id))
      .then((post) => {
        if (!post) return
        setFormData({
          title: post.title,
          slug: post.slug,
          body: post.body,
          tldr: post.tldr || "",
          meta_description: post.meta_description || "",
          featured_image: post.featured_image || "",
          author_name: post.author_name,
          author_role: post.author_role || "",
          status: post.status,
          series_name: post.series_name || "",
          series_order: post.series_order ?? undefined,
          tags: post.tags.map((t) => t.name),
        })
        if (post.scheduled_at) {
          setScheduleDate(new Date(post.scheduled_at).toISOString().slice(0, 16))
        }
        rteRef.current?.setContent(post.body)
        loadedIdRef.current = id
      })
      .finally(() => setLoadingPost(false))

  }, [id, isEdit, token])

  // Auto-generate slug from title
  useEffect(() => {
    if (!isEdit && formData.title) {
      const slug = formData.title
        .toLowerCase()
        .replace(/[^\w\s-]/g, "")
        .replace(/[\s_]+/g, "-")
        .replace(/-+/g, "-")
        .trim()
      setFormData((prev) => ({ ...prev, slug }))
    }
  }, [formData.title, isEdit])

  // Fetch existing tags for autocomplete
  useEffect(() => {
    getBlogTags().then(setAllTags).catch(() => {})
  }, [])

  // Track dirty state
  useEffect(() => {
    const current = JSON.stringify(formData)
    if (!initialFormRef.current) {
      initialFormRef.current = current
      return
    }
    setIsDirty(current !== initialFormRef.current)
  }, [formData])

  // Unsaved changes warning
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault()
      }
    }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [isDirty])

  // Auto-save drafts on a 2s debounce for existing draft posts.
  // The AutoSaveIndicator in the header surfaces saving/saved/error status,
  // so users (especially ND users) can see their work is preserved without
  // the manual Save button being the only signal.
  const autoSaveCallback = useCallback(async (data: BlogPostFormData) => {
    if (!isEdit || !id || !token) return
    if (data.status !== "draft") return
    const payload = {
      ...data,
      series_name: data.series_name || undefined,
      series_order: data.series_order ?? undefined,
      tldr: data.tldr || undefined,
      meta_description: data.meta_description || "",
      featured_image: data.featured_image || undefined,
      author_role: data.author_role || undefined,
    }
    await updateBlogPost(token, parseInt(id), payload)
    initialFormRef.current = JSON.stringify(data)
    setIsDirty(false)
  }, [isEdit, id, token])

  const { status: autoSaveStatus, lastSaved: autoSaveLastSaved, error: autoSaveError } = useAutoSave({
    data: formData,
    onSave: autoSaveCallback,
    delay: 2000,
    enabled: isEdit && !!id && !!token && formData.status === "draft" && !isSaving,
  })

  const handleSave = async (publishOnSave = false) => {
    if (!token || !formData.title.trim()) {
      toast.error("Title is required")
      return
    }

    setIsSaving(true)
    try {
      const data = {
        ...formData,
        status: publishOnSave ? "published" : formData.status,
        series_name: formData.series_name || undefined,
        series_order: formData.series_order ?? undefined,
        tldr: formData.tldr || undefined,
        meta_description: formData.meta_description || "",
        featured_image: formData.featured_image || undefined,
        author_role: formData.author_role || undefined,
      }

      if (isEdit && id) {
        await updateBlogPost(token, parseInt(id), data)
        toast.success("Post updated")
      } else {
        await createBlogPost(token, data)
        toast.success("Post created")
      }
      navigate("/staff/blog")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }


  // Ctrl+S / Cmd+S keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault()
        handleSave(false)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  })

  const loadVersions = async () => {
    if (!token || !id) return
    setLoadingVersions(true)
    try {
      const data = await getPostVersions(token, parseInt(id))
      setVersions(data)
    } catch {
      toast.error("Failed to load versions")
    } finally {
      setLoadingVersions(false)
    }
  }

  const viewVersion = async (versionId: number) => {
    if (!token || !id) return
    try {
      const data = await getPostVersion(token, parseInt(id), versionId)
      setSelectedVersion(data)
    } catch {
      toast.error("Failed to load version")
    }
  }

  const handleRestore = async (versionId: number) => {
    if (!token || !id) return
    try {
      const restored = await restorePostVersion(token, parseInt(id), versionId)
      setFormData({
        title: restored.title,
        slug: restored.slug,
        body: restored.body,
        tldr: restored.tldr || "",
        meta_description: restored.meta_description || "",
        featured_image: restored.featured_image || "",
        author_name: restored.author_name,
        author_role: restored.author_role || "",
        status: restored.status,
        series_name: restored.series_name || "",
        series_order: restored.series_order ?? undefined,
        tags: restored.tags.map((t) => t.name),
      })
      rteRef.current?.setContent(restored.body)
      setSelectedVersion(null)
      setShowVersions(false)
      toast.success("Version restored")
    } catch {
      toast.error("Failed to restore version")
    }
  }

  const filteredTagSuggestions = allTags.filter(
    (t) => t.name.toLowerCase().includes(tagInput.toLowerCase()) && !formData.tags.includes(t.name)
  ).slice(0, 8)

  const handleAddTag = (tagName?: string) => {
    const tag = (tagName || tagInput).trim()
    if (tag && !formData.tags.includes(tag)) {
      setFormData((prev) => ({ ...prev, tags: [...prev.tags, tag] }))
      setTagInput("")
      setShowTagSuggestions(false)
    }
  }

  const handleRemoveTag = (tag: string) => {
    setFormData((prev) => ({ ...prev, tags: prev.tags.filter((t) => t !== tag) }))
  }

  const handleSchedule = async () => {
    if (!token || !formData.title.trim()) {
      toast.error("Title is required")
      return
    }
    if (!scheduleDate) {
      toast.error("Schedule date is required")
      return
    }

    setIsSaving(true)
    try {
      const utcDate = new Date(scheduleDate).toISOString()
      let postId: number

      if (isEdit && id) {
        // Save changes first, then schedule
        const data = {
          ...formData,
          series_name: formData.series_name || undefined,
          series_order: formData.series_order ?? undefined,
          tldr: formData.tldr || undefined,
          meta_description: formData.meta_description || "",
          author_role: formData.author_role || undefined,
        }
        const updated = await updateBlogPost(token, parseInt(id), data)
        postId = updated.id
      } else {
        // Create as draft first, then schedule
        const data = {
          ...formData,
          status: "draft",
          series_name: formData.series_name || undefined,
          series_order: formData.series_order ?? undefined,
          tldr: formData.tldr || undefined,
          meta_description: formData.meta_description || "",
          author_role: formData.author_role || undefined,
        }
        const created = await createBlogPost(token, data)
        postId = created.id
      }

      await scheduleBlogPost(token, postId, utcDate)
      toast.success("Post scheduled")
      navigate("/staff/blog")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to schedule")
    } finally {
      setIsSaving(false)
    }
  }

  const handleMediaInsert = useCallback(
    ({ url, alt, decorative }: { url: string; alt: string; decorative: boolean }) => {
      rteRef.current?.insertImage({ url, alt, decorative })
    },
    []
  )

  if (loadingPost) {
    return (
      <div className="max-w-4xl mx-auto flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  return (
    <AdminShell title={isEdit ? "Edit Post" : "New Post"} maxWidth="max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate("/staff/blog")}
          className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Back to blog management
        </button>
        <div className="flex items-center gap-2">
          {isEdit && (
            <button
              onClick={() => {
                setShowVersions(!showVersions)
                if (!showVersions) loadVersions()
                setSelectedVersion(null)
              }}
              className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/40"
            >
              <History className="w-4 h-4" aria-hidden="true" />
              Versions
            </button>
          )}
          <button
            onClick={() => setFocusMode(!focusMode)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl border transition-colors ${
              focusMode
                ? "border-lsc-rose/40 bg-lsc-rose/10 text-lsc-rose"
                : "border-lsc-border dark:border-earth-700 hover:border-lsc-rose/40"
            }`}
            title={focusMode ? "Exit focus mode" : "Focus mode"}
          >
            {focusMode ? <Minimize2 className="w-4 h-4" aria-hidden="true" /> : <Maximize2 className="w-4 h-4" aria-hidden="true" />}
            {focusMode ? "Exit focus" : "Focus"}
          </button>
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/40"
          >
            <Eye className="w-4 h-4" aria-hidden="true" />
            {showPreview ? "Edit" : "Preview"}
          </button>
          {isEdit && formData.status === "draft" && (
            <AutoSaveIndicator
              status={autoSaveStatus}
              lastSaved={autoSaveLastSaved}
              error={autoSaveError}
              className="mr-1"
            />
          )}
          <button
            onClick={() => handleSave(false)}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 font-medium hover:border-lsc-rose/40"
          >
            {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Save className="w-4 h-4" />}
            Save draft
          </button>
          <button
            onClick={() => setShowPublishChecklist(true)}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90"
          >
            Publish now
          </button>
          <button
            onClick={handleSchedule}
            disabled={isSaving || !scheduleDate}
            className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-xl bg-status-info-600 text-white font-medium hover:bg-status-info-700 disabled:opacity-50"
          >
            <Clock className="w-4 h-4" aria-hidden="true" />
            Schedule
          </button>
        </div>
      </div>

      <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        {isEdit ? "Edit Post" : "New Post"}
      </h1>

      {/* Version History Panel */}
      {showVersions && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">Version History</h2>
            <button
              onClick={() => { setShowVersions(false); setSelectedVersion(null) }}
              className="p-1 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
              aria-label="Close version history"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {loadingVersions ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : versions.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50 py-4">No previous versions yet. Versions are created each time you save changes.</p>
          ) : selectedVersion ? (
            /* Version detail view */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setSelectedVersion(null)}
                  className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose"
                >
                  <ArrowLeft className="w-3 h-3" /> Back to list
                </button>
                <button
                  onClick={() => setVersionToRestore(selectedVersion.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-xl bg-lsc-rose text-white hover:bg-lsc-rose/90"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Restore this version
                </button>
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                Version {selectedVersion.version_number} -- {new Date(selectedVersion.created_at).toLocaleString()}
                {selectedVersion.created_by && ` by ${selectedVersion.created_by}`}
              </div>
              <div className="space-y-3">
                <div>
                  <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/40 uppercase tracking-wide">Title</span>
                  <p className="mt-1 text-lsc-dark dark:text-lsc-cream">{selectedVersion.title}</p>
                </div>
                {selectedVersion.tldr && (
                  <div>
                    <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/40 uppercase tracking-wide">TL;DR</span>
                    <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{selectedVersion.tldr}</p>
                  </div>
                )}
                <div>
                  <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/40 uppercase tracking-wide">Content</span>
                  <div
                    className="mt-1 prose prose-sm dark:prose-invert max-w-none p-4 rounded-xl bg-lsc-cream/30 dark:bg-earth-900/50 border border-lsc-border dark:border-earth-700"
                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(selectedVersion.body) }}
                  />
                </div>
              </div>
            </div>
          ) : (
            /* Version list */
            <div className="divide-y divide-lsc-border dark:divide-earth-700">
              {versions.map((v) => (
                <button
                  key={v.id}
                  onClick={() => viewVersion(v.id)}
                  className="w-full flex items-center justify-between py-3 px-2 text-left hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 rounded-lg transition-colors"
                >
                  <div>
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      v{v.version_number}
                    </span>
                    <span className="ml-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 truncate">
                      {v.title}
                    </span>
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/40 whitespace-nowrap ml-4">
                    {new Date(v.created_at).toLocaleDateString()}{" "}
                    {new Date(v.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    {v.created_by && ` -- ${v.created_by}`}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {showPreview ? (
        /* Preview mode */
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-8 space-y-6">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{formData.title || "Untitled"}</h2>
          {formData.tldr && (
            <aside className="px-5 py-4 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl border-l-4 border-lsc-rose">
              <p className="text-sm font-medium mb-1">Quick version</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{formData.tldr}</p>
            </aside>
          )}
          <div
            className="prose prose-lg dark:prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(formData.body) }}
          />
        </div>
      ) : (
        /* Edit mode */
        <div className="space-y-4">
          {!focusMode && (<>
          {/* Title */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Title
            </label>
            <input
              id="title"
              type="text"
              value={formData.title}
              onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-lg"
              placeholder="Post title"
            />
          </div>

          {/* Slug */}
          <div>
            <label htmlFor="slug" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Slug
            </label>
            <input
              id="slug"
              type="text"
              value={formData.slug}
              onChange={(e) => setFormData((prev) => ({ ...prev, slug: e.target.value }))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm font-mono"
              placeholder="post-url-slug"
            />
          </div>

          {/* TL;DR */}
          <div>
            <label htmlFor="tldr" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              TL;DR (optional)
            </label>
            <textarea
              id="tldr"
              value={formData.tldr}
              onChange={(e) => setFormData((prev) => ({ ...prev, tldr: e.target.value }))}
              rows={2}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              placeholder="Quick summary for readers who are short on time"
            />
          </div>

          {/* Meta Description */}
          <div>
            <label htmlFor="meta_description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Meta description (SEO)
            </label>
            <textarea
              id="meta_description"
              value={formData.meta_description}
              onChange={(e) => setFormData((prev) => ({ ...prev, meta_description: e.target.value }))}
              rows={2}
              maxLength={160}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              placeholder="Custom search engine description. Falls back to TL;DR if empty."
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
              {formData.meta_description?.length || 0}/160 characters
            </p>
          </div>

          {/* Featured Image */}
          <div>
            <label htmlFor="featured_image" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Featured image URL (optional)
            </label>
            <input
              id="featured_image"
              type="url"
              value={formData.featured_image || ""}
              onChange={(e) => setFormData((prev) => ({ ...prev, featured_image: e.target.value }))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
              placeholder="https://..."
            />
            {formData.featured_image && (
              <div className="mt-2 rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700 max-h-48">
                <img src={formData.featured_image} alt="Featured image preview" loading="lazy" className="w-full h-full object-cover max-h-48" />
              </div>
            )}
          </div>

          </>)}

          {/* Body -- TipTap Editor */}
          <div>
            {!focusMode && (
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Content
            </label>
            )}
            <RichTextEditor
              ref={rteRef}
              defaultValue={formData.body}
              onChange={handleBodyChange}
              onImageUpload={blogImageUpload}
              onOpenMediaLibrary={() => setShowMediaLibrary(true)}
              focusMode={focusMode}
              ariaLabel="Post content"
            />
          </div>

          {!focusMode && (<>
          {/* Tags */}
          <div>
            <label htmlFor="tags" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Tags
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {formData.tags.map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 px-2.5 py-1 text-sm rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="hover:text-status-danger-500"
                    aria-label={`Remove tag ${tag}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            <div className="relative">
              <div className="flex gap-2">
                <input
                  id="tags"
                  type="text"
                  value={tagInput}
                  onChange={(e) => { setTagInput(e.target.value); setShowTagSuggestions(true) }}
                  onFocus={() => setShowTagSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowTagSuggestions(false), 200)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      handleAddTag()
                    }
                  }}
                  className="flex-1 px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                  placeholder="Add a tag and press Enter"
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => handleAddTag()}
                  className="px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 text-sm hover:border-lsc-rose/40"
                >
                  Add
                </button>
              </div>
              {showTagSuggestions && tagInput && filteredTagSuggestions.length > 0 && (
                <div className="absolute z-10 mt-1 w-full bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg max-h-40 overflow-y-auto">
                  {filteredTagSuggestions.map((tag) => (
                    <button
                      key={tag.id}
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => handleAddTag(tag.name)}
                      className="w-full text-left px-4 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                    >
                      {tag.name}
                      {tag.post_count != null && (
                        <span className="ml-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/40">({tag.post_count})</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Author */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="author_name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Author name
              </label>
              <input
                id="author_name"
                type="text"
                value={formData.author_name}
                onChange={(e) => setFormData((prev) => ({ ...prev, author_name: e.target.value }))}
                className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="author_role" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Author role (optional)
              </label>
              <input
                id="author_role"
                type="text"
                value={formData.author_role}
                onChange={(e) => setFormData((prev) => ({ ...prev, author_role: e.target.value }))}
                className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>

          {/* Series */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="series_name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Series name (optional)
              </label>
              <input
                id="series_name"
                type="text"
                value={formData.series_name}
                onChange={(e) => setFormData((prev) => ({ ...prev, series_name: e.target.value }))}
                className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                placeholder="e.g., Beginning of the End"
              />
            </div>
            <div>
              <label htmlFor="series_order" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Series order (optional)
              </label>
              <input
                id="series_order"
                type="number"
                min={1}
                value={formData.series_order ?? ""}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    series_order: e.target.value ? parseInt(e.target.value) : undefined,
                  }))
                }
                className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                placeholder="1"
              />
            </div>
          </div>

          {/* Schedule */}
          <div>
            <label htmlFor="schedule_date" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Schedule for (optional)
            </label>
            <input
              id="schedule_date"
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              min={new Date().toISOString().slice(0, 16)}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
            {scheduleDate && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
                Will publish at {new Date(scheduleDate).toLocaleString()}. Use the Schedule button to save.
              </p>
            )}
          </div>
          </>)}
        </div>
      )}

      {/* Pre-publish checklist */}
      {showPublishChecklist && (
        <ModalBackdrop onClose={() => setShowPublishChecklist(false)} title="Pre-publish checklist">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-md mx-4 space-y-4">
            <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Pre-publish checklist</h2>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${formData.title.trim() ? "bg-forest-100 text-forest-700" : "bg-status-danger-100 text-status-danger-700"}`}>
                  {formData.title.trim() ? "\u2713" : "!"}
                </span>
                <span className="text-lsc-dark dark:text-lsc-cream">Title is set</span>
              </li>
              <li className="flex items-center gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${formData.body.trim().length > 50 ? "bg-forest-100 text-forest-700" : "bg-status-warning-100 text-status-warning-700"}`}>
                  {formData.body.trim().length > 50 ? "\u2713" : "!"}
                </span>
                <span className="text-lsc-dark dark:text-lsc-cream">Body has content</span>
              </li>
              <li className="flex items-center gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${formData.tldr?.trim() ? "bg-forest-100 text-forest-700" : "bg-status-warning-100 text-status-warning-700"}`}>
                  {formData.tldr?.trim() ? "\u2713" : "!"}
                </span>
                <span className="text-lsc-dark dark:text-lsc-cream">TL;DR summary</span>
              </li>
              <li className="flex items-center gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${formData.author_name.trim() ? "bg-forest-100 text-forest-700" : "bg-status-danger-100 text-status-danger-700"}`}>
                  {formData.author_name.trim() ? "\u2713" : "!"}
                </span>
                <span className="text-lsc-dark dark:text-lsc-cream">Author name</span>
              </li>
              {(() => {
                const imageCheck = validateBlogBodyImages(formData.body)
                const ok = imageCheck.valid
                return (
                  <li className="flex items-center gap-2">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${ok ? "bg-forest-100 text-forest-700" : "bg-status-warning-100 text-status-warning-700"}`}>
                      {ok ? "\u2713" : "!"}
                    </span>
                    <span className="text-lsc-dark dark:text-lsc-cream">
                      {imageCheck.totalImages === 0
                        ? "Image alt text"
                        : ok
                          ? `Image alt text (${imageCheck.totalImages} image${imageCheck.totalImages === 1 ? "" : "s"})`
                          : `${imageCheck.failingImages} of ${imageCheck.totalImages} image${imageCheck.totalImages === 1 ? "" : "s"} missing alt text`}
                    </span>
                  </li>
                )
              })()}
            </ul>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowPublishChecklist(false)}
                className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowPublishChecklist(false); handleSave(true) }}
                disabled={!formData.title.trim() || !formData.author_name.trim()}
                className="px-4 py-2 text-sm rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                Publish anyway
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Version restore confirmation (replaces window.confirm) */}
      <ConfirmDialog
        isOpen={versionToRestore !== null}
        title="Restore this version?"
        message="The current content will be saved as a new version before this one is restored."
        confirmText="Restore version"
        confirmVariant="primary"
        onConfirm={async () => {
          if (versionToRestore !== null) {
            await handleRestore(versionToRestore)
          }
          setVersionToRestore(null)
        }}
        onCancel={() => setVersionToRestore(null)}
      />

      {/* Media library (previously-uploaded images) */}
      <MediaLibraryPanel
        isOpen={showMediaLibrary}
        token={token}
        onClose={() => setShowMediaLibrary(false)}
        onInsert={handleMediaInsert}
      />
    </AdminShell>
  )
}
