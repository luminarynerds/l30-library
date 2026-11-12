/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Tag,
  Search,
  RefreshCw,
  Loader2,
  Plus,
  Edit2,
  Trash2,
  Globe,
  Code,
  FileText,
  Image,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells/AdminShell'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import ConfirmDialog from '../components/ConfirmDialog'
import { useTranslation } from '@/i18n'
import {
  FormModal,
  TextField,
  SelectField,
  StatusBadge,
} from '@/components/admin'

interface MetaTag {
  id: number
  page_path: string
  page_name: string
  title?: string
  description?: string
  keywords?: string
  og_title?: string
  og_description?: string
  og_image?: string
  twitter_card?: string
  canonical_url?: string
  robots?: string
  is_active: boolean
  created_at: string
  updated_at?: string
}

interface MetaTagFormData {
  page_path: string
  page_name: string
  title: string
  description: string
  keywords: string
  og_title: string
  og_description: string
  og_image: string
  twitter_card: string
  canonical_url: string
  robots: string
}

const EMPTY_FORM: MetaTagFormData = {
  page_path: '',
  page_name: '',
  title: '',
  description: '',
  keywords: '',
  og_title: '',
  og_description: '',
  og_image: '',
  twitter_card: 'summary_large_image',
  canonical_url: '',
  robots: 'index, follow',
}

const TWITTER_CARD_OPTIONS = [
  { value: 'summary', label: 'Summary' },
  { value: 'summary_large_image', label: 'Summary Large Image' },
  { value: 'app', label: 'App' },
  { value: 'player', label: 'Player' },
] as const

const ROBOTS_OPTIONS = [
  { value: 'index, follow', label: 'index, follow' },
  { value: 'noindex, follow', label: 'noindex, follow' },
  { value: 'index, nofollow', label: 'index, nofollow' },
  { value: 'noindex, nofollow', label: 'noindex, nofollow' },
] as const

export default function AdminMetaTagsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()
  const { authLoading, isAuthorized } = useRequireRole('systemAdmin')
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [metaTags, setMetaTags] = useState<MetaTag[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingTag, setEditingTag] = useState<MetaTag | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [formData, setFormData] = useState<MetaTagFormData>(EMPTY_FORM)

  useEffect(() => {
    if (!authLoading && !isAuthorized) {
      toast.error(t('toast.adminAPIStatus.adminAccessRequired'))
      navigate('/account')
    }
  }, [authLoading, isAuthorized, navigate, t])

  const fetchMetaTags = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.get<{ tags?: MetaTag[] }>(`${API_BASE}/meta-tags`)
      setMetaTags(data.tags || [])
    } catch (_error: unknown) {
      toast.error(t('admin.adminMetaTags.failedToLoadMetaTags'))
    } finally {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchMetaTags()
    }
  }, [isAuthenticated, fetchMetaTags])

  const handleOpenCreate = () => {
    setEditingTag(null)
    setFormData(EMPTY_FORM)
    setShowEditModal(true)
  }

  const handleOpenEdit = (tag: MetaTag) => {
    setEditingTag(tag)
    setFormData({
      page_path: tag.page_path,
      page_name: tag.page_name,
      title: tag.title || '',
      description: tag.description || '',
      keywords: tag.keywords || '',
      og_title: tag.og_title || '',
      og_description: tag.og_description || '',
      og_image: tag.og_image || '',
      twitter_card: tag.twitter_card || 'summary_large_image',
      canonical_url: tag.canonical_url || '',
      robots: tag.robots || 'index, follow',
    })
    setShowEditModal(true)
  }

  const handleSave = async () => {
    if (!formData.page_path || !formData.page_name) {
      toast.error(t('admin.adminMetaTags.pathAndNameAreRequired'))
      return
    }
    setIsSaving(true)
    try {
      if (editingTag) {
        await api.put(`${API_BASE}/meta-tags/${editingTag.id}`, formData)
        toast.success(t('toast.adminMetaTags.metaTagUpdated'))
      } else {
        await api.post(`${API_BASE}/meta-tags`, formData)
        toast.success(t('toast.adminMetaTags.metaTagCreated'))
      }
      setShowEditModal(false)
      fetchMetaTags()
    } catch (_error: unknown) {
      toast.error(t('admin.adminMetaTags.failedToSaveMetaTag'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (tagId: number) => {
    setIsDeleting(true)
    try {
      await api.delete(`${API_BASE}/meta-tags/${tagId}`)
      toast.success(t('toast.adminMetaTags.metaTagDeleted'))
      fetchMetaTags()
    } catch (_error: unknown) {
      toast.error(t('admin.adminMetaTags.failedToDeleteMetaTag'))
    } finally {
      setIsDeleting(false)
      setDeleteConfirm(null)
    }
  }

  const filteredTags = metaTags.filter(
    (tag) =>
      tag.page_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tag.page_path.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
      </div>
    )
  }

  if (!isAuthorized) {
    return <></>
  }

  return (
    <AdminShell title={t('admin.adminMetaTags.metaTagsSeoSettings')}>
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Meta Tags / SEO Settings
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Manage page meta tags for search engine optimization
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={fetchMetaTags}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
              Refresh
            </button>
            <button
              type="button"
              onClick={handleOpenCreate}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              Add Meta Tag
            </button>
          </div>
        </div>

        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('admin.adminMetaTags.searchByPageNameOr')}
            aria-label={t('admin.adminMetaTags.searchByPageNameOr2')}
            className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2
                className="w-8 h-8 motion-safe:animate-spin text-lsc-rose"
                aria-hidden="true"
              />
            </div>
          ) : filteredTags.length === 0 ? (
            <div className="p-8 text-center">
              <Tag
                className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4"
                aria-hidden="true"
              />
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                No Meta Tags Found
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {searchQuery
                  ? 'No meta tags match your search.'
                  : 'Start by adding your first meta tag.'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-lsc-border dark:divide-earth-700">
              {filteredTags.map((tag) => (
                <div key={tag.id} className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Globe
                          className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70"
                          aria-hidden="true"
                        />
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {tag.page_name}
                        </span>
                        <StatusBadge
                          label={tag.is_active ? 'Active' : 'Inactive'}
                          tone={tag.is_active ? 'success' : 'muted'}
                          size="sm"
                        />
                      </div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                        {tag.page_path}
                      </p>
                      {tag.title && (
                        <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                          <span className="font-medium">Title:</span> {tag.title}
                        </p>
                      )}
                      {tag.description && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2">
                          <span className="font-medium">Description:</span> {tag.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(tag)}
                        aria-label="Edit"
                        title="Edit"
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                      >
                        <Edit2 className="w-4 h-4" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteConfirm(tag.id)}
                        aria-label="Delete"
                        title="Delete"
                        className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <FormModal
          open={showEditModal}
          title={editingTag ? 'Edit Meta Tag' : 'Add Meta Tag'}
          onClose={() => setShowEditModal(false)}
          onSave={handleSave}
          saving={isSaving}
          saveLabel={editingTag ? 'Update' : 'Create'}
          size="lg"
        >
          <div className="space-y-4">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <FileText className="w-4 h-4" aria-hidden="true" />
              Basic Information
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <TextField
                label="Page Path *"
                value={formData.page_path}
                onChange={(v) => setFormData({ ...formData, page_path: v })}
                placeholder={t('placeholder.adminMetaTags.catalog')}
              />
              <TextField
                label="Page Name *"
                value={formData.page_name}
                onChange={(v) => setFormData({ ...formData, page_name: v })}
                placeholder={t('placeholder.adminMetaTags.catalog1')}
              />
            </div>
            <TextField
              label="Title"
              value={formData.title}
              onChange={(v) => setFormData({ ...formData, title: v })}
              placeholder={t('admin.adminMetaTags.pageTitleLibraryName')}
            />
            <div>
              <label htmlFor="meta-tag-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Description
              </label>
              <textarea
                id="meta-tag-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                placeholder={t('admin.adminMetaTags.aBriefDescriptionOfThis')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <TextField
              label="Keywords"
              value={formData.keywords}
              onChange={(v) => setFormData({ ...formData, keywords: v })}
              placeholder={t('placeholder.adminMetaTags.libraryBooksCatalog')}
            />
          </div>

          <div className="space-y-4 pt-4 border-t border-lsc-border dark:border-earth-700">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Image className="w-4 h-4" aria-hidden="true" />
              Open Graph (Social Media)
            </h4>
            <TextField
              label="OG Title"
              value={formData.og_title}
              onChange={(v) => setFormData({ ...formData, og_title: v })}
              placeholder={t('admin.adminMetaTags.titleForSocialMediaShares')}
            />
            <div>
              <label htmlFor="meta-tag-og-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                OG Description
              </label>
              <textarea
                id="meta-tag-og-description"
                value={formData.og_description}
                onChange={(e) => setFormData({ ...formData, og_description: e.target.value })}
                rows={2}
                placeholder={t('admin.adminMetaTags.descriptionForSocialMediaShares')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <TextField
              label="OG Image URL"
              type="url"
              value={formData.og_image}
              onChange={(v) => setFormData({ ...formData, og_image: v })}
              placeholder={t('placeholder.indie.httpsexamplecomimagejpg')}
            />
            <SelectField
              label="Twitter Card Type"
              value={formData.twitter_card}
              onChange={(v) => setFormData({ ...formData, twitter_card: v })}
              options={TWITTER_CARD_OPTIONS}
            />
          </div>

          <div className="space-y-4 pt-4 border-t border-lsc-border dark:border-earth-700">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Code className="w-4 h-4" aria-hidden="true" />
              Advanced Settings
            </h4>
            <TextField
              label="Canonical URL"
              type="url"
              value={formData.canonical_url}
              onChange={(v) => setFormData({ ...formData, canonical_url: v })}
              placeholder={t('placeholder.adminMetaTags.httpsexamplecompage')}
            />
            <SelectField
              label="Robots Directive"
              value={formData.robots}
              onChange={(v) => setFormData({ ...formData, robots: v })}
              options={ROBOTS_OPTIONS}
            />
          </div>
        </FormModal>

        <ConfirmDialog
          isOpen={deleteConfirm !== null}
          title={t('admin.adminMetaTags.deleteThisMetaTag')}
          message="This will permanently remove this meta tag configuration. This action cannot be undone."
          confirmText="Yes, delete it"
          cancelText="Keep it"
          confirmVariant="danger"
          onConfirm={() => {
            if (deleteConfirm !== null) handleDelete(deleteConfirm)
          }}
          onCancel={() => setDeleteConfirm(null)}
          loading={isDeleting}
        />
      </div>
    </AdminShell>
  )
}
