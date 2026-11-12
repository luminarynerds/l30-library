/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * My eBooks Page
 * View active ebook checkouts from MetisLib
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  Loader2,
  Clock,
  Download,
  RotateCcw,
  Library,
  ArrowLeft,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import { getMyMetisLibCheckouts, returnMetisLibEbook, getMetisLibDownloadUrl, type MetisLibCheckout } from '@/api/domains/catalog/metislib-api'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

function DownloadButton({ accessId, title }: { accessId: number; title: string }): React.ReactElement {
  const [loading, setLoading] = useState(false)
  const handleClick = async () => {
    setLoading(true)
    try {
      const data = await getMetisLibDownloadUrl(accessId)
      if ('provider' in data) {
        const blob = new Blob([JSON.stringify(data)], { type: 'application/vnd.readium.lcp.license.v1.0+json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${title}.lcpl`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Open with Thorium Reader or any LCP-compatible app', { duration: 5000 })
      } else if (data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer')
      }
    } catch {
      toast.error(t('toast.myEbooks.downloadFailed'))
    } finally {
      setLoading(false)
    }
  }
  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="flex items-center gap-1.5 px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
    >
      {loading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}
      Download
    </button>
  )
}

function CheckoutCard({ checkout, onReturn, isReturning }: { checkout: MetisLibCheckout; onReturn: (accessId: number) => void; isReturning: boolean }): React.ReactElement {
  const [coverFailed, setCoverFailed] = useState(false)
  const [now] = useState(() => Date.now())
  const daysLeft = checkout.expires_at
    ? Math.max(0, Math.ceil((new Date(checkout.expires_at).getTime() - now) / (1000 * 60 * 60 * 24)))
    : null

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 flex gap-4">
      {/* Cover */}
      <div className="w-16 h-24 bg-lsc-cream dark:bg-lsc-brown rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
        {checkout.cover_url && !coverFailed ? (
          <img
            src={checkout.cover_url}
            alt={`Cover of ${checkout.title}`}
            className="w-full h-full object-cover"
            onError={() => setCoverFailed(true)}
          />
        ) : (
          <BookOpen className="w-6 h-6 text-lsc-rose/30" aria-hidden="true" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <Link to={`/ebooks/${checkout.ebook_id}`} className="hover:text-lsc-rose transition-colors">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={checkout.title}>
            {checkout.title}
          </h3>
        </Link>
        <p className="text-sm text-earth-600 dark:text-earth-400 truncate" title={checkout.author_name}>
          {checkout.author_name}
        </p>

        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <span className="text-xs px-2 py-0.5 rounded bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300 uppercase">
            {checkout.format}
          </span>
          {daysLeft !== null && (
            <span className={clsx(
              'flex items-center gap-1 text-xs',
              daysLeft <= 3 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-earth-600 dark:text-earth-400'
            )}>
              <Clock className="w-3 h-3" />
              {daysLeft === 0 ? 'Expires today' : `${daysLeft} day${daysLeft !== 1 ? 's' : ''} left`}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 items-end">
        <DownloadButton accessId={checkout.access_id} title={checkout.title || 'ebook'} />
        <button
          onClick={() => onReturn(checkout.access_id)}
          disabled={isReturning}
          className="flex items-center gap-1 px-3 py-1.5 text-xs border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400"
        >
          <RotateCcw className="w-3 h-3" /> Return
        </button>
      </div>
    </div>
  )
}

export default function MyEbooksPage(): React.ReactElement {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const { data: checkouts, isLoading, error } = useQuery({
    queryKey: ['metislib-checkouts'],
    queryFn: getMyMetisLibCheckouts,
    enabled: !!user,
  })

  const returnMutation = useMutation({
    mutationFn: (accessId: number) => returnMetisLibEbook(accessId),
    onSuccess: () => {
      toast.success(t('toast.myBooks.ebookReturned'))
      queryClient.invalidateQueries({ queryKey: ['metislib-checkouts'] })
    },
    onError: (err: unknown) => {
      toast.error(friendlyErrorMessage(err))
    },
  })

  if (!user) {
    return (
      <PageContainer className="py-16 text-center">
        <BookOpen className="w-16 h-16 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
        <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          My eBooks
        </h1>
        <p className="text-earth-600 dark:text-earth-400 mb-4">
          Sign in to view your borrowed eBooks.
        </p>
        <Link to="/login" className="text-lsc-rose hover:underline">
          Sign in
        </Link>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <nav className="text-sm text-earth-600 dark:text-earth-400 mb-2">
            <Link to="/ebooks" className="flex items-center gap-1 hover:text-lsc-rose transition-colors">
              <ArrowLeft className="w-4 h-4" />
              eBooks
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <Library className="w-7 h-7 text-lsc-rose" />
            <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              My eBooks
            </h1>
          </div>
        </div>
        <Link
          to="/ebooks"
          className="text-sm text-lsc-rose hover:underline"
        >
          Browse more
        </Link>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-20">
          <p className="text-earth-600 dark:text-earth-400">
            Unable to load your eBooks. Please try again later.
          </p>
        </div>
      )}

      {/* Checkouts list */}
      {checkouts && checkouts.length > 0 && (
        <div className="space-y-3">
          {checkouts.map((checkout) => (
            <CheckoutCard
              key={checkout.access_id}
              checkout={checkout}
              onReturn={(id) => returnMutation.mutate(id)}
              isReturning={returnMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Empty */}
      {checkouts && checkouts.length === 0 && (
        <div className="text-center py-20">
          <BookOpen className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
          <h3 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream mb-1">
            No eBooks checked out
          </h3>
          <p className="text-earth-600 dark:text-earth-400 mb-4">
            Browse our digital collection and borrow something to read.
          </p>
          <Link
            to="/ebooks"
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            <BookOpen className="w-4 h-4" />
            Browse eBooks
          </Link>
        </div>
      )}
    </PageContainer>
  )
}
