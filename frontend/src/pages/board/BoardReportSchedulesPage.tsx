/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Modal } from "@/components/ui/Modal"
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { DestructiveActionDialog } from "@/components/dialogs/DestructiveActionDialog";
import { Plus, Edit2, Trash2, Clock, Loader2 } from "lucide-react";
import api from "../../api/api";
import toast from "react-hot-toast";
import { API_BASE } from '@/api/types'
import { useTranslation} from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface ReportSchedule {
  id: number;
  name: string;
  is_active: boolean;
  frequency: string;
  day_of_month?: number;
  day_of_week?: number;
  time_of_day?: string;
  template_id?: number;
  recipient_user_ids?: number[];
  recipient_emails?: string[];
  report_format: string;
  include_comparison: boolean;
  last_run_at?: string;
  next_run_at?: string;
  last_status?: string;
}

const frequencyLabels = {
  monthly: "Monthly",
  quarterly: "Quarterly",
  annually: "Annually",
};

export default function BoardReportSchedulesPage() {
  const { t } = useTranslation()
  const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const response = await api.get(`${API_BASE}/board/reports/schedules`);
      setSchedules(response);
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportSchedules.failedToLoadSchedules'));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchSchedules();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const deleteSchedule = (id: number) => {
    setPendingDeleteId(id);
    setShowDeleteConfirm(true);
  };

  const confirmDeleteSchedule = async () => {
    if (pendingDeleteId === null) return;
    try {
      setDeleting(pendingDeleteId);
      await api.delete(`${API_BASE}/board/reports/schedules/${pendingDeleteId}`);
      toast.success(t('toast.boardReportSchedules.scheduleDeleted'));
      fetchSchedules();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportSchedules.failedToDeleteSchedule'));
    } finally {
      setDeleting(null);
      setShowDeleteConfirm(false);
      setPendingDeleteId(null);
    }
  };

  const ordinal = (n: number): string => {
    if (n % 100 >= 11 && n % 100 <= 13) return n + 'th';
    switch (n % 10) {
      case 1: return n + 'st';
      case 2: return n + 'nd';
      case 3: return n + 'rd';
      default: return n + 'th';
    }
  };

  const formatScheduleDescription = (schedule: ReportSchedule): string => {
    let desc = `${frequencyLabels[schedule.frequency as keyof typeof frequencyLabels]}`;

    if (schedule.frequency === "monthly" && schedule.day_of_month) {
      desc += ` on the ${ordinal(schedule.day_of_month)}`;
    } else if (schedule.frequency === "quarterly" && schedule.day_of_month) {
      desc += ` on the ${ordinal(schedule.day_of_month)}`;
    }

    if (schedule.time_of_day) {
      desc += ` at ${schedule.time_of_day}`;
    }

    return desc;
  };

  if (loading) {
    return (
      <>
        <PageContainer className="py-8">
          <div className="motion-safe:animate-pulse space-y-4">
            <div className="h-8 bg-earth-200 dark:bg-earth-600 rounded w-1/3"></div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-earth-200 dark:bg-earth-600 rounded"></div>
              ))}
            </div>
          </div>
        </PageContainer>
      </>
    );
  }

  return (
    <>
      <PageContainer className="py-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Report Schedules
            </h1>
            <p className="text-earth-600 dark:text-earth-200 mt-2">
              Configure automatic board report generation on a recurring schedule.
            </p>
          </div>
          <button
            onClick={() => {
              setEditingId(null);
              setShowForm(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Schedule
          </button>
        </div>

        {/* Schedules List */}
        {schedules.length === 0 ? (
          <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg">
            <Clock className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">No schedules configured</p>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90"
            >
              Create First Schedule
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {schedules.map((schedule) => (
              <div
                key={schedule.id}
                className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                      {schedule.name}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {formatScheduleDescription(schedule)}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      schedule.is_active
                        ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900 dark:text-status-success-200"
                        : "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200"
                    }`}
                  >
                    {schedule.is_active ? "Active" : "Inactive"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  <div>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Format</p>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {schedule.report_format === "both"
                        ? "PowerPoint & PDF"
                        : schedule.report_format === "powerpoint"
                          ? "PowerPoint"
                          : "PDF"}
                    </p>
                  </div>
                  <div>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Recipients</p>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {(schedule.recipient_emails?.length || 0) +
                        (schedule.recipient_user_ids?.length || 0)}{" "}
                      member{(schedule.recipient_emails?.length || 0) + (schedule.recipient_user_ids?.length || 0) !== 1 ? "s" : ""}
                    </p>
                  </div>
                </div>

                {schedule.last_run_at && (
                  <div className="mb-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    Last run: {new Date(schedule.last_run_at).toLocaleDateString()}
                    {schedule.last_status && ` (${schedule.last_status})`}
                  </div>
                )}

                {schedule.next_run_at && (
                  <div className="mb-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    Next run: {new Date(schedule.next_run_at).toLocaleDateString()}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setEditingId(schedule.id);
                      setShowForm(true);
                    }}
                    aria-label={`Edit schedule: ${schedule.name}`}
                    className="flex items-center gap-1 px-3 py-2 text-sm bg-earth-500 text-white rounded hover:bg-lsc-rose transition-colors"
                  >
                    <Edit2 className="w-3 h-3" aria-hidden="true" />
                    Edit
                  </button>
                  <button
                    onClick={() => deleteSchedule(schedule.id)}
                    disabled={deleting === schedule.id}
                    aria-label={`Delete schedule: ${schedule.name}`}
                    className="flex items-center gap-1 px-3 py-2 text-sm bg-status-danger-500 text-white rounded hover:bg-status-danger-600 disabled:opacity-50 transition-colors"
                  >
                    {deleting === schedule.id ? (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    ) : (
                      <Trash2 className="w-3 h-3" />
                    )}
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Form Modal */}
        {showForm && (
          <ScheduleFormModal
            scheduleId={editingId}
            onClose={() => {
              setShowForm(false);
              setEditingId(null);
            }}
            onSuccess={() => {
              setShowForm(false);
              setEditingId(null);
              fetchSchedules();
            }}
          />
        )}

        <DestructiveActionDialog
          isOpen={showDeleteConfirm}
          title="Delete Schedule"
          message="Are you sure you want to delete this schedule? This action cannot be undone."
          isLoading={deleting !== null}
          onConfirm={confirmDeleteSchedule}
          onCancel={() => { setShowDeleteConfirm(false); setPendingDeleteId(null); }}
        />
      </PageContainer>
    </>
  );
}

interface ScheduleFormModalProps {
  scheduleId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}

function ScheduleFormModal({ scheduleId, onClose, onSuccess }: ScheduleFormModalProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    is_active: true,
    frequency: "monthly",
    day_of_month: 1,
    time_of_day: "09:00",
    recipient_emails: [] as string[],
    report_format: "both",
    include_comparison: true,
  });
  const [emailInput, setEmailInput] = useState("");

  const fetchSchedule = async () => {
    try {
      const response = await api.get(`${API_BASE}/board/reports/schedules/${scheduleId}`);
      setFormData({ ...response, recipient_emails: response.recipient_emails ?? [] });
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportSchedules.failedToLoadSchedule'));
    }
  };


  useEffect(() => {
    if (scheduleId) {
      fetchSchedule();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheduleId]);

  const addEmail = () => {
    const trimmed = emailInput.trim()
    if (!trimmed) return
    if (!trimmed.includes('@')) {
      toast.error('Please enter a valid email address')
      return
    }
    if (!formData.recipient_emails.includes(trimmed)) {
      setFormData({
        ...formData,
        recipient_emails: [...formData.recipient_emails, trimmed],
      });
      setEmailInput("");
    }
  };

  const removeEmail = (email: string) => {
    setFormData({
      ...formData,
      recipient_emails: formData.recipient_emails.filter((e) => e !== email),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);

      if (scheduleId) {
        await api.put(`${API_BASE}/board/reports/schedules/${scheduleId}`, formData);
        toast.success(t('toast.boardReportSchedules.scheduleUpdated'));
      } else {
        await api.post(`${API_BASE}/board/reports/schedules`, formData);
        toast.success(t('toast.boardReportSchedules.scheduleCreated'));
      }

      onSuccess();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportSchedules.failedToSaveSchedule'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={scheduleId ? "Edit Schedule" : "New Schedule"}
      size="md"
    >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="schedule-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Schedule Name *
              </label>
              <input
                id="schedule-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                required
                aria-required="true"
              />
            </div>

            <div>
              <label htmlFor="schedule-frequency" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Frequency *
              </label>
              <select
                id="schedule-frequency"
                value={formData.frequency}
                onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annually">Annually</option>
              </select>
            </div>

            {(formData.frequency === "monthly" || formData.frequency === "quarterly") && (
              <div>
                <label htmlFor="schedule-day" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Day of Month (1-31)
                </label>
                <input
                  id="schedule-day"
                  type="number"
                  min="1"
                  max="31"
                  value={formData.day_of_month}
                  onChange={(e) =>
                    setFormData({ ...formData, day_of_month: parseInt(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            )}

            <div>
              <label htmlFor="schedule-time" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Time of Day
              </label>
              <input
                id="schedule-time"
                type="time"
                value={formData.time_of_day}
                onChange={(e) => setFormData({ ...formData, time_of_day: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              />
            </div>

            <div>
              <label htmlFor="schedule-format" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Report Format
              </label>
              <select
                id="schedule-format"
                value={formData.report_format}
                onChange={(e) => setFormData({ ...formData, report_format: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="both">PowerPoint & PDF</option>
                <option value="powerpoint">PowerPoint Only</option>
                <option value="pdf">PDF Only</option>
              </select>
            </div>

            <div>
              <label htmlFor="schedule-email" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Recipient Emails
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  id="schedule-email"
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addEmail())}
                  className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.boardReportSchedules.enterEmailAddress')}
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
                {formData.recipient_emails.map((email) => (
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
                      ✕
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.include_comparison}
                onChange={(e) =>
                  setFormData({ ...formData, include_comparison: e.target.checked })
                }
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Include comparison to previous period
              </span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active</span>
            </label>

            <div className="flex gap-2 justify-end pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                {scheduleId ? "Update" : "Create"} Schedule
              </button>
            </div>
          </form>
    </Modal>
  );
}