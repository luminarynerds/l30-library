/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { AdminShell } from '../components/shells/AdminShell'
import { API_BASE } from '@/api/types';
import {
  Target, TrendingUp, Users, Building2, CheckCircle2,
  Clock, Award, ChevronRight, BarChart3, Lightbulb
} from "lucide-react";
import api from "../api/api";
import toast from "react-hot-toast";
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Goal {
  id: number;
  title: string;
  description?: string;
  category?: string;
  department?: string;
  progress: number;
  status: string;
  can_update: boolean;
  target_date?: string;
  metrics?: { name: string; current: number; target: number; unit?: string }[];
}

interface StaffGoalsData {
  has_plan: boolean;
  plan_title?: string;
  mission?: string;
  goals: Goal[];
}

const statusColors: Record<string, string> = {
  not_started: "bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300",
  on_track: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300",
  in_progress: "bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300",
  at_risk: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  delayed: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  completed: "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light",
};

const statusLabels: Record<string, string> = {
  not_started: "Not Started",
  on_track: "On Track",
  in_progress: "In Progress",
  at_risk: "At Risk",
  delayed: "Delayed",
  completed: "Completed",
};

const departmentColors: Record<string, string> = {
  "Youth Services": "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300",
  "Adult Services": "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light",
  "Technical Services": "bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300",
  "Circulation": "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300",
  "Administration": "bg-lsc-cream text-lsc-rose dark:bg-lsc-dark/30 dark:text-lsc-rose-light",
  "Outreach": "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
  default: "bg-lsc-cream text-lsc-dark dark:bg-lsc-brown dark:text-lsc-cream/80",
};

export default function StaffStrategicPage() {
  const { t } = useTranslation()
  const { user } = useAuth();
  const isStaff = user && ["staff", "admin", "super_admin"].includes(user.role);

  const [data, setData] = useState<StaffGoalsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateForm, setUpdateForm] = useState({ progress: 0, note: "" });
  const [submitting, setSubmitting] = useState(false);

  const fetchGoals = async () => {
    setLoading(true);
    try {
      const res = await api.get(`${API_BASE}/strategic/staff/my-goals`);
      setData(res);
    } catch (_err) {
      toast.error(t('staffStrategic.failedToLoadStrategicGoals'));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    if (isStaff) {
      fetchGoals();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStaff]);

  const openUpdateModal = (goal: Goal) => {
    setSelectedGoal(goal);
    setUpdateForm({ progress: goal.progress, note: "" });
    setShowUpdateModal(true);
  };

  const submitUpdate = async () => {
    if (!selectedGoal) return;
    setSubmitting(true);
    try {
      await api.post(`${API_BASE}/strategic/goals/${selectedGoal.id}/progress`, {
        progress: updateForm.progress,
        note: updateForm.note,
      });
      toast.success(t('staffStrategic.progressUpdatedThankYouFor'));
      setShowUpdateModal(false);
      fetchGoals();
    } catch (_err) {
      toast.error(t('staffStrategic.failedToSubmitUpdate'));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isStaff) {
    return (
      <AdminShell title="Strategic Planning">
            <div className="py-8 px-4 text-center">
              <Users className="h-16 w-16 text-lsc-border mx-auto mb-4" />
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff Access Required</h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                This page is available to library staff members.
              </p>
            </div>
      </AdminShell>
    );
  }

  if (loading) {
    return (
      <AdminShell title="Strategic Planning">
            <div className="py-8 px-4">
              <div className="motion-safe:animate-pulse space-y-4">
                <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
                <div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
              </div>
            </div>
      </AdminShell>
    );
  }

  if (!data?.has_plan) {
    return (
      <AdminShell title="Strategic Planning">
            <div className="py-8 px-4 text-center">
              <Target className="h-16 w-16 text-lsc-border mx-auto mb-4" />
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Strategic Goals</h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                No active strategic plan is currently in place.
              </p>
            </div>
      </AdminShell>
    );
  }

  // Group goals by department
  const myGoals = data.goals.filter(g => g.can_update);
  const otherGoals = data.goals.filter(g => !g.can_update);
  const departments = [...new Set(data.goals.map(g => g.department).filter(Boolean))];

  // Calculate stats
  const totalProgress = data.goals.length > 0
    ? Math.round(data.goals.reduce((sum, g) => sum + g.progress, 0) / data.goals.length)
    : 0;
  const completedGoals = data.goals.filter(g => g.status === "completed").length;

  return (
    <AdminShell title="Strategic Planning">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <Target className="h-7 w-7 text-lsc-rose" />
          My Goals
        </h1>
        {data.plan_title && (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {data.plan_title}
          </p>
        )}
      </div>

      {/* Mission Reminder */}
      {data.mission && (
        <div className="bg-gradient-to-r from-status-warning-50 to-cream-100 dark:from-lsc-dark/20 dark:to-earth-800 rounded-xl p-6 mb-8 border border-earth-100 dark:border-earth-900/30">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-lsc-rose rounded-xl flex items-center justify-center shrink-0">
              <Lightbulb className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Our Mission</h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{data.mission}</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-dark/30 rounded-xl flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{totalProgress}%</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overall Progress</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-status-success-100 dark:bg-status-success-900/30 rounded-xl flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-status-success-600 dark:text-status-success-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{completedGoals}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Completed</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-earth-100 dark:bg-earth-800/30 rounded-xl flex items-center justify-center">
              <Target className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{data.goals.length}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Goals</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-category-100 dark:bg-category-900/30 rounded-xl flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-category-600 dark:text-category-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{myGoals.length}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">You Can Update</p>
            </div>
          </div>
        </div>
      </div>

      {/* Goals I Can Update */}
      {myGoals.length > 0 && (
        <div className="mb-8">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-status-success-600" />
            Goals You Can Contribute To
          </h2>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
            {myGoals.map((goal) => (
              <div key={goal.id} className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {goal.title}
                      </h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[goal.status]}`}>
                        {statusLabels[goal.status]}
                      </span>
                      {goal.department && (
                        <span className={`px-2 py-0.5 rounded text-xs ${departmentColors[goal.department] || departmentColors.default}`}>
                          {goal.department}
                        </span>
                      )}
                    </div>

                    {goal.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                        {goal.description}
                      </p>
                    )}

                    {/* Progress */}
                    <div className="mb-3">
                      <div className="flex justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <span>Progress</span>
                        <span>{goal.progress}%</span>
                      </div>
                      <div className="h-2.5 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            goal.progress >= 100
                              ? "bg-earth-500"
                              : goal.progress >= 75
                              ? "bg-status-success-500"
                              : goal.progress >= 50
                              ? "bg-lsc-rose"
                              : "bg-earth-400"
                          }`}
                          style={{ width: `${goal.progress}%` }}
                        />
                      </div>
                    </div>

                    {/* Metrics */}
                    {goal.metrics && goal.metrics.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-3">
                        {goal.metrics.slice(0, 2).map((metric, i) => (
                          <div
                            key={i}
                            className="px-3 py-1.5 bg-lsc-cream dark:bg-lsc-brown rounded-xl text-sm"
                          >
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{metric.name}:</span>{" "}
                            <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {metric.current}/{metric.target} {metric.unit}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {goal.target_date && (
                      <div className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <Clock className="h-4 w-4" />
                        Target: {new Date(goal.target_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => openUpdateModal(goal)}
                    className="flex items-center gap-2 px-4 py-2 bg-status-success-600 text-white rounded-xl hover:bg-status-success-700 transition-colors shrink-0"
                  >
                    <TrendingUp className="h-4 w-4" />
                    Update
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Other Strategic Goals */}
      {otherGoals.length > 0 && (
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Building2 className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            Other Library Goals
          </h2>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
            {otherGoals.map((goal) => (
              <div key={goal.id} className="p-5">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {goal.title}
                      </h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[goal.status]}`}>
                        {statusLabels[goal.status]}
                      </span>
                      {goal.category && (
                        <span className="px-2 py-0.5 rounded text-xs bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70">
                          {goal.category}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                        <div
                          className="h-full bg-lsc-rose"
                          style={{ width: `${goal.progress}%` }}
                        />
                      </div>
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-12">
                        {goal.progress}%
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Departments Overview */}
      {departments.length > 0 && (
        <div className="mt-8 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Departments Contributing
          </h3>
          <div className="flex flex-wrap gap-2">
            {departments.map((dept) => {
              const count = data.goals.filter(g => g.department === dept).length;
              return (
                <span
                  key={dept}
                  className={`px-4 py-2 rounded-xl text-sm font-medium ${
                    departmentColors[dept || ""] || departmentColors.default
                  }`}
                >
                  {dept} ({count} {count === 1 ? "goal" : "goals"})
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Progress Update Modal */}
      {showUpdateModal && selectedGoal && (
        <ModalBackdrop onClose={() => setShowUpdateModal(false)} title="Update Progress">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-status-success-100 dark:bg-status-success-900/30 rounded-xl flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-status-success-600 dark:text-status-success-400" />
                </div>
                <div>
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    Update Progress
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {selectedGoal.title}
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label htmlFor="goal-progress-range" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                    Progress: {updateForm.progress}%
                  </label>
                  <input
                    id="goal-progress-range"
                    type="range"
                    min="0"
                    max="100"
                    value={updateForm.progress}
                    onChange={(e) => setUpdateForm({ ...updateForm, progress: parseInt(e.target.value) })}
                    className="w-full h-2 bg-lsc-cream dark:bg-lsc-brown rounded-xl appearance-none cursor-pointer accent-status-success-600"
                  />
                  <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>

                <div>
                  <label htmlFor="goal-update-note" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                    What did you accomplish? (optional)
                  </label>
                  <textarea
                    id="goal-update-note"
                    value={updateForm.note}
                    onChange={(e) => setUpdateForm({ ...updateForm, note: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                    placeholder={t('staffStrategic.shareWhatProgressWasMade')}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => setShowUpdateModal(false)}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={submitUpdate}
                  disabled={submitting}
                  className="flex items-center gap-2 px-6 py-2 bg-status-success-600 text-white rounded-xl hover:bg-status-success-700 transition-colors disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full motion-safe:animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Award className="h-4 w-4" />
                      Submit Update
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  );
}