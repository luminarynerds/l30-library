/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { AdminShell } from '../components/shells/AdminShell';
import { fairSchedulingApi } from '../api/fair-scheduling-api';
import { listStaff, type StaffMember } from '@/api/staff-api/staff-management';
import { useBranchOptions } from '@/hooks/useBranchOptions';
import { Brain, CheckCircle, HelpCircle, XCircle, Loader2, Search, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

interface LearnedPreference {
  id: number;
  staff_id: number;
  preference_category: string;
  preference_value: string;
  preference_strength: number;
  confidence: number;
  evidence: Record<string, unknown>[];
  sample_size: number;
  is_confirmed: boolean | null;
  confirmed_at: string | null;
  calculated_at: string;
}

function StrengthBar({ strength }: { strength: number }) {
  const pct = Math.round(strength * 100);
  const color =
    strength >= 0.7 ? 'bg-lsc-green' :
    strength >= 0.4 ? 'bg-status-warning-500' :
    'bg-status-danger-500';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-earth-200 dark:bg-earth-700">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums w-10 text-right">
        {pct}%
      </span>
    </div>
  );
}

function ConfirmedStatus({ value }: { value: boolean | null }) {
  if (value === true) {
    return <CheckCircle aria-label="Confirmed" className="w-5 h-5 text-lsc-green" />;
  }
  if (value === false) {
    return <XCircle aria-label="Denied" className="w-5 h-5 text-status-danger-500" />;
  }
  return <HelpCircle aria-label="Unconfirmed" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40" />;
}

export default function FairSchedulingPreferencesPage(): React.ReactElement {
  const { token } = useAuth();

  const [staffId, setStaffId] = useState<string>('');
  const [branchId, setBranchId] = useState<string>('');
  const [preferences, setPreferences] = useState<LearnedPreference[]>([]);
  const [loading, setLoading] = useState(false);
  const [learning, setLearning] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [staffOptions, setStaffOptions] = useState<StaffMember[]>([]);
  const [staffOptionsLoading, setStaffOptionsLoading] = useState(true);
  const { branches, loading: branchesLoading } = useBranchOptions();

  // NOTE: name source for the staff picker mirrors the timesheet editor's
  // role="staff" filter. Staff scheduled under non-"staff" roles (e.g. admin,
  // director, teacher) won't appear here -- there is no list-schedulable-staff
  // endpoint (GET /fair-scheduling/profiles is not implemented). See report.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setStaffOptionsLoading(true);
    (async () => {
      try {
        const first = await listStaff(token, 1, 100, { role: 'staff' });
        const pages = Math.max(1, Math.ceil((first.total || first.staff.length) / 100));
        const rest = pages > 1
          ? await Promise.all(
              Array.from({ length: pages - 1 }, (_, i) => listStaff(token, i + 2, 100, { role: 'staff' })),
            )
          : [];
        if (cancelled) return;
        const all = [first, ...rest].flatMap(r => r.staff).filter(s => s.is_active);
        setStaffOptions(all);
      } catch {
        if (!cancelled) toast.error('Failed to load staff list');
      } finally {
        if (!cancelled) setStaffOptionsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const loadPreferences = useCallback(async () => {
    const id = Number(staffId);
    if (!id || id <= 0) {
      toast.error('Enter a valid staff ID');
      return;
    }
    setLoading(true);
    try {
      const data = await fairSchedulingApi.getLearnedPreferences(id);
      setPreferences(Array.isArray(data) ? data : []);
      setLoaded(true);
    } catch {
      toast.error('Failed to load preferences');
    } finally {
      setLoading(false);
    }
  }, [staffId]);

  const runLearning = useCallback(async () => {
    setLearning(true);
    try {
      const payload: { branch_id?: number; staff_ids?: number[] } = {};
      const bid = Number(branchId);
      if (bid > 0) payload.branch_id = bid;
      const sid = Number(staffId);
      if (sid > 0) payload.staff_ids = [sid];
      await fairSchedulingApi.learnPreferences(payload);
      toast.success('Preference learning complete');
      if (sid > 0) {
        const data = await fairSchedulingApi.getLearnedPreferences(sid);
        setPreferences(Array.isArray(data) ? data : []);
        setLoaded(true);
      }
    } catch {
      toast.error('Preference learning failed');
    } finally {
      setLearning(false);
    }
  }, [branchId, staffId]);

  const confirmPreference = useCallback(async (preferenceId: number) => {
    setConfirmingId(preferenceId);
    try {
      await fairSchedulingApi.confirmPreference(preferenceId);
      setPreferences(prev =>
        prev.map(p =>
          p.id === preferenceId
            ? { ...p, is_confirmed: true, confirmed_at: new Date().toISOString() }
            : p
        )
      );
      toast.success('Preference confirmed');
    } catch {
      toast.error('Failed to confirm preference');
    } finally {
      setConfirmingId(null);
    }
  }, []);

  return (
    <AdminShell title="Preference Learning" subtitle="View and manage learned staff preferences">
      <div className="space-y-6">
        {/* Staff selector */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label
                htmlFor="staff-id"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                Staff member
              </label>
              <select
                id="staff-id"
                value={staffId}
                onChange={e => setStaffId(e.target.value)}
                disabled={staffOptionsLoading}
                className="w-64 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
              >
                <option value="">{staffOptionsLoading ? 'Loading staff...' : 'Select a staff member'}</option>
                {staffOptions.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.first_name} {s.last_name} ({s.email})
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={loadPreferences}
              disabled={loading}
              className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Load Preferences
            </button>
          </div>
        </div>

        {/* Trigger learning */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <Brain className="w-5 h-5 text-lsc-rose" />
            Run Preference Learning
          </h2>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label
                htmlFor="branch-id"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                Branch ID (optional)
              </label>
              <select
                id="branch-id"
                value={branchId}
                onChange={e => setBranchId(e.target.value)}
                disabled={branchesLoading}
                className="w-56 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
              >
                <option value="">All branches</option>
                {branches.map(b => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={runLearning}
              disabled={learning}
              className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              {learning ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              {learning ? 'Learning...' : 'Run Preference Learning'}
            </button>
          </div>
        </div>

        {/* Empty state */}
        {loaded && preferences.length === 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 text-center">
            <Brain className="w-10 h-10 mx-auto text-lsc-dark/30 dark:text-lsc-cream/30 mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              No preferences learned yet for this staff member. Try running preference learning.
            </p>
          </div>
        )}

        {/* Preference cards */}
        {preferences.length > 0 && (
          <div className="space-y-4">
            {preferences.map(pref => (
              <div
                key={pref.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
              >
                <div className="flex items-start justify-between gap-4 mb-4">
                  <h3 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream">
                    {pref.preference_category}: {pref.preference_value}
                  </h3>
                  <div className="flex items-center gap-2 shrink-0">
                    <ConfirmedStatus value={pref.is_confirmed} />
                    {pref.is_confirmed === null && (
                      <button
                        onClick={() => confirmPreference(pref.id)}
                        disabled={confirmingId === pref.id}
                        className="inline-flex items-center gap-1 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
                      >
                        {confirmingId === pref.id ? (
                          <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                        ) : (
                          <CheckCircle className="w-3.5 h-3.5" />
                        )}
                        Confirm
                      </button>
                    )}
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">
                      Strength
                    </span>
                    <StrengthBar strength={pref.preference_strength} />
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        Confidence
                      </span>
                      <span className="text-lsc-dark dark:text-lsc-cream font-medium">
                        {Math.round(pref.confidence * 100)}%
                      </span>
                    </div>
                    <div>
                      <span className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        Sample Size
                      </span>
                      <span className="text-lsc-dark dark:text-lsc-cream font-medium">
                        {pref.sample_size}
                      </span>
                    </div>
                    <div>
                      <span className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        Calculated
                      </span>
                      <span className="text-lsc-dark dark:text-lsc-cream font-medium">
                        {new Date(pref.calculated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminShell>
  );
}
