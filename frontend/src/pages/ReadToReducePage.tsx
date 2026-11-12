/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { fetchApi } from '@/api/fetchApi';
import {
  Book, Clock, Star, Send, CheckCircle, XCircle, Loader2, Trophy, Sparkles,
  Flame, Zap, Crown, Compass, PenTool, BookMarked, Sword, BookOpen,
  Download, Printer, QrCode, Users
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

interface ReadingBalance {
  minutes_owed: number
  minutes_logged: number
  minutes_pending: number
  balance: number
  pending_logs: number
}

interface ReadingStats {
  streak: number
  longest_streak: number
  xp: number
  level: number
  xp_to_next_level: number
  total_approved_minutes: number
  total_submissions: number
  unique_books: number
  notes_written: number
}

interface Achievement {
  id: number
  slug: string
  name: string
  description: string
  icon: string
  xp: number
  earned: boolean
  earned_at: string | null
}

interface ReadingLog {
  id: number
  minutes: number
  book_title: string | null
  book_author: string | null
  notes: string | null
  status: "pending" | "approved" | "rejected"
  reading_date: string
  created_at: string
  rejection_reason: string | null
}

interface CommunityStats {
  monthly_minutes: number
  total_minutes: number
  active_readers_this_month: number
  message: string
}

interface BadgeEarned {
  slug: string
  name: string
}

interface ExportData {
  patron_name: string
  date_from: string | null
  date_to: string | null
  teacher_name?: string
  school_name?: string
  total_minutes: number
  total_sessions: number
  books_read?: unknown[]
  badges_earned?: BadgeEarned[]
  verification_code: string
}

const ICON_MAP: Record<string, React.ReactNode> = {
  BookOpen: <BookOpen className="w-6 h-6" />,
  BookMarked: <BookMarked className="w-6 h-6" />,
  Sword: <Sword className="w-6 h-6" />,
  Trophy: <Trophy className="w-6 h-6" />,
  Flame: <Flame className="w-6 h-6" />,
  Zap: <Zap className="w-6 h-6" />,
  Crown: <Crown className="w-6 h-6" />,
  Compass: <Compass className="w-6 h-6" />,
  PenTool: <PenTool className="w-6 h-6" />,
  CheckCircle: <CheckCircle className="w-6 h-6" />,
}

function ProgressRing({ progress, size = 60, strokeWidth = 6 }: { progress: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (progress / 100) * circumference

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} className="text-lsc-border dark:text-lsc-cream/70" />
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="text-lsc-rose transition-all duration-500" />
    </svg>
  )
}

function BadgeCard({ badge }: { badge: Achievement }) {
  return (
    <div className={`relative p-3 rounded-xl border-2 transition-all ${badge.earned ? "bg-gradient-to-br from-status-warning-50 to-status-warning-100 dark:from-lsc-dark/30 dark:to-lsc-dark/30 border-lsc-border dark:border-earth-700" : "bg-lsc-cream dark:bg-earth-800 border-lsc-border dark:border-earth-700 opacity-60"}`}>
      <div className={`w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-2 ${badge.earned ? "bg-lsc-cream dark:bg-lsc-rose-light text-lsc-rose dark:text-lsc-rose-light/50" : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70"}`}>
        {ICON_MAP[badge.icon] || <Star className="w-6 h-6" />}
      </div>
      <p className={`text-xs font-medium text-center ${badge.earned ? "text-lsc-dark dark:text-lsc-cream" : "text-lsc-dark/70 dark:text-lsc-cream/70"}`}>{badge.name}</p>
      {badge.earned && <div className="absolute -top-1 -right-1 w-5 h-5 bg-status-success-500 rounded-full flex items-center justify-center"><CheckCircle className="w-3 h-3 text-white" /></div>}
    </div>
  )
}

function ExportModal({ isOpen, onClose, token }: { isOpen: boolean; onClose: () => void; token: string | null }) {
  const branding = useBranding()
  const { t } = useTranslation();
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [teacherName, setTeacherName] = useState("")
  const [schoolName, setSchoolName] = useState("")
  const [isExporting, setIsExporting] = useState(false)
  const [exportData, setExportData] = useState<ExportData | null>(null)

  const handleExport = async () => {
    if (!token) return
    setIsExporting(true)
    try {
      const data = await fetchApi('/reading/export', {
        method: "POST",
        body: JSON.stringify({ date_from: dateFrom || null, date_to: dateTo || null, teacher_name: teacherName || null, school_name: schoolName || null }),
      })
      setExportData(data)
      toast.success(t('toast.readToReduce.reportGenerated'))
    } catch { toast.error(t('readToReduce.failedToGenerateReport')) } finally { setIsExporting(false) }
  }

  if (!isOpen) return null

  return (
    <ModalBackdrop onClose={onClose} title="Export Reading Report">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-lg">
        {!exportData ? (
          <div className="p-6">
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2"><Download className="w-5 h-5 text-lsc-rose" />Export Reading Report</h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('readToReduce.generateAReportToShow')}</p>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">From Date</label><input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div>
                <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">To Date</label><input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div>
              </div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Teacher Name (optional)</label><input type="text" value={teacherName} onChange={(e) => setTeacherName(e.target.value)} placeholder={t('placeholder.readToReduce.mrsJohnson')} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">School Name (optional)</label><input type="text" value={schoolName} onChange={(e) => setSchoolName(e.target.value)} placeholder={t('placeholder.readToReduce.partnerElementary')} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500" /></div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 hover:bg-lsc-cream dark:text-lsc-cream/70 dark:hover:bg-lsc-brown rounded-xl transition-colors">Cancel</button>
              <button onClick={handleExport} disabled={isExporting} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose text-white rounded-xl transition-colors flex items-center gap-2">{isExporting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}Generate Report</button>
            </div>
          </div>
        ) : (
          <div className="print:p-0">
            <div className="p-6 print:p-8" id="reading-report">
              <div className="text-center mb-6 print:mb-8">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-earth-800/30 rounded-full mb-2 print:bg-transparent"><Book className="w-5 h-5 text-lsc-rose" /><span className="font-medium text-lsc-rose dark:text-lsc-cream/70">{branding.library_short_name}</span></div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Reading Progress Report</h1>
              </div>
              <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-4 mb-6 print:border print:border-lsc-border">
                <div className="grid grid-cols-2 gap-4">
                  <div><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Student</p><p className="font-semibold text-lsc-dark dark:text-lsc-cream">{exportData.patron_name}</p></div>
                  <div><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Report Period</p><p className="font-semibold text-lsc-dark dark:text-lsc-cream">{exportData.date_from || "All time"} - {exportData.date_to || "Present"}</p></div>
                  {exportData.teacher_name && <div><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Teacher</p><p className="font-semibold text-lsc-dark dark:text-lsc-cream">{exportData.teacher_name}</p></div>}
                  {exportData.school_name && <div><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">School</p><p className="font-semibold text-lsc-dark dark:text-lsc-cream">{exportData.school_name}</p></div>}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 bg-lsc-cream dark:bg-earth-800/20 rounded-xl"><p className="text-3xl font-bold text-lsc-rose">{exportData.total_minutes}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Minutes Read</p></div>
                <div className="text-center p-4 bg-lsc-cream dark:bg-lsc-dark/20 rounded-xl"><p className="text-3xl font-bold text-lsc-rose">{exportData.total_sessions}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Sessions</p></div>
                <div className="text-center p-4 bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl"><p className="text-3xl font-bold text-lsc-rose">{exportData.books_read?.length || 0}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Books</p></div>
              </div>
              {exportData.badges_earned && exportData.badges_earned.length > 0 && <div className="mb-6"><h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Badges Earned</h3><div className="flex flex-wrap gap-2">{exportData.badges_earned.map((b) => <span key={b.slug} className="inline-flex items-center gap-1 px-3 py-1 bg-lsc-cream text-lsc-rose rounded-full text-sm">{b.name}</span>)}</div></div>}
              <div className="flex items-center justify-between border-t border-lsc-border dark:border-earth-700 pt-4">
                <div><p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Verification Code</p><p className="font-mono font-bold text-lsc-rose">{exportData.verification_code}</p></div>
                <div className="text-right"><p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Scan to verify</p><div className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70"><QrCode className="w-4 h-4" /><span className="text-xs">{branding.domain.replace('https://', '')}/reading/verify/{exportData.verification_code}</span></div></div>
              </div>
            </div>
            <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2 print:hidden">
              <button onClick={() => setExportData(null)} className="px-4 py-2 text-lsc-dark/70 hover:bg-lsc-cream dark:text-lsc-cream/70 dark:hover:bg-lsc-brown rounded-xl transition-colors">Back</button>
              <button onClick={() => window.print()} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors flex items-center gap-2"><Printer className="w-4 h-4" />Print Report</button>
            </div>
          </div>
        )}
      </div>
    </ModalBackdrop>
  )
}

export default function ReadToReducePage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isAuthenticated, isLoading: authLoading } = useAuth()
  const [balance, setBalance] = useState<ReadingBalance | null>(null)
  const [stats, setStats] = useState<ReadingStats | null>(null)
  const [achievements, setAchievements] = useState<Achievement[]>([])
  const [logs, setLogs] = useState<ReadingLog[]>([])
  const [community, setCommunity] = useState<CommunityStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [minutes, setMinutes] = useState(15)
  const [bookTitle, setBookTitle] = useState("")
  const [bookAuthor, setBookAuthor] = useState("")
  const [notes, setNotes] = useState("")
  const [readingDate, setReadingDate] = useState(() => new Date().toISOString().split("T")[0])

  const fetchData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const [balanceRes, statsRes, achievementsRes, logsRes, communityRes] = await Promise.all([
        fetchApi('/reading/balance'),
        fetchApi('/reading/my-stats'),
        fetchApi('/reading/achievements'),
        fetchApi('/reading/logs?limit=10'),
        fetchApi('/reading/community'),
      ])
      setBalance(balanceRes)
      setStats(statsRes)
      setAchievements(achievementsRes)
      setLogs(logsRes)
      setCommunity(communityRes)
    } catch (err: unknown) { Sentry.captureException(err instanceof Error ? err : new Error(String(err))); toast.error(t('toast.readToReduce.failedToLoadReadingData')) } finally { setIsLoading(false) }
  }, [token, t])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      setIsLoading(false)
    } else if (isAuthenticated && token) {
      fetchData()
    }
  }, [authLoading, isAuthenticated, token, fetchData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !readingDate) return
    setIsSubmitting(true)
    try {
      const dateObj = new Date(readingDate + "T12:00:00")
      const data = await fetchApi('/reading/log', {
        method: "POST",
        body: JSON.stringify({ minutes, book_title: bookTitle || null, book_author: bookAuthor || null, notes: notes || null, reading_date: dateObj.toISOString() }),
      })
      if (data.badges_earned?.length > 0) { data.badges_earned.forEach((badge: BadgeEarned) => { toast.success(`Badge earned: ${badge.name}!`, { duration: 5000 }) }) }
      else { toast.success(t('readToReduce.readingLoggedKeepItUp')) }
      setMinutes(15); setBookTitle(""); setBookAuthor(""); setNotes(""); fetchData()
    } catch (err: unknown) {
      const message = (err && typeof err === 'object' && 'message' in err) ? String((err as { message: unknown }).message) : t('toast.readToReduce.failedToSubmitReadingLog')
      toast.error(message)
    } finally { setIsSubmitting(false) }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved": return <span className="inline-flex items-center gap-1 px-2 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded-full text-xs font-medium"><CheckCircle className="w-3 h-3" /> Approved!</span>
      case "rejected": return <span className="inline-flex items-center gap-1 px-2 py-1 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-full text-xs font-medium"><XCircle className="w-3 h-3" /> Not Approved</span>
      default: return <span className="inline-flex items-center gap-1 px-2 py-1 bg-lsc-cream text-lsc-rose rounded-full text-xs font-medium"><Clock className="w-3 h-3" /> Waiting</span>
    }
  }

  if (authLoading || isLoading) return <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!isAuthenticated) return <div className="text-center py-12"><p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('readToReduce.pleaseLogInToUse')}</p></div>
  if (balance && balance.minutes_owed === 0) return (
    <PageContainer className="py-8">
      <div className="bg-gradient-to-br from-lsc-cream to-lsc-cream dark:from-sage-900/20 dark:to-earth-800 rounded-xl p-8 text-center shadow-lg border border-earth-100 dark:border-lsc-dark">
        <div className="w-20 h-20 bg-lsc-cream dark:bg-lsc-brown/50 rounded-full flex items-center justify-center mx-auto mb-4"><Trophy className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" /></div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('readToReduce.youReAllCaughtUp')}</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('readToReduce.youDonTHaveAny')}</p>
        {achievements.filter(a => a.earned).length > 0 && <div className="mt-6"><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Your Badges</p><div className="flex justify-center gap-2">{achievements.filter(a => a.earned).map(badge => <div key={badge.slug} className="w-10 h-10 bg-lsc-cream rounded-full flex items-center justify-center text-lsc-rose">{ICON_MAP[badge.icon] || <Star className="w-5 h-5" />}</div>)}</div></div>}
      </div>
    </PageContainer>
  )

  return (
    <PageContainer className="py-6 space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-dark/30 rounded-full mb-4"><Sparkles className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" /><span className="font-medium text-lsc-rose dark:text-lsc-rose-light">Read to Reduce</span></div>
        <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('readToReduce.turnReadingTimeIntoFree')}</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xl mx-auto">{t('readToReduce.logYourReadingToClear')}</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-orange-50 to-status-warning-50 dark:from-orange-900/20 dark:to-lsc-dark/20 rounded-xl p-4 text-center border border-status-warning-100 dark:border-status-warning-800">
            <div className="flex items-center justify-center gap-1 mb-1"><Flame className="w-5 h-5 text-status-warning-500" /><span className="text-2xl font-bold text-status-warning-600">{stats.streak}</span></div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Day Streak</p>
          </div>
          <div className="bg-gradient-to-br from-category-50 to-lsc-rose/10 dark:from-category-900/20 dark:to-lsc-rose/20 rounded-xl p-4 text-center border border-category-100 dark:border-category-800">
            <div className="flex items-center justify-center gap-2 mb-1"><div className="relative"><ProgressRing progress={((100 - stats.xp_to_next_level) / 100) * 100} size={40} strokeWidth={4} /><span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-category-600">{stats.level}</span></div></div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Level ({stats.xp} XP)</p>
          </div>
          <div className="bg-gradient-to-br from-lsc-cream to-lsc-cream dark:from-earth-800/20 dark:to-sage-900/20 rounded-xl p-4 text-center border border-earth-100 dark:border-earth-700">
            <span className="text-2xl font-bold text-lsc-rose">{balance?.balance || 0}</span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Minutes to Go</p>
          </div>
          <div className="bg-gradient-to-br from-status-warning-50 to-yellow-50 dark:from-lsc-dark/20 dark:to-yellow-900/20 rounded-xl p-4 text-center border border-earth-100 dark:border-earth-800">
            <span className="text-2xl font-bold text-lsc-rose">{achievements.filter(a => a.earned).length}/{achievements.length}</span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Badges Earned</p>
          </div>
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4"><Trophy className="w-5 h-5 text-lsc-rose" />Your Badges</h2>
        <div className="grid grid-cols-5 gap-3">{achievements.map(badge => <BadgeCard key={badge.slug} badge={badge} />)}</div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-6">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4"><Book className="w-5 h-5 text-lsc-rose" />Log Your Reading</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">{t('readToReduce.howManyMinutesDidYou')}</label>
              <div className="flex items-center gap-3"><input type="range" min={5} max={120} step={5} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="flex-1 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-xl appearance-none cursor-pointer accent-lsc-rose" /><span className="w-16 text-center text-lg font-bold text-lsc-rose dark:text-lsc-rose-light">{minutes} min</span></div>
            </div>
            <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">What book?</label><input type="text" value={bookTitle} onChange={(e) => setBookTitle(e.target.value)} placeholder={t('placeholder.readToReduce.egHarryPotter')} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500" /></div>
            <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">When?</label><input type="date" value={readingDate} onChange={(e) => setReadingDate(e.target.value)} max={new Date().toISOString().split("T")[0]} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div>
            <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">What happened? (optional)</label><textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t('placeholder.readToReduce.favoritePart')} rows={2} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 resize-none" /></div>
            <button type="submit" disabled={isSubmitting} className="w-full py-3 px-4 bg-lsc-rose hover:bg-lsc-rose disabled:bg-lsc-border text-white disabled:text-lsc-dark/70 dark:text-lsc-cream/50 font-medium rounded-xl flex items-center justify-center gap-2 transition-colors">{isSubmitting ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : <Send className="w-5 h-5" />}Log Reading</button>
          </form>
        </div>

        <div className="space-y-6">
          {community && (
            <div className="bg-gradient-to-br from-lsc-rose to-lsc-rose dark:from-lsc-rose dark:to-earth-700 rounded-xl p-6 text-white shadow-lg">
              <div className="flex items-center gap-2 mb-3"><Users className="w-5 h-5" /><h3 className="font-serif font-semibold">Reading Together</h3></div>
              <p className="text-3xl font-bold mb-1">{community.total_minutes.toLocaleString()} minutes</p>
              <p className="text-lsc-border text-sm">read by our library community</p>
              <div className="mt-3 pt-3 border-t border-earth-500/30 text-sm text-lsc-border">{community.active_readers_this_month} readers this month</div>
            </div>
          )}

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><Star className="w-5 h-5 text-lsc-rose" />Recent Activity</h2>
              <button onClick={() => setShowExport(true)} className="text-sm text-lsc-rose hover:text-lsc-rose flex items-center gap-1"><Download className="w-4 h-4" />Export</button>
            </div>
            {logs.length > 0 ? (
              <div className="space-y-3 max-h-[300px] overflow-y-auto">
                {logs.map((log) => (
                  <div key={log.id} className="p-3 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl border border-lsc-border dark:border-earth-700">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{log.minutes} min</p>
                        {log.book_title && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={log.book_title}>{log.book_title}</p>}
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{new Date(log.reading_date).toLocaleDateString()}</p>
                      </div>
                      {getStatusBadge(log.status)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70"><Book className="w-12 h-12 mx-auto mb-2 opacity-50" /><p>{t('readToReduce.noReadingLoggedYet')}</p></div>
            )}
          </div>
        </div>
      </div>

      <ExportModal isOpen={showExport} onClose={() => setShowExport(false)} token={token} />
    </PageContainer>
  )
}