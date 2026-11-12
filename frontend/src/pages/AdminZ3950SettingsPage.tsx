/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import {
  Database,
  Plus,
  Pencil,
  Trash2,
  Zap,
  Check,
  X,
  Loader2,
  Server,
  Download,
  Info,
} from 'lucide-react';
import { AdminShell } from '../components/shells/AdminShell'
import ConfirmDialog from '../components/ConfirmDialog'
import z3950AdminApi, {
  type Z3950Source,
  type Z3950SourceCreate,
  type Z3950SourceUpdate,
} from '../api/z3950-admin-api';
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

const EMPTY_FORM: Z3950SourceCreate = {
  name: '',
  host: '',
  port: 210,
  database_name: '',
  syntax: 'USMARC',
  encoding: 'UTF-8',
  sru_url: '',
  requires_auth: false,
  username: '',
  password: '',
  is_enabled: true,
  display_order: 0,
  notes: '',
};

export default function AdminZ3950SettingsPage() {
  const { t } = useTranslation()
  const [sources, setSources] = useState<Z3950Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<Z3950SourceCreate>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const fetchSources = useCallback(async () => {
    try {
      const data = await z3950AdminApi.list();
      setSources(data);
    } catch {
      toast.error(t('admin.adminZ3950Settings.failedToLoadZSources'));
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const openAddModal = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  };

  const openEditModal = (source: Z3950Source) => {
    setEditingId(source.id);
    setForm({
      name: source.name,
      host: source.host,
      port: source.port,
      database_name: source.database_name,
      syntax: source.syntax,
      encoding: source.encoding,
      sru_url: source.sru_url || '',
      requires_auth: source.requires_auth,
      username: source.username || '',
      password: '',
      is_enabled: source.is_enabled,
      display_order: source.display_order,
      notes: source.notes || '',
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.name || !form.host || !form.database_name) {
      toast.error(t('admin.adminZ3950Settings.nameHostAndDatabaseAre'));
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form };
      // Don't send empty password on edit (preserves existing)
      if (editingId && !payload.password) {
        delete (payload as Z3950SourceUpdate).password;
      }
      if (editingId) {
        await z3950AdminApi.update(editingId, payload);
        toast.success(t('toast.adminZ3950Settings.sourceUpdated'));
      } else {
        await z3950AdminApi.create(payload);
        toast.success(t('toast.adminZ3950Settings.sourceCreated'));
      }
      setModalOpen(false);
      fetchSources();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.adminZ3950Settings.failedToSaveSource'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    setIsDeleting(true);
    try {
      await z3950AdminApi.delete(id);
      toast.success(t('toast.adminZ3950Settings.sourceDeleted'));
      fetchSources();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.adminZ3950Settings.failedToDeleteSource'));
    } finally {
      setIsDeleting(false);
      setDeleteConfirmId(null);
    }
  };

  const handleTest = async (id: number) => {
    setTestingId(id);
    try {
      const result = await z3950AdminApi.test(id);
      if (result.success) {
        toast.success(`${result.message}${result.response_time_ms ? ` (${result.response_time_ms}ms)` : ''}`);
      } else {
        toast.error(result.message);
      }
      fetchSources();
    } catch {
      toast.error(t('toast.adminZ3950Settings.testRequestFailed'));
    } finally {
      setTestingId(null);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await z3950AdminApi.seed();
      toast.success(t('admin.adminZ3950Settings.defaultSourcesLocOclcAdded'));
      fetchSources();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.adminZ3950Settings.failedToSeedDefaults'));
    } finally {
      setSeeding(false);
    }
  };

  const handleToggleEnabled = async (source: Z3950Source) => {
    try {
      await z3950AdminApi.update(source.id, { is_enabled: !source.is_enabled });
      fetchSources();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.adminZ3950Settings.failedToToggleSource'));
    }
  };

  const updateField = (field: string, value: string | number | boolean | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <AdminShell title="Z39.50 Sources">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell title="Z39.50 Sources">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-lsc-rose" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Z39.50 Sources
            </h1>
          </div>
          <button
            onClick={openAddModal}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Source
          </button>
        </div>

        {/* Info banner */}
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 flex gap-3">
          <Info className="w-5 h-5 text-status-warning-700 dark:text-status-warning-300 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-warning-800 dark:text-status-warning-200">
            Configure Z39.50/SRU sources for catalog record imports. These sources are used when
            searching for MARC records to copy-catalog into your collection.
          </p>
        </div>

        {/* Empty state */}
        {sources.length === 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-12 text-center">
            <Server className="w-12 h-12 text-earth-600 mx-auto mb-4" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              No Z39.50 Sources Configured
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              Get started by seeding the default Library of Congress and OCLC WorldCat sources.
            </p>
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
            >
              {seeding ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}
              Seed Default Sources
            </button>
          </div>
        )}

        {/* Source cards */}
        <div className="space-y-4">
          {sources.map((source) => (
            <div
              key={source.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                      {source.name}
                    </h3>
                    {source.is_enabled ? (
                      <span className="px-2 py-0.5 text-xs font-medium bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300 rounded-full">
                        Enabled
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-xs font-medium bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300 rounded-full">
                        Disabled
                      </span>
                    )}
                    {source.last_test_success === true && (
                      <Check className="w-4 h-4 text-status-success-600" />
                    )}
                    {source.last_test_success === false && (
                      <X className="w-4 h-4 text-status-danger-500" />
                    )}
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">
                    {source.host}:{source.port}/{source.database_name}
                  </p>
                  {source.sru_url && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 truncate max-w-lg">
                      SRU: {source.sru_url}
                    </p>
                  )}
                  {source.last_tested_at && (
                    <p className="text-xs text-earth-600 mt-1">
                      Last tested: {new Date(source.last_tested_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {/* Toggle */}
                  <button
                    role="switch" aria-checked={source.is_enabled} aria-label={`${source.name} enabled`} onClick={() => handleToggleEnabled(source)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      source.is_enabled ? 'bg-status-success-500' : 'bg-earth-300 dark:bg-earth-600'
                    }`}
                    title={source.is_enabled ? 'Disable' : 'Enable'}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white transition-transform ${
                        source.is_enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  {/* Test */}
                  <button
                    onClick={() => handleTest(source.id)}
                    disabled={testingId === source.id}
                    className="p-2 text-earth-600 hover:text-lsc-rose hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50"
                    title="Test Connection"
                  >
                    {testingId === source.id ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <Zap className="w-4 h-4" />
                    )}
                  </button>
                  {/* Edit */}
                  <button
                    onClick={() => openEditModal(source)}
                    className="p-2 text-earth-600 hover:text-lsc-rose hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  {/* Delete */}
                  <button
                    onClick={() => setDeleteConfirmId(source.id)}
                    className="p-2 text-earth-600 hover:text-status-danger-600 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <ConfirmDialog
        isOpen={deleteConfirmId !== null}
        title="Delete this Z39.50 source?"
        message="This will permanently remove this source configuration. This action cannot be undone."
        confirmText="Yes, delete it"
        cancelText="Keep it"
        confirmVariant="danger"
        onConfirm={() => { if (deleteConfirmId !== null) handleDelete(deleteConfirmId); }}
        onCancel={() => setDeleteConfirmId(null)}
        loading={isDeleting}
      />

      {/* Modal */}
      {modalOpen && (
        <ModalBackdrop onClose={() => setModalOpen(false)} title={editingId ? "Edit Source" : "Add Z39.50 Source"}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-lsc-border dark:border-earth-700">
              <h2 id="z3950-modal-title" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {editingId ? 'Edit Source' : 'Add Z39.50 Source'}
              </h2>
            </div>
            <div className="p-6 space-y-4">
              {/* Name */}
              <div>
                <label htmlFor="z3950-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Name *
                </label>
                <input
                  id="z3950-name"
                  type="text"
                  value={form.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  placeholder={t('placeholder.adminZ3950Settings.egLibraryOfCongress')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              {/* Host + Port */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label htmlFor="z3950-host" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Host *
                  </label>
                  <input
                    id="z3950-host"
                    type="text"
                    value={form.host}
                    onChange={(e) => updateField('host', e.target.value)}
                    placeholder={t('placeholder.adminZ3950Settings.lx2locgov')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
                <div>
                  <label htmlFor="z3950-port" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Port
                  </label>
                  <input
                    id="z3950-port"
                    type="number"
                    value={form.port}
                    onChange={(e) => updateField('port', parseInt(e.target.value) || 210)}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              </div>
              {/* Database */}
              <div>
                <label htmlFor="z3950-database-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Database Name *
                </label>
                <input
                  id="z3950-database-name"
                  type="text"
                  value={form.database_name}
                  onChange={(e) => updateField('database_name', e.target.value)}
                  placeholder={t('placeholder.adminZ3950Settings.lcdb')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              {/* Syntax + Encoding */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="z3950-syntax" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Record Syntax
                  </label>
                  <select
                    id="z3950-syntax"
                    value={form.syntax}
                    onChange={(e) => updateField('syntax', e.target.value)}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    <option value="USMARC">USMARC</option>
                    <option value="MARC21">MARC21</option>
                    <option value="UNIMARC">UNIMARC</option>
                    <option value="XML">XML</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="z3950-encoding" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Encoding
                  </label>
                  <select
                    id="z3950-encoding"
                    value={form.encoding}
                    onChange={(e) => updateField('encoding', e.target.value)}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    <option value="UTF-8">UTF-8</option>
                    <option value="MARC-8">MARC-8</option>
                    <option value="ISO-8859-1">ISO-8859-1</option>
                  </select>
                </div>
              </div>
              {/* SRU URL */}
              <div>
                <label htmlFor="z3950-sru-url" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  SRU URL
                </label>
                <input
                  id="z3950-sru-url"
                  type="text"
                  value={form.sru_url || ''}
                  onChange={(e) => updateField('sru_url', e.target.value || null)}
                  placeholder={t('placeholder.adminZ3950Settings.httpslx2locgovsrulcdb')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              {/* Auth */}
              <div className="flex items-center gap-3">
                <input
                  id="z3950-requires-auth"
                  type="checkbox"
                  checked={form.requires_auth}
                  onChange={(e) => updateField('requires_auth', e.target.checked)}
                  className="w-4 h-4 text-lsc-rose rounded border-lsc-border focus:ring-lsc-rose"
                />
                <label htmlFor="z3950-requires-auth" className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Requires Authentication
                </label>
              </div>
              {form.requires_auth && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="z3950-username" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Username
                    </label>
                    <input
                      id="z3950-username"
                      type="text"
                      value={form.username || ''}
                      onChange={(e) => updateField('username', e.target.value)}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label htmlFor="z3950-password" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Password {editingId && '(leave blank to keep existing)'}
                    </label>
                    <input
                      id="z3950-password"
                      type="password"
                      value={form.password || ''}
                      onChange={(e) => updateField('password', e.target.value)}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>
                </div>
              )}
              {/* Notes */}
              <div>
                <label htmlFor="z3950-notes" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Notes
                </label>
                <textarea
                  id="z3950-notes"
                  value={form.notes || ''}
                  onChange={(e) => updateField('notes', e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
            </div>
            {/* Footer */}
            <div className="p-6 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
              >
                {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                {editingId ? 'Save Changes' : 'Add Source'}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  );
}
