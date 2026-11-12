/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
import { FormEvent, KeyboardEvent, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Heart, Sparkles, Send, Trophy, MessageSquareHeart, BookHeart, SmilePlus, Star, Shield, Megaphone, CheckCircle, XCircle } from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import {
  createPositivityEntry,
  listPositivityEntries,
  getPositivityDigest,
  deletePositivityEntry,
  toggleAdvocacyFlag,
  getAdvocacyEntries,
  getModerationQueue,
  moderateEntry,
  type PositivityEntry,
  type PositivityDigest,
  type AdvocacyEntriesResponse,
} from '../api/staff-positivity-api'
import { useTranslation} from '@/i18n'

type PositivityEntryType = 'feedback' | 'win' | 'program' | 'thank-you' | 'compliment' | 'story' | 'appreciation'
type TabId = 'joy-board' | 'moderation' | 'advocacy'

const entryTypeLabels: Record<PositivityEntryType, string> = {
  feedback: 'Positive patron feedback',
  win: 'Win of the day',
  program: 'Program celebration',
  'thank-you': 'Thank-you note',
  compliment: 'Compliment to forward',
  story: 'Heartwarming patron story',
  appreciation: 'Staff appreciation',
}

export function summarizePositivity(praiseCount: number, complaintsCount: number): { praiseCount: number; ratioLabel: string } {
  if (praiseCount === 0 && complaintsCount === 0) return { praiseCount, ratioLabel: 'No entries yet' }
  if (complaintsCount === 0) return { praiseCount, ratioLabel: 'All praise this month' }
  const ratio = (praiseCount / complaintsCount).toFixed(1)
  return { praiseCount, ratioLabel: `${ratio}:1 praise-to-complaint` }
}

export default function StaffPositivityHubPage(): React.ReactElement {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabId>('joy-board')
  const [entryType, setEntryType] = useState<PositivityEntryType>('feedback')
  const [entryText, setEntryText] = useState('')
  const [complaintsCount, setComplaintsCount] = useState(0)
  const [entries, setEntries] = useState<PositivityEntry[]>([])
  const [digest, setDigest] = useState<PositivityDigest | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [moderationEntries, setModerationEntries] = useState<PositivityEntry[]>([])
  const [moderationLoading, setModerationLoading] = useState(false)
  const [rejectNotes, setRejectNotes] = useState<Record<number, string>>({})
  const [showRejectInput, setShowRejectInput] = useState<number | null>(null)
  const [advocacyData, setAdvocacyData] = useState<AdvocacyEntriesResponse | null>(null)
  const [advocacyLoading, setAdvocacyLoading] = useState(false)
  const [advocacyDays, setAdvocacyDays] = useState(90)

  const tablistId = useId()
  const tabIds: Record<TabId, string> = {
    'joy-board': `${tablistId}-joy-board`,
    'moderation': `${tablistId}-moderation`,
    'advocacy': `${tablistId}-advocacy`,
  }
  const panelIds: Record<TabId, string> = {
    'joy-board': `${tablistId}-joy-board-panel`,
    'moderation': `${tablistId}-moderation-panel`,
    'advocacy': `${tablistId}-advocacy-panel`,
  }
  const tabOrder: TabId[] = ['joy-board', 'moderation', 'advocacy']
  const tabRefs = useRef<Record<TabId, HTMLButtonElement | null>>({
    'joy-board': null,
    'moderation': null,
    'advocacy': null,
  })

  const focusTab = (id: TabId) => {
    setActiveTab(id)
    // Defer focus to next tick so React applies tabIndex updates first
    requestAnimationFrame(() => {
      tabRefs.current[id]?.focus()
    })
  }

  const handleTabKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const currentIndex = tabOrder.indexOf(activeTab)
    let nextIndex: number | null = null
    if (e.key === 'ArrowRight') {
      nextIndex = (currentIndex + 1) % tabOrder.length
    } else if (e.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + tabOrder.length) % tabOrder.length
    } else if (e.key === 'Home') {
      nextIndex = 0
    } else if (e.key === 'End') {
      nextIndex = tabOrder.length - 1
    }
    if (nextIndex !== null) {
      e.preventDefault()
      focusTab(tabOrder[nextIndex]!)
    }
  }

  useEffect(() => { const f = async () => { try { setIsLoading(true); setError(null); const [ed, dd] = await Promise.all([listPositivityEntries(1, 15), getPositivityDigest(30)]); setEntries(ed.entries); setDigest(dd) } catch (e) { setError(e instanceof Error ? e.message : 'Failed to load'); Sentry.captureException(e instanceof Error ? e : new Error(String(e))) } finally { setIsLoading(false) } }; f() }, [])

  const fetchMod = async () => { try { setModerationLoading(true); const d = await getModerationQueue(1, 50); setModerationEntries(d.entries) } catch (e) { setError(e instanceof Error ? e.message : 'Failed') } finally { setModerationLoading(false) } }



  useEffect(() => { if (activeTab === 'moderation') fetchMod() }, [activeTab])
  const fetchAdv = async () => { try { setAdvocacyLoading(true); const d = await getAdvocacyEntries(advocacyDays); setAdvocacyData(d) } catch (e) { setError(e instanceof Error ? e.message : 'Failed') } finally { setAdvocacyLoading(false) } }


  useEffect(() => { if (activeTab === 'advocacy') fetchAdv() }, [activeTab, advocacyDays])

  const monthlyDigest = useMemo(() => digest || { feedback: 0, win: 0, program: 0, thank_you: 0, compliment: 0, story: 0, appreciation: 0, total: 0, advocacy_flagged: 0, patron_submissions: 0, pending_moderation: 0 }, [digest])
  const positivitySummary = summarizePositivity(monthlyDigest.total, complaintsCount)
  const pendingCount = digest?.pending_moderation ?? 0

  const handleSubmit = async (event: FormEvent) => { event.preventDefault(); const t = entryText.trim(); if (!t) return; try { const n = await createPositivityEntry(entryType, t); setEntries(p => [n, ...p]); setEntryText(''); setDigest(await getPositivityDigest(30)) } catch (e) { setError(e instanceof Error ? e.message : 'Failed') } }
  const handleDeleteEntry = async (id: number) => { try { await deletePositivityEntry(id); setEntries(p => p.filter(e => e.id !== id)); setDigest(await getPositivityDigest(30)) } catch (e) { setError(e instanceof Error ? e.message : 'Failed') } }
  const handleToggleFlag = async (entry: PositivityEntry) => { try { const u = await toggleAdvocacyFlag(entry.id, !entry.flagged_for_advocacy); setEntries(p => p.map(e => e.id === u.id ? u : e)); setDigest(await getPositivityDigest(30)) } catch (e) { setError(e instanceof Error ? e.message : 'Failed') } }
  const handleModerate = async (id: number, action: 'approve' | 'reject') => { try { const note = action === 'reject' ? rejectNotes[id] : undefined; await moderateEntry(id, action, note); setModerationEntries(p => p.filter(e => e.id !== id)); setShowRejectInput(null); setRejectNotes(p => { const n = { ...p }; delete n[id]; return n }); const [ud] = await Promise.all([getPositivityDigest(30), action === 'approve' ? listPositivityEntries(1, 15).then(d => setEntries(d.entries)) : Promise.resolve()]); setDigest(ud) } catch (e) { setError(e instanceof Error ? e.message : 'Failed') } }

  return (
    <AdminShell title="Positivity Hub">
      <div className="space-y-6">
            <div
              role="tablist"
              aria-label="Positivity Hub sections"
              className="flex gap-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-1"
            >
              <button
                ref={el => { tabRefs.current['joy-board'] = el }}
                id={tabIds['joy-board']}
                role="tab"
                type="button"
                aria-selected={activeTab === 'joy-board'}
                aria-controls={panelIds['joy-board']}
                tabIndex={activeTab === 'joy-board' ? 0 : -1}
                onClick={() => setActiveTab('joy-board')}
                onKeyDown={handleTabKeyDown}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose ${activeTab === 'joy-board' ? 'bg-lsc-rose text-white' : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'}`}
              >
                <Heart aria-hidden="true" className="w-4 h-4" /> Joy Board
              </button>
              <button
                ref={el => { tabRefs.current['moderation'] = el }}
                id={tabIds['moderation']}
                role="tab"
                type="button"
                aria-selected={activeTab === 'moderation'}
                aria-controls={panelIds['moderation']}
                tabIndex={activeTab === 'moderation' ? 0 : -1}
                onClick={() => setActiveTab('moderation')}
                onKeyDown={handleTabKeyDown}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose ${activeTab === 'moderation' ? 'bg-lsc-rose text-white' : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'}`}
              >
                <Shield aria-hidden="true" className="w-4 h-4" /> Moderation
                {pendingCount > 0 && (
                  <span
                    aria-label={`${pendingCount} pending`}
                    className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-status-danger-500 rounded-full"
                  >
                    {pendingCount}
                  </span>
                )}
              </button>
              <button
                ref={el => { tabRefs.current['advocacy'] = el }}
                id={tabIds['advocacy']}
                role="tab"
                type="button"
                aria-selected={activeTab === 'advocacy'}
                aria-controls={panelIds['advocacy']}
                tabIndex={activeTab === 'advocacy' ? 0 : -1}
                onClick={() => setActiveTab('advocacy')}
                onKeyDown={handleTabKeyDown}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose ${activeTab === 'advocacy' ? 'bg-lsc-rose text-white' : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'}`}
              >
                <Megaphone aria-hidden="true" className="w-4 h-4" /> Advocacy
              </button>
            </div>
            {error && <div role="alert" className="rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20 p-3"><p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p></div>}

            {activeTab === 'joy-board' && (<div
              role="tabpanel"
              id={panelIds['joy-board']}
              aria-labelledby={tabIds['joy-board']}
              tabIndex={0}
              className="focus:outline-none space-y-6"
            >
              <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><SmilePlus className="w-5 h-5 text-lsc-rose" />{t('staffPositivityHub.logPositivePatronFeedbackQuickly')}</h2>
                <form onSubmit={handleSubmit} className="mt-4 grid gap-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Entry type<select value={entryType} onChange={e => setEntryType(e.target.value as PositivityEntryType)} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2">{Object.entries(entryTypeLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
                    <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('staffPositivityHub.complaintsLoggedThisMonth')}<input type="number" min={0} value={complaintsCount} onChange={e => setComplaintsCount(Number(e.target.value || 0))} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2" /></label>
                  </div>
                  <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('staffPositivityHub.addJoyToTheRecord')}<textarea required value={entryText} onChange={e => setEntryText(e.target.value)} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 min-h-[100px]" placeholder={t('staffPositivityHub.examplePatronSaidOurDigital')} /></label>
                  <div className="flex justify-end"><button type="submit" disabled={isLoading} className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose text-white px-4 py-2 font-medium hover:bg-lsc-rose-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><Send className="w-4 h-4" />Save positivity entry</button></div>
                </form>
              </section>
              <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm"><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Documented praise</p><p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{positivitySummary.praiseCount}</p></article>
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm"><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Balance tracker</p><p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mt-1">{positivitySummary.ratioLabel}</p></article>
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm"><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Advocacy flagged</p><p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{monthlyDigest.advocacy_flagged}</p></article>
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm"><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Patron submissions</p><p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{monthlyDigest.patron_submissions}</p></article>
              </section>
              <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><Sparkles className="w-5 h-5 text-lsc-rose" />Monthly positivity digest</h2>
                {isLoading ? <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p> : <div className="mt-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-sm"><p><strong>{monthlyDigest.feedback}</strong> positive patron feedback entries</p><p><strong>{monthlyDigest.thank_you}</strong> thank-you notes stored</p><p><strong>{monthlyDigest.compliment}</strong> compliments ready to forward</p><p><strong>{monthlyDigest.story}</strong> heartwarming patron stories</p><p><strong>{monthlyDigest.appreciation}</strong> staff appreciation moments</p><p><strong>{monthlyDigest.win}</strong> win-of-the-day shares</p></div>}
              </section>
              <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><Heart className="w-5 h-5 text-lsc-rose" />Joy board</h2>
                {isLoading ? <p className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p> : entries.length === 0 ? <p className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPositivityHub.noEntriesYetStartWith')}</p> : <ul className="mt-4 space-y-3">{entries.slice(0, 15).map(entry => <li key={entry.id} className="rounded-lg border border-lsc-border dark:border-earth-700 p-3"><div className="flex justify-between items-start gap-2"><div className="flex-1"><div className="flex items-center gap-2"><p className="text-xs uppercase tracking-wide text-lsc-rose font-semibold">{entryTypeLabels[entry.entry_type as PositivityEntryType] || entry.entry_type}</p>{entry.source === 'patron' && <span className="text-xs bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light px-2 py-0.5 rounded-full">Patron submission</span>}</div><p className="text-sm text-lsc-dark dark:text-lsc-cream mt-1">{entry.text}</p>{entry.source === 'patron' && entry.patron_name && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">- {entry.patron_name}</p>}</div><div className="flex items-center gap-1"><button onClick={() => handleToggleFlag(entry)} className={`p-1 rounded transition-colors ${entry.flagged_for_advocacy ? 'text-status-warning-500 hover:text-status-warning-600' : 'text-lsc-dark/30 dark:text-lsc-cream/60 hover:text-status-warning-500'}`} title={entry.flagged_for_advocacy ? 'Remove advocacy flag' : 'Flag for advocacy'}><Star className={`w-4 h-4 ${entry.flagged_for_advocacy ? 'fill-current' : ''}`} /></button><button onClick={() => handleDeleteEntry(entry.id)} className="text-xs text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300 transition-colors whitespace-nowrap p-1">Delete</button></div></div></li>)}</ul>}
              </section>
              <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm"><h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><MessageSquareHeart className="w-4 h-4 text-lsc-rose" />Compliment forwarding</h3><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('staffPositivityHub.copyNamesAndQuotesFrom')}</p></article>
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm"><h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><Trophy className="w-4 h-4 text-lsc-rose" />{t('staffPositivityHub.rememberWhyWeDoThis')}</h3><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('staffPositivityHub.useOneStoryFromThis')}</p></article>
                <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm md:col-span-2"><h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><BookHeart className="w-4 h-4 text-lsc-rose" />Thank-you note repository</h3><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('staffPositivityHub.logQuickNotesFromCards')}</p></article>
              </section>
            </div>)}

            {activeTab === 'moderation' && <div
              role="tabpanel"
              id={panelIds['moderation']}
              aria-labelledby={tabIds['moderation']}
              tabIndex={0}
              className="focus:outline-none"
            ><section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-6"><h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><Shield className="w-5 h-5 text-lsc-rose" />Patron submission moderation</h2><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('staffPositivityHub.reviewPatronSubmittedExperiencesBefore')}</p>{moderationLoading ? <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p> : moderationEntries.length === 0 ? <div className="mt-6 text-center py-8"><Shield className="w-10 h-10 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto" /><p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPositivityHub.noSubmissionsAwaitingReview')}</p></div> : <ul className="mt-4 space-y-3">{moderationEntries.map(entry => <li key={entry.id} className="rounded-lg border border-lsc-border dark:border-earth-700 p-4"><div className="flex justify-between items-start gap-3"><div className="flex-1"><div className="flex items-center gap-2"><p className="text-xs uppercase tracking-wide text-lsc-rose font-semibold">{entryTypeLabels[entry.entry_type as PositivityEntryType] || entry.entry_type}</p><span className={`text-xs px-2 py-0.5 rounded-full ${entry.moderation_status === 'pending' ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300' : entry.moderation_status === 'approved' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'}`}>{entry.moderation_status}</span></div><p className="text-sm text-lsc-dark dark:text-lsc-cream mt-2">{entry.text}</p>{entry.patron_name && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Submitted by: {entry.patron_name}</p>}<p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{new Date(entry.created_at).toLocaleDateString()}</p></div>{entry.moderation_status === 'pending' && <div className="flex items-center gap-2"><button onClick={() => handleModerate(entry.id, 'approve')} className="inline-flex items-center gap-1 text-sm text-status-success-600 dark:text-status-success-400 hover:text-status-success-800 font-medium"><CheckCircle className="w-4 h-4" />Approve</button><button onClick={() => setShowRejectInput(showRejectInput === entry.id ? null : entry.id)} className="inline-flex items-center gap-1 text-sm text-status-danger-600 dark:text-status-danger-400 hover:text-status-danger-800 font-medium"><XCircle className="w-4 h-4" />Reject</button></div>}</div>{showRejectInput === entry.id && <div className="mt-3 flex gap-2"><input type="text" placeholder={t('placeholder.staffPositivityHub.optionalRejectionNote')} value={rejectNotes[entry.id] || ''} onChange={e => setRejectNotes(p => ({ ...p, [entry.id]: e.target.value }))} className="flex-1 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-1.5 text-sm" /><button onClick={() => handleModerate(entry.id, 'reject')} className="rounded-lg bg-status-danger-500 text-white px-3 py-1.5 text-sm font-medium hover:bg-status-danger-600">Confirm reject</button></div>}</li>)}</ul>}</section></div>}

            {activeTab === 'advocacy' && <div
              role="tabpanel"
              id={panelIds['advocacy']}
              aria-labelledby={tabIds['advocacy']}
              tabIndex={0}
              className="focus:outline-none"
            ><section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-6"><div className="flex items-center justify-between"><div><h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><Megaphone className="w-5 h-5 text-lsc-rose" />Advocacy pipeline</h2><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{advocacyData ? `${advocacyData.count} stories flagged for advocacy` : 'Loading...'}</p></div><select value={advocacyDays} onChange={e => setAdvocacyDays(Number(e.target.value))} className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-1.5 text-sm"><option value={30}>Last 30 days</option><option value={60}>Last 60 days</option><option value={90}>Last 90 days</option><option value={365}>Last year</option></select></div>{advocacyLoading ? <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p> : !advocacyData || advocacyData.entries.length === 0 ? <div className="mt-6 text-center py-8"><Star className="w-10 h-10 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto" /><p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPositivityHub.noEntriesFlaggedForAdvocacy')}</p></div> : <ul className="mt-4 space-y-3">{advocacyData.entries.map(entry => <li key={entry.id} className="rounded-lg border border-lsc-border dark:border-earth-700 p-4"><div className="flex items-center gap-2 mb-2"><Star className="w-4 h-4 text-status-warning-500 fill-current" /><p className="text-xs uppercase tracking-wide text-lsc-rose font-semibold">{entryTypeLabels[entry.entry_type as PositivityEntryType] || entry.entry_type}</p>{entry.source === 'patron' && <span className="text-xs bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light px-2 py-0.5 rounded-full">Patron</span>}</div><p className="text-sm text-lsc-dark dark:text-lsc-cream">{entry.text}</p><div className="mt-2 flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{entry.flagged_by_name && <span>Flagged by {entry.flagged_by_name}</span>}{entry.flagged_at && <span>{new Date(entry.flagged_at).toLocaleDateString()}</span>}{entry.patron_name && <span>From: {entry.patron_name}</span>}</div></li>)}</ul>}</section></div>}
      </div>
    </AdminShell>
  )
}
