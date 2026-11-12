/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { API_BASE } from '@/api/types';
import {
  Target, TrendingUp, Clock, Plus,
  ChevronDown, ChevronUp,  Trash2, BarChart3
} from "lucide-react";
import api from "../api/api";
import toast from "react-hot-toast";
import { useTranslation} from '@/i18n'
import ConfirmDialog from "@/components/ConfirmDialog"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

interface Metric {
  name: string;
  current: number;
  target: number;
  unit?: string;
}

interface ProgressUpdate {
  date: string;
  progress: number;
  note?: string;
  updated_by?: string;
}

interface Goal {
  id: number;
  plan_id: number;
  title: string;
  description?: string;
  category?: string;
  target_date?: string;
  completed_date?: string;
  progress: number;
  status: string;
  metrics: Metric[];
  updates: ProgressUpdate[];
  owner?: string;
  priority: number;
}

interface Plan {
  id: number;
  title: string;
  description?: string;
  period_start: string;
  period_end: string;
  mission?: string;
  vision?: string;
  values: string[];
  status: string;
  goals: Goal[];
  next_review?: string;
}

interface Dashboard {
  has_active_plan: boolean;
  plan?: {
    id: number;
    title: string;
    period: string;
    mission?: string;
    vision?: string;
    values: string[];
  };
  progress?: {
    overall: number;
    total_goals: number;
    completed: number;
    on_track: number;
    at_risk: number;
    delayed: number;
    not_started: number;
  };
  by_category?: Record<string, { count: number; progress: number }>;
}

const statusColors: Record<string, string> = {
  not_started: "bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300",
  on_track: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-300",
  at_risk: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-300",
  delayed: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-300",
  completed: "bg-earth-100 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light",
};

const statusLabels: Record<string, string> = {
  not_started: "Not Started",
  on_track: "On Track",
  at_risk: "At Risk",
  delayed: "Delayed",
  completed: "Completed",
};

export default function StrategicPlanPage() {
  const { t } = useTranslation()
  const { user } = useAuth();
  const isAdmin = user && ["admin", "super_admin"].includes(user.role);
  const isStaff = user && ["staff", "admin", "super_admin"].includes(user.role);

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGoals, setExpandedGoals] = useState<number[]>([]);

  // Edit states
  const [_editingGoal, _setEditingGoal] = useState<number | null>(null);
  const [progressUpdate, setProgressUpdate] = useState({ goalId: 0, progress: 0, note: "" });
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);

  // New goal form
  const [showNewGoal, setShowNewGoal] = useState(false);
  const [newGoal, setNewGoal] = useState({
    title: "",
    description: "",
    category: "",
    target_date: "",
    owner: "",
    priority: 3
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dashboardRes, planRes] = await Promise.all([
        api.get(`${API_BASE}/strategic/dashboard`).catch(() => null),
        api.get(`${API_BASE}/strategic/plans/active`).catch(() => null)
      ]);
      setDashboard(dashboardRes);
      setPlan(planRes);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      toast.error(t('strategicPlan.failedToLoadStrategicPlan'));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleGoal = (goalId: number) => {
    setExpandedGoals(prev =>
      prev.includes(goalId) ? prev.filter(id => id !== goalId) : [...prev, goalId]
    );
  };

  const openProgressUpdate = (goal: Goal) => {
    setProgressUpdate({ goalId: goal.id, progress: goal.progress, note: "" });
    setShowProgressModal(true);
  };

  const submitProgressUpdate = async () => {
    try {
      await api.post(`${API_BASE}/strategic/goals/${progressUpdate.goalId}/progress`, {
        progress: progressUpdate.progress,
        note: progressUpdate.note
      });
      toast.success(t('toast.strategicPlan.progressUpdated'));
      setShowProgressModal(false);
      fetchData();
    } catch (_err) {
      toast.error(t('strategicPlan.failedToUpdateProgress'));
    }
  };

  const createGoal = async () => {
    if (!plan) return;
    try {
      await api.post(`${API_BASE}/strategic/plans/${plan.id}/goals`, {
        ...newGoal,
        target_date: newGoal.target_date || null
      });
      toast.success(t('toast.strategicPlan.goalCreated'));
      setShowNewGoal(false);
      setNewGoal({ title: "", description: "", category: "", target_date: "", owner: "", priority: 3 });
      fetchData();
    } catch (_err) {
      toast.error(t('strategicPlan.failedToCreateGoal'));
    }
  };

  const updateGoalStatus = async (goalId: number, status: string) => {
    try {
      await api.put(`${API_BASE}/strategic/goals/${goalId}`, { status });
      toast.success(t('toast.adminMaterialCosts.statusUpdated'));
      fetchData();
    } catch (_err) {
      toast.error(t('strategicPlan.failedToUpdateStatus'));
    }
  };

  const deleteGoal = (goalId: number) => {
    setPendingAction(() => async () => {
      try {
        await api.delete(`${API_BASE}/strategic/goals/${goalId}`);
        toast.success(t('toast.strategicPlan.goalDeleted'));
        fetchData();
      } catch (_err) {
        toast.error(t('strategicPlan.failedToDeleteGoal'));
      }
    });
    setConfirmOpen(true);
  };

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-1/3"></div>
          <div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded"></div>
        </div>
      </PageContainer>
    );
  }

  if (!dashboard?.has_active_plan || !plan) {
    return (
      <PageContainer className="py-8">
        <div className="text-center py-16">
          <Target className="h-16 w-16 text-lsc-border mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Strategic Plan</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicPlan.noActiveStrategicPlanHas')}</p>
          {isAdmin && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
              Create a plan at <code>/admin/strategic</code>
            </p>
          )}
        </div>
      </PageContainer>
    );
  }

  const progress = dashboard.progress!;

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <Target className="h-8 w-8 text-lsc-rose" />
          {plan.title}
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          {new Date(plan.period_start).getFullYear()} - {new Date(plan.period_end).getFullYear()} Strategic Plan
        </p>
      </div>

      {/* Mission & Vision */}
      {(plan.mission || plan.vision) && (
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {plan.mission && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Our Mission</h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{plan.mission}</p>
            </div>
          )}
          {plan.vision && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Our Vision</h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{plan.vision}</p>
            </div>
          )}
        </div>
      )}

      {/* Progress Overview */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 mb-8">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Overall Progress
        </h2>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            <span>{progress.overall}% Complete</span>
            <span>{progress.completed} of {progress.total_goals} goals completed</span>
          </div>
          <div className="h-4 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-lsc-rose to-status-warning-600 transition-all duration-500"
              style={{ width: `${progress.overall}%` }}
            />
          </div>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-status-success-700 dark:text-status-success-300">{progress.on_track}</p>
            <p className="text-sm text-status-success-800 dark:text-status-success-400">On Track</p>
          </div>
          <div className="bg-earth-50 dark:bg-earth-800/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{progress.completed}</p>
            <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">Completed</p>
          </div>
          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-300">{progress.at_risk}</p>
            <p className="text-sm text-status-warning-800 dark:text-status-warning-400">At Risk</p>
          </div>
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-status-danger-700 dark:text-status-danger-300">{progress.delayed}</p>
            <p className="text-sm text-status-danger-800 dark:text-status-danger-400">Delayed</p>
          </div>
          <div className="bg-earth-50 dark:bg-earth-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-lsc-dark/70 dark:text-lsc-cream/70">{progress.not_started}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Not Started</p>
          </div>
        </div>
      </div>

      {/* Goals List */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Strategic Goals</h2>
          {isStaff && (
            <button
              onClick={() => setShowNewGoal(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
            >
              <Plus className="h-4 w-4" /> Add Goal
            </button>
          )}
        </div>

        <div className="divide-y divide-lsc-border dark:divide-earth-700">
          {plan.goals.length === 0 ? (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicPlan.noGoalsDefinedYet')}</div>
          ) : (
            plan.goals
              .sort((a, b) => a.priority - b.priority)
              .map((goal) => (
                <div key={goal.id} className="p-4">
                  {/* Goal Header */}
                  <div
                    className="flex items-start gap-4 cursor-pointer"
                    onClick={() => toggleGoal(goal.id)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => toggleGoal(goal.id))(); } }}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{goal.title}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[goal.status]}`}>
                          {statusLabels[goal.status]}
                        </span>
                        {goal.category && (
                          <span className="px-2 py-0.5 rounded bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 text-xs">
                            {goal.category}
                          </span>
                        )}
                      </div>
                      {/* Progress bar */}
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${goal.progress >= 100 ? "bg-earth-500" : goal.progress >= 50 ? "bg-status-success-500" : "bg-lsc-rose/30"}`}
                            style={{ width: `${goal.progress}%` }}
                          />
                        </div>
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-12">{goal.progress}%</span>
                      </div>
                    </div>
                    {expandedGoals.includes(goal.id) ? (
                      <ChevronUp className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    )}
                  </div>

                  {/* Expanded Details */}
                  {expandedGoals.includes(goal.id) && (
                    <div className="mt-4 pl-4 border-l-2 border-lsc-border dark:border-earth-700 space-y-4">
                      {goal.description && (
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{goal.description}</p>
                      )}

                      <div className="flex flex-wrap gap-4 text-sm">
                        {goal.owner && (
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            <strong>Owner:</strong> {goal.owner}
                          </span>
                        )}
                        {goal.target_date && (
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            <strong>Target:</strong> {new Date(goal.target_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      {/* Metrics */}
                      {goal.metrics && goal.metrics.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">Key Metrics</h4>
                          <div className="grid md:grid-cols-2 gap-2">
                            {goal.metrics.map((metric, i) => (
                              <div key={i} className="bg-lsc-cream dark:bg-lsc-brown rounded p-2 text-sm">
                                <div className="flex justify-between">
                                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{metric.name}</span>
                                  <span className="text-lsc-dark dark:text-earth-100">
                                    {metric.current} / {metric.target} {metric.unit}
                                  </span>
                                </div>
                                <div className="h-1.5 bg-lsc-cream dark:bg-lsc-brown rounded-full mt-1">
                                  <div
                                    className="h-full bg-lsc-rose/30 rounded-full"
                                    style={{ width: `${Math.min(100, (metric.current / metric.target) * 100)}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Recent Updates */}
                      {goal.updates && goal.updates.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">Recent Updates</h4>
                          <div className="space-y-2">
                            {goal.updates.slice(-3).reverse().map((update, i) => (
                              <div key={i} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2">
                                <Clock className="h-4 w-4 mt-0.5 shrink-0" />
                                <div>
                                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(update.date).toLocaleDateString()}</span>
                                  {" - "}{update.progress}%
                                  {update.note && <span> - {update.note}</span>}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      {isStaff && (
                        <div className="flex gap-2 pt-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); openProgressUpdate(goal); }}
                            className="flex items-center gap-1 px-3 py-1.5 bg-status-success-600 text-white rounded text-sm hover:bg-status-success-700"
                          >
                            <TrendingUp className="h-4 w-4" /> Update Progress
                          </button>
                          <select
                            value={goal.status}
                            onChange={(e) => { e.stopPropagation(); updateGoalStatus(goal.id, e.target.value); }}
                            className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded text-sm bg-lsc-white dark:bg-lsc-brown"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {Object.entries(statusLabels).map(([value, label]) => (
                              <option key={value} value={value}>{label}</option>
                            ))}
                          </select>
                          {isAdmin && (
                            <button
                              onClick={(e) => { e.stopPropagation(); deleteGoal(goal.id); }}
                              className="flex items-center gap-1 px-3 py-1.5 bg-status-danger-600 text-white rounded text-sm hover:bg-status-danger-700"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
          )}
        </div>
      </div>

      {/* Values */}
      {plan.values && plan.values.length > 0 && (
        <div className="mt-8 bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Our Core Values</h2>
          <div className="flex flex-wrap gap-3">
            {plan.values.map((value, i) => (
              <span
                key={i}
                className="px-4 py-2 bg-lsc-cream dark:bg-lsc-dark/20 text-lsc-dark dark:text-lsc-rose-light/50 rounded-full"
              >
                {value}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Progress Update Modal */}
      {showProgressModal && (
        <ModalBackdrop onClose={() => setShowProgressModal(false)} title="Update Progress">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 w-full max-w-md">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Update Progress</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Progress (%)</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={progressUpdate.progress}
                  onChange={(e) => setProgressUpdate({ ...progressUpdate, progress: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="text-center font-semibold text-lsc-dark dark:text-lsc-cream">
                  {progressUpdate.progress}%
                </div>
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Note (optional)</label>
                <textarea
                  value={progressUpdate.note}
                  onChange={(e) => setProgressUpdate({ ...progressUpdate, note: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                  placeholder={t('placeholder.strategicPlan.whatWasAccomplished')}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowProgressModal(false)}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={submitProgressUpdate}
                className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose"
              >
                Save Update
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* New Goal Modal */}
      {showNewGoal && (
        <ModalBackdrop onClose={() => setShowNewGoal(false)} title="Add Strategic Goal">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 w-full max-w-lg">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Add Strategic Goal</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
                <input
                  type="text"
                  value={newGoal.title}
                  onChange={(e) => setNewGoal({ ...newGoal, title: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                  placeholder={t('placeholder.strategicPlan.egIncreaseYouthProgram')}
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
                <textarea
                  value={newGoal.description}
                  onChange={(e) => setNewGoal({ ...newGoal, description: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Category</label>
                  <input
                    type="text"
                    value={newGoal.category}
                    onChange={(e) => setNewGoal({ ...newGoal, category: e.target.value })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                    placeholder={t('placeholder.strategicPlan.egCommunity')}
                  />
                </div>
                <div>
                  <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Priority</label>
                  <select
                    value={newGoal.priority}
                    onChange={(e) => setNewGoal({ ...newGoal, priority: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                  >
                    <option value={1}>1 - Highest</option>
                    <option value={2}>2 - High</option>
                    <option value={3}>3 - Medium</option>
                    <option value={4}>4 - Low</option>
                    <option value={5}>5 - Lowest</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Target Date</label>
                  <input
                    type="date"
                    value={newGoal.target_date}
                    onChange={(e) => setNewGoal({ ...newGoal, target_date: e.target.value })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                  />
                </div>
                <div>
                  <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Owner</label>
                  <input
                    type="text"
                    value={newGoal.owner}
                    onChange={(e) => setNewGoal({ ...newGoal, owner: e.target.value })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown"
                    placeholder={t('placeholder.strategicPlan.whosResponsible')}
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowNewGoal(false)}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={createGoal}
                disabled={!newGoal.title}
                className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
              >
                Create Goal
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete this goal?"
        message="This cannot be undone."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </PageContainer>
  );
}