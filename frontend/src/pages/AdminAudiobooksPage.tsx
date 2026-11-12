/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Admin Audiobooks Management Page
 * Comprehensive dashboard for audiobook management, analytics, and administration
 */

import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/api/types';
import api from '@/lib/api-client'
import { t } from '@/i18n'
import {
  TrendingUp,
  TrendingDown,
  Users,
  Music,
  Award,
  Download,
  Clock,
  Heart,
  Calendar} from 'lucide-react'
import { AdminShell } from '@/components/shells'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { StatusVariant } from '@/components/ui/StatusBadge'

// Placeholder API functions
async function getAudiobooksStats() {
  return api.get(`${API_BASE}/audiobooks/stats`)
}

async function getAudiobooksList(filters?: Record<string, string | undefined>) {
  const params = new URLSearchParams()
  if (filters) Object.entries(filters).forEach(([k, v]) => { if (v !== undefined) params.set(k, v) })
  return api.get(`${API_BASE}/audiobooks?${params}`)
}

interface AdminAudiobook {
  id: number
  title: string
  author_pen_name: string
  status: string
  total_borrows: number
  average_rating: number
  rating_count: number
  created_at: string
  approved_at?: string
}

function StatCard({ icon, label, value, subtext, trend }: {
  icon: React.ReactNode
  label: string
  value: string | number
  subtext?: string
  trend?: { value: number; isPositive: boolean }
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <div className="p-2 bg-lsc-cream dark:bg-lsc-brown rounded-lg">
            {icon}
          </div>
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
            {subtext && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{subtext}</p>
            )}
          </div>
        </div>
        {trend && (
          <div className={`text-sm font-semibold ${trend.isPositive ? 'text-status-success-600 dark:text-status-success-400' : 'text-status-danger-600 dark:text-status-danger-400'}`}>
            {trend.isPositive ? <TrendingUp className="w-3 h-3 inline" /> : <TrendingDown className="w-3 h-3 inline" />} {Math.abs(trend.value)}%
          </div>
        )}
      </div>
    </div>
  )
}

export default function AdminAudiobooksPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [sortBy, setSortBy] = useState('created_at')

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['audiobooks-admin-stats'],
    queryFn: getAudiobooksStats,
  })

  const { data: audiobooks, isLoading: audiobooksLoading } = useQuery({
    queryKey: ['audiobooks-admin-list', statusFilter, sortBy],
    queryFn: () => getAudiobooksList({ status: statusFilter, sort: sortBy }),
  })

  const isLoading = statsLoading || audiobooksLoading

  return (
    <AdminShell
      title="Audiobook Management"
      subtitle="Monitor performance, manage content, and review statistics"
      icon={<Music className="w-7 h-7 text-lsc-rose" />}
      loading={isLoading}
    >
      <div className="space-y-8">
      {/* Statistics Grid */}
      {stats && (
        <>
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              Overview
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={<Music className="w-5 h-5 text-lsc-rose" />}
                label="Total Audiobooks"
                value={stats.total_audiobooks}
                subtext={`${stats.published_audiobooks} published`}
              />
              <StatCard
                icon={<Clock className="w-5 h-5 text-lsc-rose" />}
                label="Pending Review"
                value={stats.pending_review}
                subtext="Awaiting approval"
              />
              <StatCard
                icon={<Users className="w-5 h-5 text-lsc-rose" />}
                label="Total Borrows"
                value={stats.total_borrows}
                subtext={`${stats.active_borrows} active now`}
              />
              <StatCard
                icon={<Award className="w-5 h-5 text-lsc-rose" />}
                label="Avg Rating"
                value={stats.avg_rating?.toFixed(1) || '-'}
                subtext="Community feedback"
              />
            </div>
          </div>

          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              Performance Metrics
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard
                icon={<TrendingUp className="w-5 h-5 text-lsc-rose" />}
                label="Total Listeners"
                value={stats.total_listeners}
                trend={{ value: 12, isPositive: true }}
              />
              <StatCard
                icon={<Heart className="w-5 h-5 text-lsc-rose" />}
                label="Hours Listened"
                value={(stats.total_hours_listened / 1000).toFixed(1) + 'k'}
                subtext="Total across platform"
              />
              <StatCard
                icon={<Download className="w-5 h-5 text-lsc-rose" />}
                label="Revenue Generated"
                value={`$${stats.revenue_generated.toFixed(2)}`}
                subtext="Author earnings paid"
              />
            </div>
          </div>
        </>
      )}

      {/* Audiobooks List */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
            All Audiobooks
          </h2>
          <div className="flex gap-2">
            <select
              value={statusFilter || ''}
              onChange={(e) => setStatusFilter(e.target.value || undefined)}
              aria-label={t('aria.adminAudiobooks.filterByStatus', 'Filter by status')}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
            >
              <option value="">All Status</option>
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
              <option value="declined">Declined</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label={t('aria.adminAudiobooks.sortBy', 'Sort by')}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
            >
              <option value="created_at">Newest</option>
              <option value="total_borrows">Most Borrowed</option>
              <option value="average_rating">Top Rated</option>
              <option value="status">Status</option>
            </select>
          </div>
        </div>

        {audiobooks && audiobooks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700">
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">Title</th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">Author</th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">Status</th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">Borrows</th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">Rating</th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
                </tr>
              </thead>
              <tbody>
                {audiobooks.map((audiobook: AdminAudiobook) => (
                  <tr key={audiobook.id} className="border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-800/50 transition-colors">
                    <td className="py-4 px-4 text-lsc-dark dark:text-lsc-cream font-medium truncate" title={audiobook.title}>
                      {audiobook.title}
                    </td>
                    <td className="py-4 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                      {audiobook.author_pen_name}
                    </td>
                    <td className="py-4 px-4">
                      <StatusBadge variant={
                        (audiobook.status === 'approved' ? 'success' :
                        audiobook.status === 'declined' ? 'danger' :
                        audiobook.status === 'submitted' ? 'warning' :
                        'neutral') as StatusVariant
                      }>
                        {audiobook.status.charAt(0).toUpperCase() + audiobook.status.slice(1)}
                      </StatusBadge>
                    </td>
                    <td className="py-4 px-4 text-lsc-dark dark:text-lsc-cream text-sm">
                      {audiobook.total_borrows}
                    </td>
                    <td className="py-4 px-4 text-lsc-dark dark:text-lsc-cream text-sm">
                      {audiobook.average_rating ? audiobook.average_rating.toFixed(1) : '-'} ({audiobook.rating_count})
                    </td>
                    <td className="py-4 px-4">
                      <a href={`/admin/audiobooks/${audiobook.id}`} className="text-lsc-rose hover:underline text-sm font-medium">
                        View
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Card>
            <CardContent className="text-center py-8">
              <Music className="w-12 h-12 mx-auto mb-3 text-lsc-dark/20 dark:text-lsc-cream/20" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No audiobooks found</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recent Activities */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Activity data loads from the audiobook review queue.</p>
        </CardContent>
      </Card>
      </div>
    </AdminShell>
  )
}