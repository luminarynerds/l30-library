/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listComicSeries, createComicSeries, getComicSeries, listComicIssues, quickAddComicIssue } from '@/api/comic-cataloging-api'
import type { ComicSeriesCreate } from '@/api/comic-cataloging-api'
import { AdminShell } from '../components/shells/AdminShell'
import { BookOpen, Plus, Loader2, X, Library, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { t } from '@/i18n'

const FORMATS = ['single_issue', 'trade_paperback', 'hardcover', 'omnibus', 'graphic_novel', 'annual', 'limited_series', 'one_shot']

export default function StaffComicCatalogingPage(): React.ReactElement {
  const queryClient = useQueryClient()
  const [selectedSeriesId, setSelectedSeriesId] = useState<number | null>(null)
  const [showAddSeries, setShowAddSeries] = useState(false)
  const [showAddIssue, setShowAddIssue] = useState(false)
  const [seriesForm, setSeriesForm] = useState<ComicSeriesCreate>({ title: '', publisher: '', comic_format: 'single_issue', is_ongoing: true, genres: [], characters: [] })
  const [issueForm, setIssueForm] = useState({ issue_number: '', catalog_item_id: '', issue_title: '', page_count: '' })
  const [genresInput, setGenresInput] = useState('')
  const [charsInput, setCharsInput] = useState('')

  const { data: seriesList, isLoading } = useQuery({
    queryKey: ['comic-series'],
    queryFn: () => listComicSeries(undefined, 0, 100),
  })

  const { data: seriesDetail } = useQuery({
    queryKey: ['comic-series', selectedSeriesId],
    queryFn: () => getComicSeries(selectedSeriesId!),
    enabled: !!selectedSeriesId,
  })

  const { data: issues } = useQuery({
    queryKey: ['comic-issues', selectedSeriesId],
    queryFn: () => listComicIssues(selectedSeriesId!, 0, 100),
    enabled: !!selectedSeriesId,
  })

  const createSeriesMut = useMutation({
    mutationFn: (data: ComicSeriesCreate) => createComicSeries(data),
    onSuccess: () => { toast.success('Series created'); setShowAddSeries(false); queryClient.invalidateQueries({ queryKey: ['comic-series'] }) },
    onError: () => toast.error('Failed to create series'),
  })

  const addIssueMut = useMutation({
    mutationFn: (data: { series_id: number; issue_number: string; catalog_item_id: number; issue_title?: string; page_count?: number }) => quickAddComicIssue(data),
    onSuccess: () => { toast.success('Issue added'); setShowAddIssue(false); queryClient.invalidateQueries({ queryKey: ['comic-issues', selectedSeriesId] }) },
    onError: () => toast.error('Failed to add issue'),
  })

  const handleCreateSeries = (e: React.FormEvent) => {
    e.preventDefault()
    createSeriesMut.mutate({
      ...seriesForm,
      genres: genresInput ? genresInput.split(',').map(s => s.trim()) : [],
      characters: charsInput ? charsInput.split(',').map(s => s.trim()) : [],
    })
  }

  const handleAddIssue = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSeriesId) return
    addIssueMut.mutate({
      series_id: selectedSeriesId,
      issue_number: issueForm.issue_number,
      catalog_item_id: Number(issueForm.catalog_item_id),
      ...(issueForm.issue_title ? { issue_title: issueForm.issue_title } : {}),
      ...(issueForm.page_count ? { page_count: Number(issueForm.page_count) } : {}),
    })
  }

  const inputCls = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
  const labelCls = "block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"

  return (
    <AdminShell title="Comic Cataloging">
      <div>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl"><Library className="w-6 h-6 text-lsc-rose" /></div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Comic Cataloging</h1>
          </div>
          <button onClick={() => { setSeriesForm({ title: '', publisher: '', comic_format: 'single_issue', is_ongoing: true, genres: [], characters: [] }); setGenresInput(''); setCharsInput(''); setShowAddSeries(true) }} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm">
            <Plus className="w-4 h-4" /> Add Series
          </button>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Series List */}
          <div className="lg:col-span-1">
            <h2 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wider mb-3">Series ({seriesList?.length || 0})</h2>
            {isLoading ? (
              <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
            ) : !seriesList?.length ? (
              <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                <BookOpen className="w-10 h-10 mx-auto mb-2 opacity-50" /><p className="text-sm">No series yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {seriesList.map(s => (
                  <button key={s.id} onClick={() => setSelectedSeriesId(s.id)} className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedSeriesId === s.id ? 'bg-lsc-rose/10 border-lsc-rose dark:bg-lsc-rose/20' : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{s.title}</h3>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{s.publisher} &middot; {s.comic_format.replace('_', ' ')}</p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/30" />
                    </div>
                    <div className="flex gap-2 mt-1">
                      {s.is_ongoing && <span className="text-xs px-1.5 py-0.5 rounded bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400">Ongoing</span>}
                      {s.total_issues_published && <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{s.total_issues_published} issues</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Series Detail + Issues */}
          <div className="lg:col-span-2">
            {!selectedSeriesId ? (
              <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                <Library className="w-16 h-16 mx-auto mb-3 opacity-30" /><p>Select a series to view details</p>
              </div>
            ) : (
              <div>
                {seriesDetail && (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 mb-4">
                    <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{seriesDetail.title}</h2>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">{seriesDetail.publisher} {seriesDetail.publisher_imprint ? `/ ${seriesDetail.publisher_imprint}` : ''}</p>
                    {seriesDetail.description && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{seriesDetail.description}</p>}
                    <div className="flex flex-wrap gap-2 mt-3">
                      <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs">{seriesDetail.comic_format.replace('_', ' ')}</span>
                      {seriesDetail.is_ongoing && <span className="px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 rounded text-xs text-status-success-800 dark:text-status-success-400">Ongoing</span>}
                      {seriesDetail.first_publication_year && <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{seriesDetail.first_publication_year}{seriesDetail.last_publication_year ? ` - ${seriesDetail.last_publication_year}` : ' - present'}</span>}
                    </div>
                    {seriesDetail.genres?.length ? <div className="flex gap-1 mt-2">{seriesDetail.genres.map(g => <span key={g} className="px-2 py-0.5 bg-category-100 dark:bg-category-900/30 rounded text-xs text-category-800 dark:text-category-300">{g}</span>)}</div> : null}
                  </div>
                )}

                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Issues ({issues?.length || 0})</h3>
                  <button onClick={() => { setIssueForm({ issue_number: '', catalog_item_id: '', issue_title: '', page_count: '' }); setShowAddIssue(true) }} className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90">
                    <Plus className="w-3.5 h-3.5" /> Quick Add Issue
                  </button>
                </div>

                {issues && issues.length > 0 ? (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 divide-y divide-lsc-border dark:divide-earth-700">
                    {issues.map(issue => (
                      <div key={issue.id} className="px-4 py-3 flex items-center justify-between">
                        <div>
                          <span className="font-mono text-sm font-medium text-lsc-dark dark:text-lsc-cream">#{issue.issue_number}</span>
                          {issue.issue_title && <span className="ml-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{issue.issue_title}</span>}
                        </div>
                        <div className="flex gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          {issue.writers?.length ? <span>W: {issue.writers.join(', ')}</span> : null}
                          {issue.artists?.length ? <span>A: {issue.artists.join(', ')}</span> : null}
                          {issue.page_count && <span>{issue.page_count}p</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">No issues cataloged yet</div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Add Series Modal */}
        {showAddSeries && (
          <ModalBackdrop onClose={() => setShowAddSeries(false)} title="Add Comic Series">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Add Comic Series</h3>
                <button onClick={() => setShowAddSeries(false)} aria-label={t('aria.comicCataloging.close', 'Close')}><X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /></button>
              </div>
              <form onSubmit={handleCreateSeries} className="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
                <div><label className={labelCls} htmlFor="comic-series-title">Title *</label><input id="comic-series-title" type="text" required value={seriesForm.title} onChange={e => setSeriesForm({...seriesForm, title: e.target.value})} className={inputCls} /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className={labelCls} htmlFor="comic-series-publisher">Publisher *</label><input id="comic-series-publisher" type="text" required value={seriesForm.publisher} onChange={e => setSeriesForm({...seriesForm, publisher: e.target.value})} className={inputCls} /></div>
                  <div><label className={labelCls} htmlFor="comic-series-format">Format</label><select id="comic-series-format" value={seriesForm.comic_format} onChange={e => setSeriesForm({...seriesForm, comic_format: e.target.value})} className={inputCls}>{FORMATS.map(f => <option key={f} value={f}>{f.replace('_', ' ')}</option>)}</select></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className={labelCls} htmlFor="comic-series-first-year">First Year</label><input id="comic-series-first-year" type="number" value={seriesForm.first_publication_year || ''} onChange={e => { const v = Number(e.target.value); setSeriesForm(v ? {...seriesForm, first_publication_year: v} : (() => { const rest = Object.fromEntries(Object.entries(seriesForm).filter(([k]) => k !== 'first_publication_year')); return rest as ComicSeriesCreate; })()) }} className={inputCls} /></div>
                  <div className="flex items-end"><label className="flex items-center gap-2 pb-2"><input type="checkbox" checked={seriesForm.is_ongoing} onChange={e => setSeriesForm({...seriesForm, is_ongoing: e.target.checked})} className="rounded" /><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Ongoing</span></label></div>
                </div>
                <div><label className={labelCls} htmlFor="comic-series-genres">Genres (comma-separated)</label><input id="comic-series-genres" type="text" value={genresInput} onChange={e => setGenresInput(e.target.value)} className={inputCls} placeholder="superhero, drama, sci-fi" /></div>
                <div><label className={labelCls} htmlFor="comic-series-characters">Characters (comma-separated)</label><input id="comic-series-characters" type="text" value={charsInput} onChange={e => setCharsInput(e.target.value)} className={inputCls} placeholder="Batman, Joker" /></div>
                <div><label className={labelCls} htmlFor="comic-series-description">Description</label><textarea id="comic-series-description" value={seriesForm.description || ''} onChange={e => setSeriesForm({...seriesForm, description: e.target.value})} rows={2} className={inputCls} /></div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => setShowAddSeries(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                  <button type="submit" disabled={createSeriesMut.isPending} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">{createSeriesMut.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Create'}</button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}

        {/* Quick Add Issue Modal */}
        {showAddIssue && (
          <ModalBackdrop onClose={() => setShowAddIssue(false)} title="Quick Add Issue">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Quick Add Issue</h3>
                <button onClick={() => setShowAddIssue(false)} aria-label={t('aria.comicCataloging.close', 'Close')}><X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /></button>
              </div>
              <form onSubmit={handleAddIssue} className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className={labelCls} htmlFor="comic-issue-number">Issue # *</label><input id="comic-issue-number" type="text" required value={issueForm.issue_number} onChange={e => setIssueForm({...issueForm, issue_number: e.target.value})} className={inputCls} placeholder="1" /></div>
                  <div><label className={labelCls} htmlFor="comic-issue-catalog-id">Catalog Item ID *</label><input id="comic-issue-catalog-id" type="number" required value={issueForm.catalog_item_id} onChange={e => setIssueForm({...issueForm, catalog_item_id: e.target.value})} className={inputCls} /></div>
                </div>
                <div><label className={labelCls} htmlFor="comic-issue-title">Issue Title</label><input id="comic-issue-title" type="text" value={issueForm.issue_title} onChange={e => setIssueForm({...issueForm, issue_title: e.target.value})} className={inputCls} /></div>
                <div><label className={labelCls} htmlFor="comic-issue-page-count">Page Count</label><input id="comic-issue-page-count" type="number" value={issueForm.page_count} onChange={e => setIssueForm({...issueForm, page_count: e.target.value})} className={inputCls} /></div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => setShowAddIssue(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                  <button type="submit" disabled={addIssueMut.isPending} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">{addIssueMut.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Add'}</button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </AdminShell>
  )
}
