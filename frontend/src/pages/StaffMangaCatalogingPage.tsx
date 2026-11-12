/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  listMangaTemplates,
  createMangaTemplate,
  deleteMangaTemplate,
  listMangaVolumes,
  quickAddMangaVolume,
  copyAndIncrementVolume,
  batchCreateMangaVolumes,
  isbnLookup,
  getSeriesInfo,
  getMangaCatalogingStats,
  MangaCatalogingTemplate,
  MangaVolumeRecord,
  ISBNLookupResult,
  SeriesInfo,
  MangaCatalogingStats,
} from "@/api/manga-cataloging-api"
import {
  Book, Plus, Copy, Search, Loader2, Trash2, X, BarChart3,
  BookOpen, Image, Layers,
} from "lucide-react"
import toast from "react-hot-toast"
import { clean } from '@/lib/utils'
import { formatGenre } from '@/utils/format-utils'
import { t } from '@/i18n'

type ActiveTab = "quick-add" | "templates" | "batch" | "volumes" | "stats"

export default function StaffMangaCatalogingPage(): React.ReactElement {
  const { user, isLoading: authLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<ActiveTab>("quick-add")
  const [templates, setTemplates] = useState<MangaCatalogingTemplate[]>([])
  const [volumes, setVolumes] = useState<MangaVolumeRecord[]>([])
  const [stats, setStats] = useState<MangaCatalogingStats | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Quick Add state
  const [seriesTitle, setSeriesTitle] = useState("")
  const [seriesInfo, setSeriesInfo] = useState<SeriesInfo | null>(null)
  const [quickAddForm, setQuickAddForm] = useState({
    title: "", author: "", isbn: "", publisher: "",
    original_language: "Japanese", publication_date: "",
    volume_number: 1, template_id: undefined as number | undefined,
    auto_fetch_cover: true,
  })
  const [isbnLookupResult, setIsbnLookupResult] = useState<ISBNLookupResult | null>(null)
  const [isLookingUp, setIsLookingUp] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Template form state
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [templateForm, setTemplateForm] = useState({
    name: "", series_title: "", author: "", publisher: "",
    original_language: "Japanese", genre: "manga,graphic novels",
    subjects: "manga,graphic novels,Japanese comics",
    format: "volume", isbn_pattern: "", page_count_average: "",
    auto_increment_volume: true, auto_fetch_cover: true,
    auto_populate_series_info: true,
  })

  // Batch state
  const [batchSeriesTitle, setBatchSeriesTitle] = useState("")
  const [batchVolumes, setBatchVolumes] = useState<Array<{ volume_number: number; title: string; isbn: string }>>([
    { volume_number: 1, title: "", isbn: "" },
  ])
  const [isBatchCreating, setIsBatchCreating] = useState(false)

  // Copy & increment state
  const [copySourceId, setCopySourceId] = useState("")
  const [copyNewVolNum, setCopyNewVolNum] = useState("")
  const [copyNewIsbn, setCopyNewIsbn] = useState("")
  const [isCopying, setIsCopying] = useState(false)

  // Volume search state
  const [volumeSearchSeries, setVolumeSearchSeries] = useState("")
  const [volumeLoadError, setVolumeLoadError] = useState<string | null>(null)

  const loadTemplates = useCallback(async () => {
    try {
      const data = await listMangaTemplates()
      setTemplates(data)
    } catch {
      // templates load silently
    }
  }, [])

  const loadVolumes = useCallback(async (series?: string) => {
    setVolumeLoadError(null)
    try {
      const data = await listMangaVolumes(series || undefined)
      setVolumes(data)
    } catch (err) {
      setVolumeLoadError(err instanceof Error ? err.message : 'Failed to load volumes')
    }
  }, [])

  const loadStats = useCallback(async () => {
    try {
      const data = await getMangaCatalogingStats()
      setStats(data)
    } catch {
      // stats load silently
    }
  }, [])

  useEffect(() => {
    if (!authLoading && user) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch; setState runs after await, not synchronously
      loadTemplates()
    }
  }, [authLoading, user, loadTemplates])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch; setState runs after await, not synchronously
    if (activeTab === "volumes") loadVolumes()
    if (activeTab === "stats") loadStats()
  }, [activeTab, loadVolumes, loadStats])

  // Fetch series info when series title changes
  const handleFetchSeriesInfo = async () => {
    if (!seriesTitle.trim()) return
    setIsLoading(true)
    try {
      const info = await getSeriesInfo(seriesTitle)
      setSeriesInfo(info)
      setQuickAddForm(prev => ({
        ...prev,
        volume_number: info.next_volume_number,
        publisher: (info.auto_populate_info.publisher as string) || prev.publisher,
        original_language: (info.auto_populate_info.original_language as string) || prev.original_language,
      }))
      toast.success(t('toast.staffMangaCataloging.seriesFoundTotalvolumesVolumes', { totalvolumes: info.total_volumes }))
    } catch {
      setSeriesInfo(null)
      toast.error(t('toast.staffMangaCataloging.seriesNotFoundWillCreate'))
    }
    setIsLoading(false)
  }

  // ISBN Lookup
  const handleISBNLookup = async () => {
    const isbn = quickAddForm.isbn.trim()
    if (!isbn) return
    setIsLookingUp(true)
    try {
      const result = await isbnLookup(isbn)
      setIsbnLookupResult(result)
      if (result.found) {
        setQuickAddForm(prev => ({
          ...prev,
          title: result.title || prev.title,
          author: result.author || prev.author,
          publisher: result.publisher || prev.publisher,
          publication_date: result.publish_date || prev.publication_date,
        }))
        toast.success(t('toast.staffMangaCataloging.isbnFoundTitle', { title: result.title }))
      } else {
        toast.error(t('toast.acquisition.isbnNotFoundInExternal'))
      }
    } catch {
      toast.error(t('toast.staffMangaCataloging.isbnLookupFailed'))
    }
    setIsLookingUp(false)
  }

  // Quick Add Volume
  const handleQuickAdd = async () => {
    if (!seriesTitle.trim() || !quickAddForm.title.trim()) {
      toast.error(t('toast.staffMangaCataloging.seriesTitleAndVolumeTitle'))
      return
    }
    setIsSaving(true)
    try {
      await quickAddMangaVolume(clean({
        series_title: seriesTitle,
        volume_number: quickAddForm.volume_number,
        title: quickAddForm.title,
        ...(quickAddForm.author ? { author: quickAddForm.author } : {}),
        ...(quickAddForm.isbn ? { isbn: quickAddForm.isbn } : {}),
        ...(quickAddForm.publisher ? { publisher: quickAddForm.publisher } : {}),
        ...(quickAddForm.original_language ? { original_language: quickAddForm.original_language } : {}),
        ...(quickAddForm.publication_date ? { publication_date: quickAddForm.publication_date } : {}),
        template_id: quickAddForm.template_id,
        auto_fetch_cover: quickAddForm.auto_fetch_cover,
      }))
      toast.success(t('toast.staffMangaCataloging.volumeVolumenumberAddedToSeriestitle', { volumenumber: quickAddForm.volume_number, seriesTitle: seriesTitle }))
      // Increment for next volume
      setQuickAddForm(prev => ({
        ...prev,
        volume_number: prev.volume_number + 1,
        title: "",
        isbn: "",
        publication_date: "",
      }))
      setIsbnLookupResult(null)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to add volume"
      toast.error(msg)
    }
    setIsSaving(false)
  }

  // Create Template
  const handleCreateTemplate = async () => {
    if (!templateForm.name.trim() || !templateForm.series_title.trim()) {
      toast.error(t('toast.staffMangaCataloging.templateNameAndSeriesTitle'))
      return
    }
    setIsSaving(true)
    try {
      await createMangaTemplate({
        name: templateForm.name,
        series_title: templateForm.series_title,
        ...(templateForm.author ? { author: templateForm.author } : {}),
        ...(templateForm.publisher ? { publisher: templateForm.publisher } : {}),
        original_language: templateForm.original_language,
        genre: templateForm.genre,
        subjects: templateForm.subjects,
        format: templateForm.format,
        ...(templateForm.isbn_pattern ? { isbn_pattern: templateForm.isbn_pattern } : {}),
        page_count_average: templateForm.page_count_average ? Number(templateForm.page_count_average) : undefined,
        auto_increment_volume: templateForm.auto_increment_volume,
        auto_fetch_cover: templateForm.auto_fetch_cover,
        auto_populate_series_info: templateForm.auto_populate_series_info,
      } as Partial<MangaCatalogingTemplate>)
      toast.success(t('toast.adminBanTracker.templateCreated'))
      setShowTemplateForm(false)
      loadTemplates()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create template"
      toast.error(msg)
    }
    setIsSaving(false)
  }

  // Delete Template
  const handleDeleteTemplate = async (id: number) => {
    try {
      await deleteMangaTemplate(id)
      toast.success(t('toast.adminBanTracker.templateDeleted'))
      loadTemplates()
    } catch {
      toast.error(t('toast.staffMangaCataloging.failedToDeleteTemplate'))
    }
  }

  // Copy & Increment
  const handleCopyIncrement = async () => {
    if (!copySourceId || !copyNewVolNum) {
      toast.error(t('toast.staffMangaCataloging.sourceVolumeIdAndNew'))
      return
    }
    setIsCopying(true)
    try {
      await copyAndIncrementVolume({
        source_volume_id: Number(copySourceId),
        new_volume_number: Number(copyNewVolNum),
        ...(copyNewIsbn ? { isbn: copyNewIsbn } : {}),
      })
      toast.success(t('toast.staffMangaCataloging.volumeCopynewvolnumCreatedFromCopy', { copyNewVolNum: copyNewVolNum }))
      setCopySourceId("")
      setCopyNewVolNum("")
      setCopyNewIsbn("")
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Copy failed"
      toast.error(msg)
    }
    setIsCopying(false)
  }

  // Batch Create
  const handleBatchCreate = async () => {
    if (!batchSeriesTitle.trim() || batchVolumes.length === 0) {
      toast.error(t('toast.staffMangaCataloging.seriesTitleAndAtLeast'))
      return
    }
    setIsBatchCreating(true)
    try {
      const result = await batchCreateMangaVolumes({
        series_title: batchSeriesTitle,
        volumes: batchVolumes.map(v => ({
          volume_number: v.volume_number,
          title: v.title || `${batchSeriesTitle} Vol. ${v.volume_number}`,
          ...(v.isbn ? { isbn: v.isbn } : {}),
        })),
      })
      toast.success(t('toast.staffMangaCataloging.batchCreatedCreatedtotalvolumesVolumes', { created: result.created, totalvolumes: result.total_volumes }))
      if (result.failed > 0) {
        toast.error(t('toast.staffMangaCataloging.failedVolumesFailed', { failed: result.failed }))
      }
      setBatchVolumes([{ volume_number: 1, title: "", isbn: "" }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Batch creation failed"
      toast.error(msg)
    }
    setIsBatchCreating(false)
  }

  const addBatchRow = () => {
    const lastNum = batchVolumes[batchVolumes.length - 1]?.volume_number || 0
    setBatchVolumes(prev => [...prev, { volume_number: lastNum + 1, title: "", isbn: "" }])
  }

  const removeBatchRow = (index: number) => {
    setBatchVolumes(prev => prev.filter((_, i) => i !== index))
  }

  const updateBatchRow = (index: number, field: string, value: string | number) => {
    setBatchVolumes(prev => prev.map((row, i) => i === index ? { ...row, [field]: value } : row))
  }

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  const tabs: { key: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { key: "quick-add", label: "Quick Add", icon: <Plus className="w-4 h-4" /> },
    { key: "templates", label: "Templates", icon: <BookOpen className="w-4 h-4" /> },
    { key: "batch", label: "Batch Create", icon: <Layers className="w-4 h-4" /> },
    { key: "volumes", label: "Volumes", icon: <Book className="w-4 h-4" /> },
    { key: "stats", label: "Statistics", icon: <BarChart3 className="w-4 h-4" /> },
  ]

  return (
    <AdminShell title="Manga Cataloging" subtitle="Efficient cataloging for manga series with templates, auto-fill, and batch operations">
        <div className="max-w-6xl mx-auto">
          <div className="mb-6">
          </div>

          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-1 mb-6">
            {tabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? "bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Quick Add Tab */}
          {activeTab === "quick-add" && (
            <div className="space-y-6">
              {/* Series Lookup */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6">
                <h2 className="font-serif text-lg font-semibold mb-4">Series Lookup</h2>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder={t('placeholder.staffMangaCataloging.enterSeriesTitleEg')}
                    value={seriesTitle}
                    onChange={e => setSeriesTitle(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleFetchSeriesInfo()}
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                  />
                  <button
                    onClick={handleFetchSeriesInfo}
                    disabled={isLoading || !seriesTitle.trim()}
                    className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
                  >
                    {isLoading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
                    Lookup
                  </button>
                </div>
                {seriesInfo && (
                  <div className="mt-3 p-3 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-lg text-sm">
                    <p><strong>Volumes in series:</strong> {seriesInfo.total_volumes}</p>
                    <p><strong>Next volume:</strong> #{seriesInfo.next_volume_number}</p>
                    {seriesInfo.auto_populate_info.publisher && (
                      <p><strong>Publisher:</strong> {String(seriesInfo.auto_populate_info.publisher)}</p>
                    )}
                    {seriesInfo.auto_populate_info.genre && (
                      <p><strong>Genre:</strong> {formatGenre(String(seriesInfo.auto_populate_info.genre))}</p>
                    )}
                  </div>
                )}
              </div>

              {/* ISBN Lookup & Auto-Fill */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6">
                <h2 className="font-serif text-lg font-semibold mb-4">ISBN Lookup & Auto-Fill</h2>
                <div className="flex gap-3 mb-4">
                  <input
                    type="text"
                    placeholder={t('placeholder.staffMangaCataloging.enterIsbnEg9781421500015')}
                    value={quickAddForm.isbn}
                    onChange={e => setQuickAddForm(prev => ({ ...prev, isbn: e.target.value }))}
                    onKeyDown={e => e.key === "Enter" && handleISBNLookup()}
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                  />
                  <button
                    onClick={handleISBNLookup}
                    disabled={isLookingUp || !quickAddForm.isbn.trim()}
                    className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {isLookingUp ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
                    Lookup ISBN
                  </button>
                </div>
                {isbnLookupResult?.found && (
                  <div className="flex gap-4 p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg text-sm">
                    {isbnLookupResult.cover_url && (
                      <img src={isbnLookupResult.cover_url} alt="Cover" className="w-16 h-24 object-cover rounded shadow" />
                    )}
                    <div>
                      <p><strong>Title:</strong> {isbnLookupResult.title}</p>
                      <p><strong>Author:</strong> {isbnLookupResult.author}</p>
                      <p><strong>Publisher:</strong> {isbnLookupResult.publisher}</p>
                      <p><strong>Source:</strong> {isbnLookupResult.source}</p>
                      <p className="text-status-success-700 dark:text-status-success-300 mt-1">Fields auto-filled from ISBN data</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Add Form */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6">
                <h2 className="font-serif text-lg font-semibold mb-4">Add Volume</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="quick-add-volume-number" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Volume Number</label>
                    <input
                      id="quick-add-volume-number"
                      type="number" min={0}
                      value={quickAddForm.volume_number}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, volume_number: Number(e.target.value) }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="quick-add-title" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title</label>
                    <input
                      id="quick-add-title"
                      type="text"
                      placeholder={seriesTitle ? `${seriesTitle} Vol. ${quickAddForm.volume_number}` : "Volume title"}
                      value={quickAddForm.title}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, title: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="quick-add-author" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author</label>
                    <input
                      id="quick-add-author"
                      type="text"
                      value={quickAddForm.author}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, author: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="quick-add-publisher" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publisher</label>
                    <input
                      id="quick-add-publisher"
                      type="text"
                      value={quickAddForm.publisher}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, publisher: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="quick-add-language" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Language</label>
                    <input
                      id="quick-add-language"
                      type="text"
                      value={quickAddForm.original_language}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, original_language: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="quick-add-pub-date" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publication Date</label>
                    <input
                      id="quick-add-pub-date"
                      type="text"
                      placeholder={t('placeholder.readingOrderTab.yyyymmdd')}
                      value={quickAddForm.publication_date}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, publication_date: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="quick-add-template" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Template</label>
                    <select
                      id="quick-add-template"
                      value={quickAddForm.template_id || ""}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, template_id: e.target.value ? Number(e.target.value) : undefined }))}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    >
                      <option value="">Auto-detect / None</option>
                      {templates.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2 pt-6">
                    <input
                      type="checkbox"
                      checked={quickAddForm.auto_fetch_cover}
                      onChange={e => setQuickAddForm(prev => ({ ...prev, auto_fetch_cover: e.target.checked }))}
                      className="rounded"
                      id="auto-cover"
                    />
                    <label htmlFor="auto-cover" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                      <Image className="w-4 h-4" /> Auto-fetch cover from ISBN
                    </label>
                  </div>
                </div>
                <div className="mt-6 flex gap-3">
                  <button
                    onClick={handleQuickAdd}
                    disabled={isSaving}
                    className="px-6 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
                  >
                    {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
                    Add Volume
                  </button>
                </div>
              </div>

              {/* Copy & Increment */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6">
                <h2 className="font-serif text-lg font-semibold mb-4 flex items-center gap-2">
                  <Copy className="w-5 h-5" /> Copy Previous Volume & Increment
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Clone all fields from an existing volume record and increment the volume number.
                  This is the fastest way to add sequential volumes in a series.
                </p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label htmlFor="copy-increment-source-volume-id" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Source Volume ID</label>
                    <input
                      id="copy-increment-source-volume-id"
                      type="number"
                      value={copySourceId}
                      onChange={e => setCopySourceId(e.target.value)}
                      placeholder={t('placeholder.staffMangaCataloging.eg42')}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="copy-increment-new-volume-number" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">New Volume Number</label>
                    <input
                      id="copy-increment-new-volume-number"
                      type="number"
                      value={copyNewVolNum}
                      onChange={e => setCopyNewVolNum(e.target.value)}
                      placeholder={t('placeholder.staffMangaCataloging.eg5')}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                  <div>
                    <label htmlFor="copy-increment-new-isbn" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">New ISBN (optional)</label>
                    <input
                      id="copy-increment-new-isbn"
                      type="text"
                      value={copyNewIsbn}
                      onChange={e => setCopyNewIsbn(e.target.value)}
                      placeholder={t('placeholder.issuesTab.978')}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose"
                    />
                  </div>
                </div>
                <button
                  onClick={handleCopyIncrement}
                  disabled={isCopying}
                  className="mt-4 px-4 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {isCopying ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Copy className="w-4 h-4" />}
                  Copy & Increment
                </button>
              </div>
            </div>
          )}

          {/* Templates Tab */}
          {activeTab === "templates" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="font-serif text-lg font-semibold">Manga Cataloging Templates</h2>
                <button
                  onClick={() => setShowTemplateForm(!showTemplateForm)}
                  className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 flex items-center gap-2"
                >
                  {showTemplateForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                  {showTemplateForm ? "Cancel" : "New Template"}
                </button>
              </div>

              {showTemplateForm && (
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6">
                  <h3 className="font-serif text-base font-semibold mb-4">Create Template</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="template-form-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Template Name</label>
                      <input id="template-form-name" type="text" value={templateForm.name}
                        onChange={e => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                        placeholder={t('placeholder.staffMangaCataloging.egShonenJumpStandard')}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                    <div>
                      <label htmlFor="template-form-series-title" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Series Title</label>
                      <input id="template-form-series-title" type="text" value={templateForm.series_title}
                        onChange={e => setTemplateForm(prev => ({ ...prev, series_title: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                    <div>
                      <label htmlFor="template-form-author" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author</label>
                      <input id="template-form-author" type="text" value={templateForm.author}
                        onChange={e => setTemplateForm(prev => ({ ...prev, author: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                    <div>
                      <label htmlFor="template-form-publisher" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publisher</label>
                      <input id="template-form-publisher" type="text" value={templateForm.publisher}
                        onChange={e => setTemplateForm(prev => ({ ...prev, publisher: e.target.value }))}
                        placeholder={t('placeholder.staffMangaCataloging.egVizMedia')}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                    <div>
                      <label htmlFor="template-form-genre" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Genre</label>
                      <input id="template-form-genre" type="text" value={templateForm.genre}
                        onChange={e => setTemplateForm(prev => ({ ...prev, genre: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                    <div>
                      <label htmlFor="template-form-subjects" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Subjects</label>
                      <input id="template-form-subjects" type="text" value={templateForm.subjects}
                        onChange={e => setTemplateForm(prev => ({ ...prev, subjects: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                    <div>
                      <label htmlFor="template-form-format" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Format</label>
                      <select id="template-form-format" value={templateForm.format}
                        onChange={e => setTemplateForm(prev => ({ ...prev, format: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose">
                        <option value="volume">Volume</option>
                        <option value="omnibus">Omnibus</option>
                        <option value="box_set">Box Set</option>
                        <option value="complete">Complete</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="template-form-avg-page-count" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Avg. Page Count</label>
                      <input id="template-form-avg-page-count" type="number" value={templateForm.page_count_average}
                        onChange={e => setTemplateForm(prev => ({ ...prev, page_count_average: e.target.value }))}
                        placeholder={t('placeholder.staffMangaCataloging.eg200')}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                    </div>
                  </div>
                  <div className="flex gap-4 mt-4">
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={templateForm.auto_increment_volume}
                        onChange={e => setTemplateForm(prev => ({ ...prev, auto_increment_volume: e.target.checked }))}
                        className="rounded" />
                      Auto-increment volume number
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={templateForm.auto_fetch_cover}
                        onChange={e => setTemplateForm(prev => ({ ...prev, auto_fetch_cover: e.target.checked }))}
                        className="rounded" />
                      Auto-fetch covers
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={templateForm.auto_populate_series_info}
                        onChange={e => setTemplateForm(prev => ({ ...prev, auto_populate_series_info: e.target.checked }))}
                        className="rounded" />
                      Auto-populate from previous volumes
                    </label>
                  </div>
                  <button onClick={handleCreateTemplate} disabled={isSaving}
                    className="mt-4 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2">
                    {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
                    Create Template
                  </button>
                </div>
              )}

              {/* Template List */}
              <div className="space-y-3">
                {templates.length === 0 ? (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                    No templates yet. Create one to speed up cataloging.
                  </div>
                ) : (
                  templates.map(tmpl => (
                    <div key={tmpl.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{tmpl.name}</h3>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            Series: {tmpl.series_title} | Author: {tmpl.author || "N/A"} | Publisher: {tmpl.publisher || "N/A"}
                          </p>
                          <div className="flex gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            <span>Genre: {formatGenre(tmpl.genre)}</span>
                            <span>Format: {tmpl.format}</span>
                            <span>Language: {tmpl.original_language}</span>
                            {tmpl.auto_fetch_cover && <span className="text-status-success-600">Auto-cover</span>}
                            {tmpl.auto_increment_volume && <span className="text-lsc-rose dark:text-lsc-rose-light">Auto-increment</span>}
                          </div>
                        </div>
                        <button onClick={() => handleDeleteTemplate(tmpl.id)}
                          aria-label={t('aria.deleteTemplate', 'Delete template {{name}}').replace('{{name}}', tmpl.name)}
                          className="text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300 p-1">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Batch Create Tab */}
          {activeTab === "batch" && (
            <div className="space-y-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6">
                <h2 className="font-serif text-lg font-semibold mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5" /> Batch Create Volumes
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Add multiple volumes at once for a multi-volume purchase. Template defaults and
                  auto-fetch covers will be applied to each volume.
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Series Title</label>
                  <input type="text" value={batchSeriesTitle}
                    onChange={e => setBatchSeriesTitle(e.target.value)}
                    placeholder={t('placeholder.staffMangaCataloging.egMyHeroAcademia')}
                    className="w-full max-w-md px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                </div>

                <div className="space-y-2">
                  <div className="grid grid-cols-12 gap-2 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                    <div className="col-span-2">Vol #</div>
                    <div className="col-span-5">Title</div>
                    <div className="col-span-4">ISBN</div>
                    <div className="col-span-1"></div>
                  </div>
                  {batchVolumes.map((vol, i) => (
                    <div key={i} className="grid grid-cols-12 gap-2">
                      <input id={`batch-volume-${i}`} type="number" value={vol.volume_number}
                        onChange={e => updateBatchRow(i, "volume_number", Number(e.target.value))}
                        aria-label={t('aria.staffMangaCataloging.batchVolumeRow', 'Volume number, row {{row}}').replace('{{row}}', String(i + 1))}
                        className="col-span-2 px-2 py-1 border rounded text-sm" />
                      <input id={`batch-title-${i}`} type="text" value={vol.title}
                        onChange={e => updateBatchRow(i, "title", e.target.value)}
                        placeholder={batchSeriesTitle ? `${batchSeriesTitle} Vol. ${vol.volume_number}` : "Title"}
                        aria-label={t('aria.staffMangaCataloging.batchTitleRow', 'Title, row {{row}}').replace('{{row}}', String(i + 1))}
                        className="col-span-5 px-2 py-1 border rounded text-sm" />
                      <input id={`batch-isbn-${i}`} type="text" value={vol.isbn}
                        onChange={e => updateBatchRow(i, "isbn", e.target.value)}
                        placeholder={t('placeholder.acquisition.isbn')}
                        aria-label={t('aria.staffMangaCataloging.batchIsbnRow', 'ISBN, row {{row}}').replace('{{row}}', String(i + 1))}
                        className="col-span-4 px-2 py-1 border rounded text-sm" />
                      <button onClick={() => removeBatchRow(i)}
                        aria-label={t('aria.removeRow', 'Remove row {{row}}').replace('{{row}}', String(i + 1))}
                        className="col-span-1 text-status-danger-400 hover:text-status-danger-600 flex items-center justify-center"
                        disabled={batchVolumes.length <= 1}>
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
                <div className="flex gap-3 mt-4">
                  <button onClick={addBatchRow}
                    className="px-3 py-1 text-sm border rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 flex items-center gap-1">
                    <Plus className="w-3 h-3" /> Add Row
                  </button>
                  <button onClick={handleBatchCreate} disabled={isBatchCreating}
                    className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2">
                    {isBatchCreating ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Layers className="w-4 h-4" />}
                    Create {batchVolumes.length} Volume{batchVolumes.length !== 1 ? "s" : ""}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Volumes Tab */}
          {activeTab === "volumes" && (
            <div className="space-y-4">
              <div className="flex gap-3">
                <input type="text" value={volumeSearchSeries}
                  onChange={e => setVolumeSearchSeries(e.target.value)}
                  placeholder={t('placeholder.staffMangaCataloging.filterBySeriesTitle')}
                  aria-label={t('aria.staffMangaCataloging.filterBySeriesTitle')}
                  className="flex-1 max-w-md px-3 py-2 border rounded-lg focus:ring-2 focus:ring-lsc-rose" />
                <button onClick={() => loadVolumes(volumeSearchSeries)}
                  className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 flex items-center gap-2">
                  <Search className="w-4 h-4" /> Search
                </button>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-earth-50 dark:bg-earth-900 text-left text-xs uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                    <tr>
                      <th className="px-4 py-3">ID</th>
                      <th className="px-4 py-3">Series</th>
                      <th className="px-4 py-3">Vol</th>
                      <th className="px-4 py-3">ISBN</th>
                      <th className="px-4 py-3">Publisher</th>
                      <th className="px-4 py-3">Cover</th>
                      <th className="px-4 py-3">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {volumeLoadError ? (
                      <tr><td colSpan={7} className="px-4 py-8 text-center text-red-600 dark:text-red-400">{volumeLoadError}</td></tr>
                    ) : volumes.length === 0 ? (
                      <tr><td colSpan={7} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">No volumes found</td></tr>
                    ) : (
                      volumes.map(v => (
                        <tr key={v.id} className="hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                          <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">{v.id}</td>
                          <td className="px-4 py-2 font-medium">{v.series_title}</td>
                          <td className="px-4 py-2">{v.volume_number}</td>
                          <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">{v.isbn || "-"}</td>
                          <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">{v.publisher || "-"}</td>
                          <td className="px-4 py-2">
                            {v.cover_image_url ? (
                              <img src={v.cover_image_url} alt="" className="w-8 h-12 object-cover rounded" />
                            ) : (
                              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">-</span>
                            )}
                          </td>
                          <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs">
                            {v.created_at ? new Date(v.created_at).toLocaleDateString() : '—'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Stats Tab */}
          {activeTab === "stats" && (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              {stats ? (
                <>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 text-center">
                    <p className="text-3xl font-bold text-lsc-rose">{stats.total_templates}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Templates</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 text-center">
                    <p className="text-3xl font-bold text-lsc-rose">{stats.total_volumes}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Total Volumes</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 text-center">
                    <p className="text-3xl font-bold text-lsc-rose">{stats.total_series}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Unique Series</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 text-center">
                    <p className="text-3xl font-bold text-lsc-rose">{stats.avg_volumes_per_series}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Avg Volumes/Series</p>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 text-center">
                    <p className="text-3xl font-bold text-status-success-600">{stats.templates_with_auto_cover}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Auto-Cover Templates</p>
                  </div>
                </>
              ) : (
                <div className="col-span-full bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-8 text-center">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin mx-auto mb-2 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading statistics...</p>
                </div>
              )}
            </div>
          )}
        </div>

    </AdminShell>
  )
}
