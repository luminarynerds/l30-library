/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { Loader2, Send, X } from "lucide-react";
import { API_BASE } from '@/api/types';
import api from "../../api/api";
import toast from "react-hot-toast";
import { useTranslation } from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface EmailModalProps {
  reportId: number;
  onClose: () => void;
  onSuccess: () => void;
}

export function EmailReportModal({ reportId, onClose, onSuccess }: EmailModalProps) {
  const { t } = useTranslation();
  const [sending, setSending] = useState(false);
  const [emails, setEmails] = useState<string[]>([]);
  const [emailInput, setEmailInput] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const addEmail = () => {
    const trimmed = emailInput.trim();
    if (trimmed && !emails.includes(trimmed) && trimmed.includes("@")) {
      setEmails([...emails, trimmed]);
      setEmailInput("");
    }
  };

  const removeEmail = (email: string) => {
    setEmails(emails.filter((e) => e !== email));
  };

  const handleSend = async () => {
    if (emails.length === 0) {
      toast.error(t('boardReports.addAtLeastOneEmail'));
      return;
    }

    try {
      setSending(true);
      const response = await api.post(`${API_BASE}/board/reports/${reportId}/send-email`, emails);
      toast.success(response?.message || t('toast.boardReports.reportEmailSent'));
      onSuccess();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReports.failedToSendReportEmail'));
    } finally {
      setSending(false);
    }
  };

  return (
    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-labelledby="email-report-title">
      <div className="bg-lsc-white dark:bg-earth-900 rounded-lg shadow-lg max-w-md w-full">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 id="email-report-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Send className="w-5 h-5" />
              Email Report to Board
            </h2>
            <button onClick={onClose} aria-label="Close" className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-earth-600 hover:text-earth-900 dark:text-earth-200 dark:hover:text-earth-100 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg">
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>

          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            Send the report with PowerPoint and PDF attachments to board members.
          </p>

          <div className="mb-4">
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Recipient Emails
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addEmail();
                  }
                }}
                className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                placeholder={t('placeholder.boardReports.boardmemberexamplecom')}
              />
              <button
                type="button"
                onClick={addEmail}
                className="px-3 py-2 bg-earth-300 dark:bg-earth-700 rounded-lg hover:bg-earth-400 dark:hover:bg-earth-600 text-sm"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {emails.map((email) => (
                <span
                  key={email}
                  className="px-2 py-1 bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80 rounded text-xs flex items-center gap-1"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => removeEmail(email)}
                    className="ml-1 hover:text-status-danger-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="flex gap-2 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800 rounded-lg transition-colors text-sm"
            >
              Cancel
            </button>
            <button
              onClick={handleSend}
              disabled={sending || emails.length === 0}
              className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm"
            >
              {sending ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send to {emails.length} Recipient{emails.length !== 1 ? "s" : ""}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
    </FocusTrap>
  );
}
