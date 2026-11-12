/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, MessageCircle, CalendarDays
} from 'lucide-react'
import { EmptyState } from '../components/ui/EmptyState'
import { useTranslation} from '@/i18n'

export default function BookClubDiscussionPage(): React.ReactElement {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string; meetingId: string }>()

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link
        to={`/book-clubs/${id}`}
        className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Club
      </Link>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Discussion Threads - Main Area */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Discussion Threads
            </h2>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <EmptyState
              icon={MessageCircle}
              title={t('bookClubDiscussion.noDiscussionThreadsYet')}
              description="Be the first to start a conversation about this meeting's reading."
              size="sm"
            />
          </div>
        </div>

        {/* Coming Soon Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center space-y-4">
            <MessageCircle className="w-12 h-12 text-earth-300 dark:text-lsc-cream/10 mx-auto" />
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream/80">
              Discussions Coming Soon
            </h3>
            <p className="text-sm text-earth-600 dark:text-lsc-cream/40">
              Live book club discussions are coming soon. In the meantime, check out our book club events for in-person discussions.
            </p>
            <Link
              to="/events"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 transition-colors"
            >
              <CalendarDays className="w-4 h-4" />
              View Events
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
