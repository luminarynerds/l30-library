/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { API_BASE } from '@/api/types';
import api from "../../api/api";
import toast from "react-hot-toast";
import { useTranslation } from '@/i18n'
import FocusTrap from 'focus-trap-react'


interface GeneratorFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function BoardReportGeneratorForm({ onClose, onSuccess }: GeneratorFormProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
    end_date: new Date().toISOString().split("T")[0],
    include_comparison: true,
    export_format: "both",
    send_to_emails: [] as string[],
  });
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
    if (trimmed && !formData.send_to_emails.includes(trimmed) && trimmed.includes("@")) {
      setFormData({ ...formData, send_to_emails: [...formData.send_to_emails, trimmed] });
      setEmailInput("");
    }
  };

  const removeEmail = (email: string) => {
    setFormData({
      ...formData,
      send_to_emails: formData.send_to_emails.filter((e) => e !== email),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.start_date && formData.end_date && new Date(formData.start_date) >= new Date(formData.end_date)) {
      toast.error(t("boardReports.startBeforeEnd") || "Start date must be before end date");
      return;
    }
    try {
      setLoading(true);
      await api.post(`${API_BASE}/board/reports/generate`, {
        start_date: new Date(formData.start_date ?? '').toISOString(),
        end_date: new Date(formData.end_date ?? '').toISOString(),
        include_comparison: formData.include_comparison,
        export_format: formData.export_format,
        send_to_emails: formData.send_to_emails.length > 0 ? formData.send_to_emails : undefined,
      });
      toast.success(t('toast.boardReports.reportGeneratedSuccessfully'));
      onSuccess();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReports.failedToGenerateReport'));
    } finally {
      setLoading(false);
    }
  };

  return (

    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="generator-form-title">
      <div className="bg-lsc-white dark:bg-earth-900 rounded-lg shadow-lg max-w-md w-full my-8">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 id="generator-form-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              Generate Custom Report
            </h2>
            <button onClick={onClose} aria-label="Close" className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-earth-600 hover:text-earth-900 dark:text-earth-200 dark:hover:text-earth-100 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg">
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Export Format
              </label>
              <select
                value={formData.export_format}
                onChange={(e) => setFormData({ ...formData, export_format: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
              >
                <option value="both">PowerPoint & PDF</option>
                <option value="powerpoint">PowerPoint Only</option>
                <option value="pdf">PDF Only</option>
              </select>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.include_comparison}
                onChange={(e) => setFormData({ ...formData, include_comparison: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Include comparison to previous period
              </span>
            </label>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Email to Board Members (optional)
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
                {formData.send_to_emails.map((email) => (
                  <span
                    key={email}
                    className="px-2 py-1 bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80 rounded text-xs flex items-center gap-1"
                  >
                    {email}
                    <button type="button" onClick={() => removeEmail(email)} className="hover:text-status-danger-600">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800 rounded-lg transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm"
              >
                {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                Generate Report
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
    </FocusTrap>

  );
}
