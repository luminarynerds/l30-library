/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Mail, MessageSquare, Send, Sparkles, Megaphone, CalendarDays,
} from 'lucide-react'
import api from '@/lib/api-client'
import { OutreachStatusCard } from './OutreachStatusCard'
import type { ChannelType } from './ChannelBadge'

export type SectionId = 'email-notifications' | 'sms' | 'email-marketing' | 'marketing-hub' | 'campaigns' | 'event-marketing'

interface OutreachDashboardProps {
  onSelectSection: (id: SectionId) => void
}

interface StatusData {
  notificationsEnabled: boolean | null
  enabledNotifTypes: number | null
  smsProviderEnabled: boolean | null
  resendConnected: boolean | null
  savedContentCount: number | null
  activeEventCampaigns: number | null
}

const EMPTY: StatusData = {
  notificationsEnabled: null,
  enabledNotifTypes: null,
  smsProviderEnabled: null,
  resendConnected: null,
  savedContentCount: null,
  activeEventCampaigns: null,
}

export function OutreachDashboard({ onSelectSection }: OutreachDashboardProps) {
  const [data, setData] = useState<StatusData>(EMPTY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      const d = { ...EMPTY }
      const results = await Promise.allSettled([
        api.get('/organization-features'),
        api.get('/sms/staff/stats'),
        api.get('/marketing-hub/history', { params: { limit: 1 } }),
        api.get('/event-marketing/campaigns'),
      ])

      // Organization features contains notification_settings and email_marketing config
      if (results[0].status === 'fulfilled') {
        const r = results[0].value
        const config = r.configuration ?? {}

        // Notification settings
        const notifCfg = config.notification_settings
        if (notifCfg) {
          d.notificationsEnabled = notifCfg.notifications_enabled ?? false
          let count = 0
          if (notifCfg.courtesy_notice_enabled) count++
          if (notifCfg.overdue_notice_enabled) count++
          if (notifCfg.hold_placed_notification_enabled) count++
          if (notifCfg.hold_ready_notification_enabled) count++
          if (notifCfg.hold_expiring_soon_notification_enabled) count++
          if (notifCfg.event_reminder_enabled) count++
          d.enabledNotifTypes = count
        } else {
          d.notificationsEnabled = false
          d.enabledNotifTypes = 0
        }

        // Email delivery settings. The GET endpoint redacts the raw key and
        // instead returns `sendgrid_api_key_present` (bool) +
        // `sendgrid_api_key_source` ('env' | 'db' | 'none').
        const emailCfg = config.email_marketing
        if (emailCfg) {
          d.resendConnected = !!(emailCfg.sendgrid_api_key_present)
        } else {
          d.resendConnected = false
        }
      }

      // SMS staff stats -- if reachable, provider is enabled
      if (results[1].status === 'fulfilled') {
        d.smsProviderEnabled = true
      } else {
        d.smsProviderEnabled = false
      }

      // Marketing hub history
      if (results[2].status === 'fulfilled') {
        const r = results[2].value
        d.savedContentCount = r.total ?? (Array.isArray(r.items) ? r.items.length : 0)
      } else {
        d.savedContentCount = 0
      }

      // Event marketing campaigns
      if (results[3].status === 'fulfilled') {
        const r = results[3].value
        const campaigns = Array.isArray(r) ? r : (r.campaigns ?? r.data ?? [])
        d.activeEventCampaigns = campaigns.filter(
          (c: { status?: string; archive_status?: string }) =>
            c.status === 'active' || c.status === 'scheduled' || c.archive_status === 'active'
        ).length
      } else {
        d.activeEventCampaigns = 0
      }
      setData(d)
      setLoading(false)
    }
    void load()
  }, [])

  if (loading) {
    return (
      <div aria-busy="true" aria-label="Loading outreach dashboard">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-48 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-48 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  function emailStatus(): string | null {
    if (data.notificationsEnabled === null) return 'Not configured'
    if (!data.notificationsEnabled) return 'Notifications OFF'
    return `Notifications ON -- ${data.enabledNotifTypes ?? 0} of 6 types enabled`
  }

  function smsStatus(): string | null {
    if (data.smsProviderEnabled === null) return 'Not configured'
    return data.smsProviderEnabled ? 'Provider enabled' : 'Provider not configured'
  }

  function emailMarketingStatus(): string | null {
    if (data.resendConnected === null) return 'Not configured'
    return data.resendConnected ? 'Resend configured' : 'Resend not configured'
  }

  function hubStatus(): string | null {
    if (data.savedContentCount === null) return 'Not configured'
    return `${data.savedContentCount} saved item${data.savedContentCount !== 1 ? 's' : ''}`
  }

  function eventStatus(): string | null {
    if (data.activeEventCampaigns === null) return 'Not configured'
    return `${data.activeEventCampaigns} active campaign${data.activeEventCampaigns !== 1 ? 's' : ''}`
  }

  type CardDef = {
    id: SectionId
    icon: React.ReactNode
    title: string
    description: string
    channel: ChannelType
    statusLine: string | null
    statusError: boolean
  }

  const directMessaging: CardDef[] = [
    {
      id: 'email-notifications',
      icon: <Mail className="w-5 h-5 text-lsc-rose" />,
      title: 'Email Notifications',
      description: 'Controls what emails patrons get -- due date reminders, hold alerts, event reminders. You set the rules, patrons set their preferences.',
      channel: 'email',
      statusLine: emailStatus(),
      statusError: data.notificationsEnabled === null,
    },
    {
      id: 'sms',
      icon: <MessageSquare className="w-5 h-5 text-lsc-rose" />,
      title: 'SMS Settings',
      description: 'Text message notifications for patrons who prefer texts. Includes quiet hours so you never wake anyone up.',
      channel: 'sms',
      statusLine: smsStatus(),
      statusError: data.smsProviderEnabled === null,
    },
    {
      id: 'email-marketing',
      icon: <Send className="w-5 h-5 text-lsc-rose" />,
      title: 'Email Delivery',
      description: 'Transactional email via Resend. Configure your API key, sender identity, and send safeguards.',
      channel: 'email',
      statusLine: emailMarketingStatus(),
      statusError: data.resendConnected === null,
    },
  ]

  const campaignTools: CardDef[] = [
    {
      id: 'marketing-hub',
      icon: <Sparkles className="w-5 h-5 text-lsc-rose" />,
      title: 'Marketing Hub',
      description: 'Generate marketing copy, social posts, and newsletter content with AI. Save and reuse what works.',
      channel: 'ai',
      statusLine: hubStatus(),
      statusError: data.savedContentCount === null,
    },
    {
      id: 'campaigns',
      icon: <Megaphone className="w-5 h-5 text-lsc-rose" />,
      title: 'Marketing',
      description: 'Manage the newsletter interest categories patrons can subscribe to, and see how the mail is performing.',
      channel: 'campaign',
      statusLine: null,
      statusError: false,
    },
    {
      id: 'event-marketing',
      icon: <CalendarDays className="w-5 h-5 text-lsc-rose" />,
      title: 'Event Marketing',
      description: 'Promote upcoming events across channels -- email, social, flyers, calendar feeds. Track which promotions drive attendance.',
      channel: 'campaign',
      statusLine: eventStatus(),
      statusError: data.activeEventCampaigns === null,
    },
  ]

  return (
    <nav aria-label="Outreach settings">
      <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide mb-3">
        Direct Messaging
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        {directMessaging.map((card) => (
          <OutreachStatusCard
            key={card.id}
            id={card.id}
            icon={card.icon}
            title={card.title}
            description={card.description}
            channel={card.channel}
            statusLine={card.statusLine}
            statusError={card.statusError}
            onClick={(id) => onSelectSection(id as SectionId)}
          />
        ))}
      </div>
      <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide mb-3">
        Campaigns & Promotion
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {campaignTools.map((card) => (
          <OutreachStatusCard
            key={card.id}
            id={card.id}
            icon={card.icon}
            title={card.title}
            description={card.description}
            channel={card.channel}
            statusLine={card.statusLine}
            statusError={card.statusError}
            onClick={(id) => onSelectSection(id as SectionId)}
          />
        ))}
      </div>
    </nav>
  )
}
