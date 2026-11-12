/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import ConfirmDialog from '@/components/ConfirmDialog'
import { useState, useEffect, FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  MessageSquare, Pin, Send, Plus, Search, Filter,
  Trash2, Edit3, ArrowLeft, Clock, User, Archive,
  FileText, Building2, MapPin, Coffee, Lightbulb, GraduationCap,
  ChevronLeft, ChevronRight,
} from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import { useAuth } from '../contexts/AuthContext'
import {
  listPosts, getPost, createPost, updatePost, deletePost,
  createReply, deleteReply, getCategories,
  type BoardPost, type BoardPostDetail, type BoardReply, type CategoryOption,
} from '../api/staff-message-board-api'
import { useTranslation, getCurrentLocale } from '@/i18n'

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  memo: <FileText className="w-4 h-4" />,
  library_happenings: <Building2 className="w-4 h-4" />,
  state_news: <MapPin className="w-4 h-4" />,
  general: <Coffee className="w-4 h-4" />,
  tips_tricks: <Lightbulb className="w-4 h-4" />,
  professional_dev: <GraduationCap className="w-4 h-4" />,
}

const CATEGORY_COLORS: Record<string, string> = {
  memo: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  library_happenings: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  state_news: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300',
  general: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  tips_tricks: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  professional_dev: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light',
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined })
}

export default function StaffMessageBoardPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const isAdmin = user && ['admin', 'super_admin'].includes(user.role)
  const { postId } = useParams()
  const navigate = useNavigate()

  // List state
  const [posts, setPosts] = useState<BoardPost[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [categories, setCategories] = useState<CategoryOption[]>([])

  // Detail state
  const [selectedPost, setSelectedPost] = useState<BoardPostDetail | null>(null)

  // Create/edit state
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingPost, setEditingPost] = useState<BoardPostDetail | null>(null)
  const [formTitle, setFormTitle] = useState('')
  const [formContent, setFormContent] = useState('')
  const [formCategory, setFormCategory] = useState('general')
  const [formPinned, setFormPinned] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Reply state
  const [replyContent, setReplyContent] = useState('')
  const [replySubmitting, setReplySubmitting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmTitle, setConfirmTitle] = useState('')
  const [confirmMessage, setConfirmMessage] = useState('')
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {})
  }, [])

  const fetchPosts = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listPosts(page, 20, categoryFilter || undefined, false, false, searchQuery || undefined)
      setPosts(data.posts)
      setTotal(data.total)
      setPages(data.pages)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load posts')
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    fetchPosts()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, categoryFilter, searchQuery])

  const openPost = async (postId: number) => {
    try {
      const data = await getPost(postId)
      setSelectedPost(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load post')
    }
  }


  // Deep link: /staff/message-board/:postId opens that post directly
  useEffect(() => {
    if (postId) openPost(Number(postId))

  }, [postId])

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    setPage(1)
    setSearchQuery(searchInput)
  }

  const openCreateForm = () => {
    setEditingPost(null)
    setFormTitle('')
    setFormContent('')
    setFormCategory('general')
    setFormPinned(false)
    setShowCreateForm(true)
  }

  const openEditForm = (post: BoardPostDetail) => {
    setEditingPost(post)
    setFormTitle(post.title)
    setFormContent(post.content)
    setFormCategory(post.category)
    setFormPinned(post.pinned)
    setShowCreateForm(true)
  }

  const handleSubmitPost = async (e: FormEvent) => {
    e.preventDefault()
    if (!formTitle.trim() || !formContent.trim()) return
    try {
      setSubmitting(true)
      if (editingPost) {
        const updated = await updatePost(editingPost.id, {
          title: formTitle,
          content: formContent,
          category: formCategory,
          pinned: formPinned,
        })
        setSelectedPost(updated)
      } else {
        await createPost({
          title: formTitle,
          content: formContent,
          category: formCategory,
          pinned: formPinned,
        })
      }
      setShowCreateForm(false)
      setEditingPost(null)
      fetchPosts()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save post')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeletePost = (postId: number) => {
    setConfirmTitle('Delete this post?')
    setConfirmMessage('Are you sure you want to delete this post? This cannot be undone.')
    setPendingAction(() => async () => {
      try {
        await deletePost(postId)
        setSelectedPost(null)
        fetchPosts()
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to delete post')
      }
    })
    setConfirmOpen(true)
  }

  const handleTogglePin = async (post: BoardPostDetail) => {
    try {
      const updated = await updatePost(post.id, { pinned: !post.pinned })
      setSelectedPost(updated)
      fetchPosts()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update pin status')
    }
  }

  const handleArchivePost = async (post: BoardPostDetail) => {
    try {
      const updated = await updatePost(post.id, { archived: !post.archived })
      setSelectedPost(updated)
      fetchPosts()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to archive post')
    }
  }

  const handleSubmitReply = async (e: FormEvent) => {
    e.preventDefault()
    if (!replyContent.trim() || !selectedPost) return
    try {
      setReplySubmitting(true)
      const reply = await createReply(selectedPost.id, replyContent)
      setSelectedPost({
        ...selectedPost,
        replies: [...selectedPost.replies, reply],
        reply_count: selectedPost.reply_count + 1,
      })
      setReplyContent('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to post reply')
    } finally {
      setReplySubmitting(false)
    }
  }

  const handleDeleteReply = (replyId: number) => {
    if (!selectedPost) return
    setConfirmTitle('Delete this reply?')
    setConfirmMessage('Are you sure you want to delete this reply?')
    const post = selectedPost
    setPendingAction(() => async () => {
      try {
        await deleteReply(post.id, replyId)
        setSelectedPost({
          ...post,
          replies: post.replies.filter(r => r.id !== replyId),
          reply_count: post.reply_count - 1,
        })
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to delete reply')
      }
    })
    setConfirmOpen(true)
  }

  const canEditPost = (post: BoardPost | BoardPostDetail) => {
    return isAdmin || (user && post.author?.id === user.id)
  }

  const getCategoryLabel = (value: string) => {
    return categories.find(c => c.value === value)?.label || value
  }

  // ---- RENDER ----

  return (
    <AdminShell title="Staff Message Board">
        <div className="mb-6">
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
            <Coffee className="w-8 h-8 text-status-warning-600" />
            Staff Message Board
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            Your virtual break room — share memos, library happenings, state news, and connect with colleagues.
          </p>
        </div>

        <div className="space-y-6">
            {error && (
              <div role="alert" className="bg-status-danger-50 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 p-3 rounded-lg text-sm">
                {error}
                <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
              </div>
            )}

            {/* Create / Edit Form */}
            {showCreateForm && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  {editingPost ? 'Edit Post' : 'New Post'}
                </h2>
                <form onSubmit={handleSubmitPost} className="space-y-4">
                  <div>
                    <label htmlFor="message-board-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Title</label>
                    <input
                      id="message-board-title"
                      type="text"
                      value={formTitle}
                      onChange={e => setFormTitle(e.target.value)}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      placeholder={t('placeholder.staffMessageBoard.postTitle')}
                      required
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="message-board-category" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Category</label>
                      <select
                        id="message-board-category"
                        value={formCategory}
                        onChange={e => setFormCategory(e.target.value)}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
                      >
                        {categories.map(c => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                    </div>
                    {isAdmin && (
                      <div className="flex items-end">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formPinned}
                            onChange={e => setFormPinned(e.target.checked)}
                            className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                          />
                          <Pin className="w-4 h-4 text-status-warning-600" />
                          <span className="text-sm text-lsc-dark dark:text-lsc-cream">Pin to top</span>
                        </label>
                      </div>
                    )}
                  </div>
                  <div>
                    <label htmlFor="message-board-content" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Content</label>
                    <textarea
                      id="message-board-content"
                      value={formContent}
                      onChange={e => setFormContent(e.target.value)}
                      rows={6}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      placeholder={t('staffMessageBoard.shareSomethingWithYourColleagues')}
                      required
                    />
                  </div>
                  <div className="flex gap-3">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      {submitting ? 'Posting...' : editingPost ? 'Save Changes' : 'Post'}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowCreateForm(false); setEditingPost(null) }}
                      className="px-4 py-2 border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Post Detail View */}
            {selectedPost && !showCreateForm && (
              <div className="space-y-4">
                <button
                  onClick={() => { setSelectedPost(null); if (postId) navigate('/staff/message-board') }}
                  className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  <ArrowLeft className="w-4 h-4" /> Back to all posts
                </button>

                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        {selectedPost.pinned && <Pin className="w-4 h-4 text-status-warning-600" />}
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[selectedPost.category] || CATEGORY_COLORS.general}`}>
                          {CATEGORY_ICONS[selectedPost.category]}
                          {getCategoryLabel(selectedPost.category)}
                        </span>
                      </div>
                      <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{selectedPost.title}</h2>
                      <div className="flex items-center gap-3 mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                        <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" /> {selectedPost.author?.full_name || 'Staff'}</span>
                        <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {formatDate(selectedPost.created_at)}</span>
                      </div>
                    </div>
                    {canEditPost(selectedPost) && (
                      <div className="flex items-center gap-1">
                        {isAdmin && (
                          <>
                            <button onClick={() => handleTogglePin(selectedPost)} title={selectedPost.pinned ? 'Unpin' : 'Pin'} className="p-1.5 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/60" aria-label={selectedPost.pinned ? 'Unpin post' : 'Pin post'}>
                              <Pin className={`w-4 h-4 ${selectedPost.pinned ? 'text-status-warning-600' : ''}`} />
                            </button>
                            <button onClick={() => handleArchivePost(selectedPost)} title={selectedPost.archived ? 'Unarchive' : 'Archive'} className="p-1.5 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/60" aria-label={selectedPost.archived ? 'Unarchive post' : 'Archive post'}>
                              <Archive className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        <button onClick={() => openEditForm(selectedPost)} className="p-1.5 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/60" aria-label={t('aria.staffMessageBoard.editPost')}>
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDeletePost(selectedPost.id)} className="p-1.5 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/30 text-status-danger-500" aria-label={t('aria.staffMessageBoard.deletePost')}>
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="prose dark:prose-invert max-w-none text-lsc-dark dark:text-lsc-cream/90 whitespace-pre-wrap">
                    {selectedPost.content}
                  </div>
                </div>

                {/* Replies */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <MessageSquare className="w-5 h-5" />
                    Replies ({selectedPost.replies.length})
                  </h3>

                  {selectedPost.replies.length === 0 && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50 italic mb-4">{t('staffMessageBoard.noRepliesYetBeThe')}</p>
                  )}

                  <div className="space-y-4 mb-6">
                    {selectedPost.replies.map((reply: BoardReply) => (
                      <div key={reply.id} className="border-l-2 border-lsc-border dark:border-earth-600 pl-4 py-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                            <User className="w-3.5 h-3.5" />
                            <span className="font-medium">{reply.author?.full_name || 'Staff'}</span>
                            <span>&middot;</span>
                            <span>{formatDate(reply.created_at)}</span>
                          </div>
                          {(isAdmin || (user && reply.author?.id === user.id)) && (
                            <button onClick={() => handleDeleteReply(reply.id)} className="p-1 rounded hover:bg-status-danger-50 dark:hover:bg-status-danger-900/30 text-status-danger-400" aria-label={t('aria.staffMessageBoard.deleteReply')}>
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                        <p className="text-lsc-dark dark:text-lsc-cream/90 mt-1 whitespace-pre-wrap">{reply.content}</p>
                      </div>
                    ))}
                  </div>

                  {/* Reply form */}
                  <form onSubmit={handleSubmitReply} className="flex gap-3">
                    <input
                      type="text"
                      value={replyContent}
                      onChange={e => setReplyContent(e.target.value)}
                      placeholder={t('placeholder.strategicComments.writeAReply')}
                      className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                    <button
                      type="submit"
                      disabled={replySubmitting || !replyContent.trim()}
                      className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      {replySubmitting ? '...' : 'Reply'}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* Post List View */}
            {!selectedPost && !showCreateForm && (
              <>
                {/* Toolbar */}
                <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
                  <div className="flex gap-3 items-center flex-wrap">
                    <button
                      onClick={openCreateForm}
                      className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 flex items-center gap-2 font-medium"
                    >
                      <Plus className="w-4 h-4" /> New Post
                    </button>
                    <div className="flex items-center gap-1">
                      <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                      <select
                        value={categoryFilter}
                        onChange={e => { setCategoryFilter(e.target.value); setPage(1) }}
                        aria-label={t('aria.staffMessageBoard.filterByCategory', 'Filter by category')}
                        className="text-sm px-2 py-1.5 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      >
                        <option value="">All Categories</option>
                        {categories.map(c => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <form onSubmit={handleSearch} className="flex gap-2">
                    <div className="relative">
                      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/60" />
                      <input
                        type="text"
                        value={searchInput}
                        onChange={e => setSearchInput(e.target.value)}
                        placeholder={t('placeholder.staffMessageBoard.searchPosts')}
                        className="pl-9 pr-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      />
                    </div>
                    <button type="submit" className="px-3 py-1.5 text-sm bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600">
                      Search
                    </button>
                  </form>
                </div>

                {/* Posts */}
                {loading ? (
                  <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/50">Loading posts...</div>
                ) : posts.length === 0 ? (
                  <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                    <Coffee className="w-12 h-12 mx-auto mb-3 text-lsc-dark/30 dark:text-lsc-cream/60" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/60 mb-2">No posts yet</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{t('staffMessageBoard.startTheConversationByCreating')}</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {posts.map(post => (
                      <button
                        key={post.id}
                        onClick={() => openPost(post.id)}
                        className="w-full text-left bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4 hover:border-lsc-rose/50 dark:hover:border-lsc-rose/50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {post.pinned && <Pin className="w-3.5 h-3.5 text-status-warning-600 flex-shrink-0" />}
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[post.category] || CATEGORY_COLORS.general}`}>
                                {CATEGORY_ICONS[post.category]}
                                {getCategoryLabel(post.category)}
                              </span>
                            </div>
                            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={post.title}>{post.title}</h3>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1 line-clamp-2" title={post.content}>{post.content}</p>
                            <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                              <span className="flex items-center gap-1"><User className="w-3 h-3" /> {post.author?.full_name || 'Staff'}</span>
                              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {formatDate(post.created_at)}</span>
                              <span className="flex items-center gap-1"><MessageSquare className="w-3 h-3" /> {post.reply_count} {post.reply_count === 1 ? 'reply' : 'replies'}</span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {pages > 1 && (
                  <div className="flex items-center justify-center gap-4 pt-4">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded-lg disabled:opacity-40 hover:bg-earth-100 dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream flex items-center gap-1"
                    >
                      <ChevronLeft className="w-4 h-4" /> Previous
                    </button>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                      Page {page} of {pages} ({total} posts)
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(pages, p + 1))}
                      disabled={page >= pages}
                      className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded-lg disabled:opacity-40 hover:bg-earth-100 dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream flex items-center gap-1"
                    >
                      Next <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </>
            )}
        </div>

      <ConfirmDialog
        isOpen={confirmOpen}
        title={confirmTitle}
        message={confirmMessage}
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </AdminShell>
  )
}
