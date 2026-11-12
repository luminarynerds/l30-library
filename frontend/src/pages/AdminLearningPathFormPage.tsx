/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../api/api";
import { Save, Route } from "lucide-react";
import { AdminShell } from '../components/shells';
import { t } from '@/i18n'

export default function AdminLearningPathFormPage() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id && id !== "new");

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    status: "draft",
    is_public: false,
    difficulty: "beginner",
    estimated_hours: "",
    tags: "",
    enforce_prerequisites: true,
  });

  const [saving, setSaving] = useState(false);

  const fetchPath = async () => {
    try {
      const response = await api.get(`/learning-paths/${id}`);
      const data = response.data || response;
      setFormData({
        title: data.title,
        description: data.description || "",
        status: data.status,
        is_public: data.is_public,
        difficulty: data.difficulty || "beginner",
        estimated_hours: data.estimated_hours?.toString() || "",
        tags: data.tags?.join(", ") || "",
        enforce_prerequisites: data.enforce_prerequisites,
      });
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    }
  };


  useEffect(() => {
    if (isEdit) {
      fetchPath();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      ...formData,
      estimated_hours: formData.estimated_hours ? parseInt(formData.estimated_hours) : null,
      tags: formData.tags ? formData.tags.split(",").map((t) => t.trim()) : [],
    };

    try {
      if (isEdit) {
        await api.put(`/learning-paths/${id}`, payload);
      } else {
        await api.post("/learning-paths", { ...payload, courses: [] });
      }
      navigate("/staff/admin/learning-paths");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.saveFailed'));
      setSaving(false);
    }
  };

  return (
    <AdminShell
      title={`${isEdit ? "Edit" : "Create"} Learning Path`}
      icon={<Route className="w-8 h-8" />}
      maxWidth="max-w-3xl"
    >
      <form onSubmit={handleSubmit} className="bg-lsc-white dark:bg-earth-800 shadow-md rounded-lg p-8 space-y-6 border border-lsc-border dark:border-earth-700">
        <div>
          <label htmlFor="learning-path-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Title *</label>
          <input
            id="learning-path-title"
            type="text"
            required
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>

        <div>
          <label htmlFor="learning-path-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Description</label>
          <textarea
            id="learning-path-description"
            rows={4}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="learning-path-status" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Status</label>
            <select
              id="learning-path-status"
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div>
            <label htmlFor="learning-path-difficulty" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Difficulty</label>
            <select
              id="learning-path-difficulty"
              value={formData.difficulty}
              onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
              className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="learning-path-hours" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Estimated Hours</label>
            <input
              id="learning-path-hours"
              type="number"
              value={formData.estimated_hours}
              onChange={(e) => setFormData({ ...formData, estimated_hours: e.target.value })}
              className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>

          <div className="flex items-center gap-4 mt-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_public}
                onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
                className="w-5 h-5 rounded border-lsc-border"
              />
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Public</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.enforce_prerequisites}
                onChange={(e) => setFormData({ ...formData, enforce_prerequisites: e.target.checked })}
                className="w-5 h-5 rounded border-lsc-border"
              />
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Enforce Prerequisites</span>
            </label>
          </div>
        </div>

        <div>
          <label htmlFor="learning-path-tags" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Tags (comma-separated)</label>
          <input
            id="learning-path-tags"
            type="text"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
            placeholder={t('placeholder.adminLearningPathForm.gettingstartedExplorethecatalogLearnatyourpace')}
            className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 bg-lsc-rose text-white px-6 py-3 rounded-lg font-semibold hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Save className="w-5 h-5" />
            {saving ? "Saving..." : "Save Path"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/staff/admin/learning-paths")}
            className="px-6 py-3 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
          >
            Cancel
          </button>
        </div>
      </form>
    </AdminShell>
  );
}
