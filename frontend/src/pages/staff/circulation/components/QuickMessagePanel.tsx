/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useMemo } from "react"
import { Mail, MessageSquare, Send, Loader2, ChevronDown, ChevronUp } from "lucide-react"
import toast from "react-hot-toast"
import {
  sendPatronMessage,
  type MessageType,
  type MessageChannel,
} from "@/api/domains/patron/patron-communication-api"
import type { Patron } from "../types"
import { useTranslation } from "@/i18n"

interface QuickMessagePanelProps {
  patron: Patron
  token: string
}

interface Template {
  type: MessageType
  label: string
  subject: string
  body: string
}

export function QuickMessagePanel({ patron, token }: QuickMessagePanelProps): React.ReactElement {
  const { t } = useTranslation()
  const TEMPLATES = useMemo<readonly [Template, ...Template[]]>(() => [
    {
      type: "overdue_notice",
      label: t('staffCirculation.quickMessage.templateOverdueLabel'),
      subject: t('staffCirculation.quickMessage.templateOverdueSubject'),
      body: t('staffCirculation.quickMessage.templateOverdueBody'),
    },
    {
      type: "hold_ready",
      label: t('staffCirculation.quickMessage.templateHoldReadyLabel'),
      subject: t('staffCirculation.quickMessage.templateHoldReadySubject'),
      body: t('staffCirculation.quickMessage.templateHoldReadyBody'),
    },
    {
      type: "account_blocked",
      label: t('staffCirculation.quickMessage.templateAccountLabel'),
      subject: t('staffCirculation.quickMessage.templateAccountSubject'),
      body: t('staffCirculation.quickMessage.templateAccountBody'),
    },
    {
      type: "custom",
      label: t('staffCirculation.quickMessage.templateCustomLabel'),
      subject: "",
      body: "",
    },
  ], [t])

  const [expanded, setExpanded] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<Template>(TEMPLATES[0])
  const [channel, setChannel] = useState<MessageChannel>("email")
  const [subject, setSubject] = useState(TEMPLATES[0].subject)
  const [body, setBody] = useState(TEMPLATES[0].body)
  const [sending, setSending] = useState(false)

  const handleTemplateChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const template = TEMPLATES.find((tpl) => tpl.type === e.target.value) || TEMPLATES[0]
    setSelectedTemplate(template)
    setSubject(template.subject)
    setBody(template.body)
  }, [TEMPLATES])

  const handleSend = useCallback(async () => {
    if (!subject.trim() || !body.trim()) {
      toast.error(t('staffCirculation.quickMessage.requiredToast'))
      return
    }

    if (channel === "email" && !patron.email) {
      toast.error(t('staffCirculation.quickMessage.noEmailToast'))
      return
    }

    if (channel === "sms" && !patron.phone) {
      toast.error(t('staffCirculation.quickMessage.noPhoneToast'))
      return
    }

    setSending(true)
    try {
      await sendPatronMessage(token, patron.id, {
        message_type: selectedTemplate.type,
        channel,
        subject: subject.trim(),
        body: body.trim(),
      })
      toast.success(channel === "email"
        ? t('staffCirculation.quickMessage.sentEmailToast')
        : t('staffCirculation.quickMessage.sentSmsToast'))
      setSelectedTemplate(TEMPLATES[0])
      setSubject(TEMPLATES[0].subject)
      setBody(TEMPLATES[0].body)
      setExpanded(false)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('staffCirculation.quickMessage.sendFailedToast'))
    } finally {
      setSending(false)
    }
  }, [token, patron, channel, subject, body, selectedTemplate, TEMPLATES, t])

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="w-full flex items-center justify-between gap-2 px-4 py-2.5 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-800/80 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Mail className="w-4 h-4" aria-hidden="true" />
          {t('staffCirculation.quickMessage.panelTitle')}
        </span>
        <ChevronDown className="w-4 h-4" aria-hidden="true" />
      </button>
    )
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Mail className="w-4 h-4" aria-hidden="true" />
          {t('staffCirculation.quickMessage.panelTitle')}
        </h3>
        <button
          onClick={() => setExpanded(false)}
          className="text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream"
          aria-label={t('staffCirculation.quickMessage.collapseAria')}
        >
          <ChevronUp className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Template + Channel row */}
      <div className="flex gap-2 mb-2">
        <select
          value={selectedTemplate.type}
          onChange={handleTemplateChange}
          className="flex-1 px-2.5 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-label={t('staffCirculation.quickMessage.templateAria')}
        >
          {TEMPLATES.map((tpl) => (
            <option key={tpl.type} value={tpl.type}>
              {tpl.label}
            </option>
          ))}
        </select>

        <div className="flex rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
          <button
            type="button"
            onClick={() => setChannel("email")}
            className={`px-2.5 py-1.5 text-sm flex items-center gap-1 transition-colors ${
              channel === "email"
                ? "bg-lsc-rose text-white"
                : "bg-lsc-white dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
            }`}
            aria-label={t('staffCirculation.quickMessage.sendViaEmailAria')}
            aria-pressed={channel === "email"}
          >
            <Mail className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">{t('staffCirculation.quickMessage.channelEmail')}</span>
          </button>
          <button
            type="button"
            onClick={() => setChannel("sms")}
            className={`px-2.5 py-1.5 text-sm flex items-center gap-1 transition-colors border-l border-lsc-border dark:border-earth-700 ${
              channel === "sms"
                ? "bg-lsc-rose text-white"
                : "bg-lsc-white dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
            }`}
            aria-label={t('staffCirculation.quickMessage.sendViaSmsAria')}
            aria-pressed={channel === "sms"}
          >
            <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">{t('staffCirculation.quickMessage.channelSms')}</span>
          </button>
        </div>
      </div>

      {/* Subject */}
      <input
        type="text"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder={t('staffCirculation.quickMessage.subjectPlaceholder')}
        className="w-full px-2.5 py-1.5 mb-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        aria-label={t('staffCirculation.quickMessage.subjectAria')}
      />

      {/* Body */}
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={t('staffCirculation.quickMessage.bodyPlaceholder')}
        rows={3}
        className="w-full px-2.5 py-1.5 mb-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
        aria-label={t('staffCirculation.quickMessage.bodyAria')}
      />

      {/* Send button */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('staffCirculation.quickMessage.toPrefix')} {patron.first_name} {patron.last_name}
          {channel === "email" ? ` (${patron.email})` : patron.phone ? ` (${patron.phone})` : ""}
        </span>
        <button
          onClick={handleSend}
          disabled={sending || !subject.trim() || !body.trim()}
          className="px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-lg font-medium text-sm flex items-center gap-1.5 transition-colors"
        >
          {sending ? (
            <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" aria-hidden="true" />
          ) : (
            <Send className="w-3.5 h-3.5" aria-hidden="true" />
          )}
          {t('staffCirculation.quickMessage.send')}
        </button>
      </div>

      {/* Screen reader announcement */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {sending ? t('staffCirculation.quickMessage.sendingMessage') : ""}
      </div>
    </div>
  )
}
