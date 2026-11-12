/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Modal } from "@/components/ui/Modal"
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { DestructiveActionDialog } from "@/components/dialogs/DestructiveActionDialog";
import { Plus, Edit2, Trash2, Star, Loader2 } from "lucide-react";
import api from "../../api/api";
import toast from "react-hot-toast";
import { API_BASE } from '@/api/types'
import { useTranslation} from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface ReportTemplate {
  id: number;
  name: string;
  description?: string;
  is_default: boolean;
  is_active: boolean;
  include_sections: Record<string, boolean>;
  colors?: Record<string, string>;
  created_at: string;
  updated_at?: string;
}

export default function BoardReportTemplatesPage() {
  const { t } = useTranslation()
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const response = await api.get(`${API_BASE}/board/reports/templates?active_only=false`);
      setTemplates(response);
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportTemplates.failedToLoadTemplates'));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchTemplates();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const deleteTemplate = (id: number) => {
    setPendingDeleteId(id);
    setShowDeleteConfirm(true);
  };

  const confirmDeleteTemplate = async () => {
    if (pendingDeleteId === null) return;
    try {
      setDeleting(pendingDeleteId);
      await api.delete(`${API_BASE}/board/reports/templates/${pendingDeleteId}`);
      toast.success(t('toast.boardReports.templateDeleted'));
      fetchTemplates();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportTemplates.failedToDeleteTemplate'));
    } finally {
      setDeleting(null);
      setShowDeleteConfirm(false);
      setPendingDeleteId(null);
    }
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
          <div><h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Report Templates</h1></div>
          <button
            onClick={() => {
              setEditingId(null);
              setShowForm(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Template
          </button>
        </div>

        {/* Templates Grid */}
        {templates.length === 0 ? (
          <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('boardReportTemplates.noTemplatesCreatedYet')}</p>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90"
            >
              Create First Template
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {templates.map((template) => (
              <div
                key={template.id}
                className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                      {template.name}
                    </h3>
                    {template.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {template.description}
                      </p>
                    )}
                  </div>
                  {template.is_default && (
                    <Star className="w-5 h-5 text-status-warning-500 fill-current ml-2" />
                  )}
                </div>

                {/* Sections */}
                <div className="mb-4">
                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Included Sections:
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(template.include_sections).map(
                      ([section, included]) =>
                        included && (
                          <span
                            key={section}
                            className="px-2 py-1 bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-lsc-rose-light/80 rounded text-xs"
                          >
                            {section.charAt(0).toUpperCase() + section.slice(1)}
                          </span>
                        )
                    )}
                  </div>
                </div>

                {/* Status */}
                <div className="mb-4 flex gap-2">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      template.is_active
                        ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900 dark:text-status-success-200"
                        : "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200"
                    }`}
                  >
                    {template.is_active ? "Active" : "Inactive"}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setEditingId(template.id);
                      setShowForm(true);
                    }}
                    aria-label={`Edit template: ${template.name}`}
                    className="flex items-center gap-1 px-3 py-2 text-sm bg-earth-500 text-white rounded hover:bg-lsc-rose transition-colors"
                  >
                    <Edit2 className="w-3 h-3" aria-hidden="true" />
                    Edit
                  </button>
                  <button
                    onClick={() => deleteTemplate(template.id)}
                    disabled={deleting === template.id}
                    aria-label={`Delete template: ${template.name}`}
                    className="flex items-center gap-1 px-3 py-2 text-sm bg-status-danger-500 text-white rounded hover:bg-status-danger-600 disabled:opacity-50 transition-colors"
                  >
                    {deleting === template.id ? (
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
          <TemplateFormModal
            templateId={editingId}
            onClose={() => {
              setShowForm(false);
              setEditingId(null);
            }}
            onSuccess={() => {
              setShowForm(false);
              setEditingId(null);
              fetchTemplates();
            }}
          />
        )}

        <DestructiveActionDialog
          isOpen={showDeleteConfirm}
          title="Delete Template"
          message="Are you sure you want to delete this template? This action cannot be undone."
          isLoading={deleting !== null}
          onConfirm={confirmDeleteTemplate}
          onCancel={() => { setShowDeleteConfirm(false); setPendingDeleteId(null); }}
        />
      </PageContainer>
    </>
  );
}

interface TemplateFormModalProps {
  templateId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}

function TemplateFormModal({ templateId, onClose, onSuccess }: TemplateFormModalProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    is_active: true,
    include_sections: {
      circulation: true,
      financial: true,
      patrons: true,
      collection: true,
    },
  });

  const fetchTemplate = async () => {
    try {
      const response = await api.get(`${API_BASE}/board/reports/templates/${templateId}`);
      setFormData(response);
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportTemplates.failedToLoadTemplate'));
    }
  };


  useEffect(() => {
    if (templateId) {
      fetchTemplate();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);

      if (templateId) {
        await api.put(`${API_BASE}/board/reports/templates/${templateId}`, formData);
        toast.success(t('toast.boardReports.templateUpdated'));
      } else {
        await api.post(`${API_BASE}/board/reports/templates`, formData);
        toast.success(t('toast.boardReports.templateCreated'));
      }

      onSuccess();
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      toast.error(t('boardReportTemplates.failedToSaveTemplate'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={templateId ? "Edit Template" : "New Template"}
      size="md"
    >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="template-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Template Name *
              </label>
              <input
                id="template-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                required
                aria-required="true"
              />
            </div>

            <div>
              <label htmlFor="template-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Description
              </label>
              <textarea
                id="template-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                rows={3}
              />
            </div>

            <div>
              <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Report Sections
              </p>
              <div className="space-y-2">
                {Object.entries(formData.include_sections).map(([section, included]) => (
                  <label key={section} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={included}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          include_sections: {
                            ...formData.include_sections,
                            [section]: e.target.checked,
                          },
                        })
                      }
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {section.charAt(0).toUpperCase() + section.slice(1)}
                    </span>
                  </label>
                ))}
              </div>
            </div>

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
                {templateId ? "Update" : "Create"} Template
              </button>
            </div>
          </form>
    </Modal>
  );
}