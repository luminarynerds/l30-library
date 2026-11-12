/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState, useCallback } from "react";
import { useRequireRole } from '@/hooks/useRequireRole';
import { Target, Plus, Upload, FileText, Award, Clock, Rocket, BarChart3 } from "lucide-react";
import api from "../api/api";
import toast from "react-hot-toast";
import ConfirmDialog from "../components/ConfirmDialog";
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { Plan, Goal, Milestone, TimelineEvent } from '../components/strategic-admin/strategic-types'
import PlanDetailsTab from '../components/strategic-admin/PlanDetailsTab'
import GoalsTab from '../components/strategic-admin/GoalsTab'
import MilestonesTab from '../components/strategic-admin/MilestonesTab'
import HistoryTab from '../components/strategic-admin/HistoryTab'
import ImportExportTab from '../components/strategic-admin/ImportExportTab'
import GoalModal from '../components/strategic-admin/GoalModal'
import MilestoneModal from '../components/strategic-admin/MilestoneModal'
import InitiativesTab from '../components/strategic-admin/InitiativesTab'
import KPIsTab from '../components/strategic-admin/KPIsTab'

const tabs = [
  { id: "plan", label: "Plan Details", icon: Target },
  { id: "goals", label: "Goals", icon: FileText },
  { id: "milestones", label: "Milestones", icon: Award },
  { id: "initiatives", label: "Initiatives", icon: Rocket },
  { id: "kpis", label: "KPIs", icon: BarChart3 },
  { id: "history", label: "History Timeline", icon: Clock },
  { id: "import", label: "Import/Export", icon: Upload },
];

export default function StrategicAdminPage() {
  const { t } = useTranslation()
  const { isAuthorized: isAdmin } = useRequireRole('systemAdmin');

  const [activeTab, setActiveTab] = useState("plan");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);

  const [planForm, setPlanForm] = useState<Plan>({
    title: "",
    description: "",
    period_start: "",
    period_end: "",
    mission: "",
    vision: "",
    values: [],
    status: "draft",
    hero_image_url: "",
    story_intro: "",
    history_timeline: [],
  });
  const [newValue, setNewValue] = useState("");

  const [goals, setGoals] = useState<Goal[]>([]);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [viewingGoalId, setViewingGoalId] = useState<number | null>(null);

  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [editingMilestone, setEditingMilestone] = useState<Milestone | null>(null);
  const [showMilestoneModal, setShowMilestoneModal] = useState(false);

  const [editingEvent, setEditingEvent] = useState<TimelineEvent | null>(null);
  const [editingEventIndex, setEditingEventIndex] = useState<number | null>(null);

  const [importJson, setImportJson] = useState("");

  const [deleteGoalConfirm, setDeleteGoalConfirm] = useState<{ id: number; title: string } | null>(null);
  const [deleteMilestoneConfirm, setDeleteMilestoneConfirm] = useState<{ id: number; title: string } | null>(null);

  const [draggedGoalId, setDraggedGoalId] = useState<number | null>(null);
  const [dragOverGoalId, setDragOverGoalId] = useState<number | null>(null);

  const handleDragStart = useCallback((e: React.DragEvent, goalId: number) => {
    setDraggedGoalId(goalId);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", goalId.toString());
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, goalId: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (draggedGoalId !== goalId) {
      setDragOverGoalId(goalId);
    }
  }, [draggedGoalId]);

  const handleDragLeave = useCallback(() => {
    setDragOverGoalId(null);
  }, []);

  const fetchPlanDetails = async (planId: number) => {
    try {
      const [planRes, milestonesRes] = await Promise.all([
        api.get(`/api/v1/strategic/plans/${planId}`) as Promise<Plan>,
        api.get(`/api/v1/strategic/plans/${planId}/milestones?include_private=true`) as Promise<{ items: Milestone[] }>,
      ]);
      setPlan(planRes);
      setPlanForm({
        ...planRes,
        period_start: planRes.period_start?.split("T")[0] || "",
        period_end: planRes.period_end?.split("T")[0] || "",
        values: planRes.values || [],
        history_timeline: planRes.history_timeline || [],
      });
      setGoals(planRes.goals || []);
      setMilestones(milestonesRes?.items || []);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    }
  };


  const handleDrop = useCallback(async (e: React.DragEvent, targetGoalId: number) => {
    e.preventDefault();
    setDragOverGoalId(null);

    if (!draggedGoalId || draggedGoalId === targetGoalId || !plan?.id) {
      setDraggedGoalId(null);
      return;
    }

    const draggedIndex = goals.findIndex(g => g.id === draggedGoalId);
    const targetIndex = goals.findIndex(g => g.id === targetGoalId);

    if (draggedIndex === -1 || targetIndex === -1) {
      setDraggedGoalId(null);
      return;
    }

    const newGoals = [...goals];
    const draggedGoal = newGoals[draggedIndex];
    if (!draggedGoal) {
      setDraggedGoalId(null);
      return;
    }
    newGoals.splice(draggedIndex, 1);
    newGoals.splice(targetIndex, 0, draggedGoal);
    setGoals(newGoals);

    try {
      const goalIds = newGoals.map(g => g.id!);
      await api.put(`/api/v1/strategic/plans/${plan.id}/goals/reorder`, { goal_ids: goalIds });
      toast.success(t('strategicPlan.toast.goalsReordered'));
    } catch (_err) {
      fetchPlanDetails(plan.id);
      toast.error(t('strategicAdmin.failedToReorderGoals'));
    }

    setDraggedGoalId(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draggedGoalId, goals, plan?.id]);

  const handleDragEnd = useCallback(() => {
    setDraggedGoalId(null);
    setDragOverGoalId(null);
  }, []);


  const fetchPlans = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/v1/strategic/plans") as { items: Plan[] };
      setPlans(res.items);
      if (res.items.length > 0) {
        const active = res.items.find((p: Plan) => p.status === "active") || res.items[0];
        if (active?.id) {
          setSelectedPlanId(active.id);
        }
      }
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    if (!isAdmin) return;
    fetchPlans();
  }, [isAdmin]);

  useEffect(() => {
    let cancelled = false
    const loadPlanDetails = async () => {
      if (!selectedPlanId) return
      try {
        const [planRes, milestonesRes] = await Promise.all([
          api.get(`/api/v1/strategic/plans/${selectedPlanId}`) as Promise<Plan>,
          api.get(`/api/v1/strategic/plans/${selectedPlanId}/milestones?include_private=true`) as Promise<{ items: Milestone[] }>,
        ])
        if (!cancelled) {
          setPlan(planRes)
          setPlanForm({
            ...planRes,
            period_start: planRes.period_start?.split("T")[0] || "",
            period_end: planRes.period_end?.split("T")[0] || "",
            values: planRes.values || [],
            history_timeline: planRes.history_timeline || [],
          })
          setGoals(planRes.goals || [])
          setMilestones(milestonesRes?.items || [])
        }
      } catch (_err) {
        if (!cancelled) {
          Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
        }
      }
    }
    loadPlanDetails()
    return () => { cancelled = true }
  }, [selectedPlanId])

  const savePlan = async () => {
    setSaving(true);
    try {
      if (plan?.id) {
        await api.put(`/api/v1/strategic/plans/${plan.id}`, planForm);
        toast.success(t('strategicPlan.toast.planUpdated'));
      } else {
        const res = await api.post<Plan>("/api/v1/strategic/plans", planForm);
        if (res.id) {
          setSelectedPlanId(res.id);
        }
        toast.success(t('strategicPlan.toast.planCreated'));
      }
      fetchPlans();
    } catch (_err) {
      toast.error(t('strategicAdmin.failedToSavePlan'));
    } finally {
      setSaving(false);
    }
  };

  const createNewPlan = () => {
    setPlan(null);
    setSelectedPlanId(null);
    setPlanForm({
      title: "",
      description: "",
      period_start: "",
      period_end: "",
      mission: "",
      vision: "",
      values: [],
      status: "draft",
      hero_image_url: "",
      story_intro: "",
      history_timeline: [],
    });
    setGoals([]);
    setMilestones([]);
    setActiveTab("plan");
  };

  const openGoalModal = (goal?: Goal) => {
    setEditingGoal(goal || {
      title: "",
      description: "",
      public_description: "",
      category: "",
      department: "",
      target_date: "",
      progress: 0,
      status: "not_started",
      priority: 3,
      is_public: true,
      staff_can_update: false,
      metrics: [],
    });
    setShowGoalModal(true);
  };

  const saveGoal = async () => {
    if (!editingGoal || !plan?.id) return;
    try {
      if (editingGoal.id) {
        await api.put(`/api/v1/strategic/goals/${editingGoal.id}`, editingGoal);
        toast.success(t('strategicPlan.toast.goalUpdated'));
      } else {
        await api.post(`/api/v1/strategic/plans/${plan.id}/goals`, editingGoal);
        toast.success(t('strategicPlan.toast.goalCreated'));
      }
      setShowGoalModal(false);
      fetchPlanDetails(plan.id);
    } catch (_err) {
      toast.error(t('strategicAdmin.failedToSaveGoal'));
    }
  };

  const deleteGoal = async (goalId: number) => {
    try {
      await api.delete(`/api/v1/strategic/goals/${goalId}`);
      toast.success(t('strategicPlan.toast.goalDeleted'));
      setDeleteGoalConfirm(null);
      if (plan?.id) fetchPlanDetails(plan.id);
    } catch (_err) {
      toast.error(t('strategicAdmin.failedToDeleteGoal'));
    }
  };

  const openMilestoneModal = (milestone?: Milestone) => {
    setEditingMilestone(milestone || {
      title: "",
      description: "",
      achieved_date: "",
      celebration_text: "",
      impact_story: "",
      photo_url: "",
      is_public: true,
      is_featured: false,
      display_order: milestones.length,
      milestone_type: "achievement",
    });
    setShowMilestoneModal(true);
  };

  const saveMilestone = async () => {
    if (!editingMilestone || !plan?.id) return;
    try {
      if (editingMilestone.id) {
        await api.put(`/api/v1/strategic/milestones/${editingMilestone.id}`, editingMilestone);
        toast.success(t('strategicPlan.toast.milestoneUpdated'));
      } else {
        await api.post(`/api/v1/strategic/plans/${plan.id}/milestones`, editingMilestone);
        toast.success(t('strategicPlan.toast.milestoneCreated'));
      }
      setShowMilestoneModal(false);
      fetchPlanDetails(plan.id);
    } catch (_err) {
      toast.error(t('strategicAdmin.failedToSaveMilestone'));
    }
  };

  const deleteMilestone = async (milestoneId: number) => {
    try {
      await api.delete(`/api/v1/strategic/milestones/${milestoneId}`);
      toast.success(t('strategicPlan.toast.milestoneDeleted'));
      setDeleteMilestoneConfirm(null);
      if (plan?.id) fetchPlanDetails(plan.id);
    } catch (_err) {
      toast.error(t('strategicAdmin.failedToDeleteMilestone'));
    }
  };

  const saveTimelineEvent = () => {
    if (!editingEvent) return;
    const timeline = [...planForm.history_timeline];
    if (editingEventIndex !== null) {
      timeline[editingEventIndex] = editingEvent;
    } else {
      timeline.push(editingEvent);
      timeline.sort((a, b) => a.year - b.year);
    }
    setPlanForm({ ...planForm, history_timeline: timeline });
    setEditingEvent(null);
    setEditingEventIndex(null);
  };

  const editTimelineEvent = (index: number) => {
    const event = planForm.history_timeline[index];
    if (event) {
      setEditingEvent(event);
      setEditingEventIndex(index);
    }
  };

  const deleteTimelineEvent = (index: number) => {
    setPlanForm({
      ...planForm,
      history_timeline: planForm.history_timeline.filter((_, i) => i !== index),
    });
  };

  const exportPlan = async () => {
    if (!plan?.id) return;
    try {
      const res = await api.get(`/api/v1/strategic/plans/${plan.id}/export`);
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `strategic-plan-${plan.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t('strategicPlan.toast.planExported'));
    } catch (_err) {
      toast.error(t('strategicPlan.toast.exportFailed'));
    }
  };

  const importPlan = async () => {
    try {
      const data = JSON.parse(importJson);
      await api.post("/api/v1/strategic/import", data);
      toast.success(t('strategicPlan.toast.planImported'));
      setImportJson("");
      fetchPlans();
    } catch (_err) {
      toast.error(t('strategicAdmin.failedToImportCheckJson'));
    }
  };

  if (!isAdmin) {
    return (
      <AdminShell title="Strategic Administration">
        <div className="text-center py-12">
          <Target className="h-16 w-16 text-lsc-border mx-auto mb-4" />
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">Admin access required.</p>
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell
      title="Strategic Administration"
      icon={<Target className="h-8 w-8 text-lsc-rose" />}
      subtitle="Create and manage your library's strategic plan"
      loading={loading}
      actions={
        <div className="flex gap-2">
          <select
            value={selectedPlanId || ""}
            onChange={(e) => setSelectedPlanId(Number(e.target.value))}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          >
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} ({p.status})
              </option>
            ))}
          </select>
          <button
            onClick={createNewPlan}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose"
          >
            <Plus className="h-5 w-5" /> New Plan
          </button>
        </div>
      }
    >
      <div className="flex gap-1 border-b border-lsc-border dark:border-earth-700 mb-6 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.id
                ? "text-lsc-rose border-b-2 border-earth-600"
                : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "plan" && (
        <PlanDetailsTab
          planForm={planForm}
          setPlanForm={setPlanForm}
          newValue={newValue}
          setNewValue={setNewValue}
          saving={saving}
          onSave={savePlan}
        />
      )}

      {activeTab === "goals" && plan?.id && (
        <GoalsTab
          goals={goals}
          draggedGoalId={draggedGoalId}
          dragOverGoalId={dragOverGoalId}
          viewingGoalId={viewingGoalId}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onDragEnd={handleDragEnd}
          onAdd={() => openGoalModal()}
          onEdit={openGoalModal}
          onDelete={(id, title) => setDeleteGoalConfirm({ id, title })}
          onToggleComments={(goalId) => setViewingGoalId(viewingGoalId === goalId ? null : goalId)}
        />
      )}

      {activeTab === "milestones" && plan?.id && (
        <MilestonesTab
          milestones={milestones}
          onAdd={() => openMilestoneModal()}
          onEdit={openMilestoneModal}
          onDelete={(id, title) => setDeleteMilestoneConfirm({ id, title })}
        />
      )}

      {activeTab === "initiatives" && plan?.id && (
        <InitiativesTab planId={plan.id} isAdmin={!!isAdmin} />
      )}

      {activeTab === "kpis" && plan?.id && (
        <KPIsTab planId={plan.id} isAdmin={!!isAdmin} />
      )}

      {activeTab === "history" && (
        <HistoryTab
          planForm={planForm}
          editingEvent={editingEvent}
          setEditingEvent={setEditingEvent}
          setEditingEventIndex={setEditingEventIndex}
          saving={saving}
          onSave={savePlan}
          onSaveEvent={saveTimelineEvent}
          onEditEvent={editTimelineEvent}
          onDeleteEvent={deleteTimelineEvent}
        />
      )}

      {activeTab === "import" && (
        <ImportExportTab
          plan={plan}
          importJson={importJson}
          setImportJson={setImportJson}
          onExport={exportPlan}
          onImport={importPlan}
        />
      )}

      {showGoalModal && editingGoal && (
        <GoalModal
          editingGoal={editingGoal}
          setEditingGoal={setEditingGoal}
          onSave={saveGoal}
          onClose={() => setShowGoalModal(false)}
        />
      )}

      {showMilestoneModal && editingMilestone && (
        <MilestoneModal
          editingMilestone={editingMilestone}
          setEditingMilestone={setEditingMilestone}
          onSave={saveMilestone}
          onClose={() => setShowMilestoneModal(false)}
        />
      )}

      <ConfirmDialog
        isOpen={!!deleteGoalConfirm}
        title="Delete Goal?"
        message={`Are you sure you want to delete "${deleteGoalConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteGoalConfirm) deleteGoal(deleteGoalConfirm.id) }}
        onCancel={() => setDeleteGoalConfirm(null)}
      />

      <ConfirmDialog
        isOpen={!!deleteMilestoneConfirm}
        title="Delete Milestone?"
        message={`Are you sure you want to delete "${deleteMilestoneConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteMilestoneConfirm) deleteMilestone(deleteMilestoneConfirm.id) }}
        onCancel={() => setDeleteMilestoneConfirm(null)}
      />
    </AdminShell>
  );
}
