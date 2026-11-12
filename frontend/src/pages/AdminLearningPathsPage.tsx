/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { Plus, Edit, Trash2, Loader2, Route } from "lucide-react";
import api from "../api/api";
import ConfirmDialog from "../components/ConfirmDialog";
import { AdminShell } from '../components/shells';
import { useTranslation} from '@/i18n'

export default function AdminLearningPathsPage() {
  const { t } = useTranslation()
  const [paths, setPaths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; title: string } | null>(null);

  const fetchPaths = async () => {
    try {
      setLoading(true);
      const response = await api.get("/learning-paths");
      setPaths(response.data || response);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchPaths();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/learning-paths/${id}`);
      setDeleteConfirm(null);
      toast.success(t('toast.adminLearningPaths.learningPathDeleted'));
      fetchPaths();
    } catch (err: unknown) {
      const errorMessage = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      toast.error(errorMessage || t('toast.adminLearningPaths.failedToDeleteLearningPath'));
    }
  };

  return (
    <AdminShell
      title="Manage Learning Paths"
      icon={<Route className="w-8 h-8" />}
      actions={
        <Link
          to="/staff/admin/learning-paths/new"
          className="bg-lsc-rose text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-lsc-rose/90"
        >
          <Plus className="w-5 h-5" />
          Create Path
        </Link>
      }
    >
      {loading ? (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin mx-auto text-lsc-rose" />
        </div>
      ) : paths.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminLearningPaths.noLearningPathsYet')}</div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 shadow-md rounded-lg overflow-hidden border border-lsc-border dark:border-earth-700">
          <table className="w-full divide-y divide-lsc-border dark:divide-earth-700">
            <thead className="bg-lsc-cream dark:bg-earth-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Public</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Courses</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-lsc-white dark:bg-earth-800 divide-y divide-lsc-border dark:divide-earth-700">
              {paths.map((path: { id: number; title: string; status: string; is_public: boolean; total_courses?: number }) => (
                <tr key={path.id} className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-lsc-dark dark:text-lsc-cream">{path.title}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{path.status}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{path.is_public ? "Yes" : "No"}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{path.total_courses || 0}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <Link
                      to={`/staff/admin/learning-paths/${path.id}/edit`}
                      className="text-lsc-rose hover:text-lsc-rose/80 mr-4"
                      aria-label={`Edit learning path ${path.title}`}
                    >
                      <Edit className="w-5 h-5 inline" aria-hidden="true" />
                    </Link>
                    <button
                      onClick={() => setDeleteConfirm({ id: path.id, title: path.title })}
                      className="text-status-danger-600 hover:text-status-danger-700 dark:text-status-danger-400 dark:hover:text-status-danger-300"
                      aria-label={`Delete learning path ${path.title}`}
                    >
                      <Trash2 className="w-5 h-5 inline" aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Learning Path?"
        message={`Are you sure you want to delete "${deleteConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteConfirm) handleDelete(deleteConfirm.id) }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </AdminShell>
  );
}
