/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react";
import { Plus, Edit2, Trash2, CheckCircle, Gavel } from "lucide-react";
import * as Sentry from "@/lib/sentry-lazy";
import toast from "react-hot-toast";
import ConfirmDialog from "@/components/ConfirmDialog";
import InitiativeModal from "./InitiativeModal";
import BoardDecisionModal from "./BoardDecisionModal";
import {
  StrategicInitiative,
  InitiativeMilestone,
  BoardDecisionType,
  getInitiatives,
  createInitiative,
  updateInitiative,
  deleteInitiative,
  createInitiativeMilestone,
  completeInitiativeMilestone,
  linkBoardDecision,
} from "@/api/domains/admin/strategic-api";

interface Props {
  planId: number;
  isAdmin: boolean;
}

type InitiativeForm = Partial<StrategicInitiative> & { title: string };

const statusColors: Record<string, string> = {
  planning: "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream",
  approved: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  in_progress: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
  on_hold: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300",
  completed: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200",
  cancelled: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400",
};

const statusLabels: Record<string, string> = {
  planning: "Planning",
  approved: "Approved",
  in_progress: "In Progress",
  on_hold: "On Hold",
  completed: "Completed",
  cancelled: "Cancelled",
};

function blankInitiative(): InitiativeForm {
  return {
    title: "",
    description: "",
    business_case: "",
    expected_outcomes: [],
    status: "planning",
    priority: 3,
    team_members: [],
  };
}

export default function InitiativesTab({ planId, isAdmin }: Props) {
  const [initiatives, setInitiatives] = useState<StrategicInitiative[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<InitiativeForm>(blankInitiative());

  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; title: string } | null>(null);

  const [milestoneInitiativeId, setMilestoneInitiativeId] = useState<number | null>(null);
  const [milestoneTitle, setMilestoneTitle] = useState("");
  const [milestoneTargetDate, setMilestoneTargetDate] = useState("");

  const [boardDecisionInitiativeId, setBoardDecisionInitiativeId] = useState<number | null>(null);
  const [boardDecisionData, setBoardDecisionData] = useState<
    Partial<{ meeting_date: string; decision_type: BoardDecisionType; meeting_reference: string; decision_summary: string; vote_result: string; minutes_url: string; resolution_number: string }> & { meeting_date: string; decision_type: BoardDecisionType }
  >({ meeting_date: "", decision_type: "approval" });

  const load = useCallback(async () => {
    setLoadError(null);
    setLoading(true);
    try {
      const data = await getInitiatives(planId);
      setInitiatives(data);
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      setLoadError(err instanceof Error ? err.message : "Failed to load initiatives");
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    load();
  }, [load]);

  const openAdd = () => {
    setEditing(blankInitiative());
    setShowModal(true);
  };

  const openEdit = (initiative: StrategicInitiative) => {
    setEditing({ ...initiative });
    setShowModal(true);
  };

  const saveInitiative = async () => {
    if (!editing.title) return;
    try {
      if (editing.id) {
        const updated = await updateInitiative(editing.id, {
          title: editing.title,
          description: editing.description,
          business_case: editing.business_case,
          expected_outcomes: editing.expected_outcomes,
          status: editing.status,
          priority: editing.priority,
          start_date: editing.start_date,
          target_completion_date: editing.target_completion_date,
          estimated_budget: editing.estimated_budget,
          strategic_alignment_score: editing.strategic_alignment_score,
          completion_percentage: editing.completion_percentage,
        });
        setInitiatives((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
        toast.success("Initiative updated");
      } else {
        const created = await createInitiative(planId, {
          title: editing.title,
          description: editing.description,
          business_case: editing.business_case,
          expected_outcomes: editing.expected_outcomes,
          status: editing.status,
          priority: editing.priority,
          start_date: editing.start_date,
          target_completion_date: editing.target_completion_date,
          estimated_budget: editing.estimated_budget,
          strategic_alignment_score: editing.strategic_alignment_score,
        });
        setInitiatives((prev) => [...prev, created]);
        toast.success("Initiative created");
      }
      setShowModal(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save initiative");
    }
  };

  const confirmDelete = async (id: number) => {
    try {
      await deleteInitiative(id);
      setInitiatives((prev) => prev.filter((i) => i.id !== id));
      setDeleteConfirm(null);
      toast.success("Initiative deleted");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete initiative");
    }
  };

  const addMilestone = async () => {
    if (!milestoneInitiativeId || !milestoneTitle.trim()) return;
    try {
      const milestone = await createInitiativeMilestone(milestoneInitiativeId, {
        title: milestoneTitle.trim(),
        target_date: milestoneTargetDate || undefined,
      });
      setInitiatives((prev) =>
        prev.map((i) =>
          i.id === milestoneInitiativeId
            ? { ...i, milestones: [...i.milestones, milestone] }
            : i
        )
      );
      setMilestoneInitiativeId(null);
      setMilestoneTitle("");
      setMilestoneTargetDate("");
      toast.success("Milestone added");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add milestone");
    }
  };

  const completeMilestone = async (milestone: InitiativeMilestone) => {
    try {
      const updated = await completeInitiativeMilestone(milestone.id);
      setInitiatives((prev) =>
        prev.map((i) => ({
          ...i,
          milestones: i.milestones.map((m) => (m.id === updated.id ? updated : m)),
        }))
      );
      toast.success("Milestone completed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to complete milestone");
    }
  };

  const saveBoardDecision = async () => {
    if (!boardDecisionInitiativeId || !boardDecisionData.meeting_date) return;
    try {
      const decision = await linkBoardDecision(boardDecisionInitiativeId, {
        meeting_date: boardDecisionData.meeting_date,
        decision_type: boardDecisionData.decision_type,
        meeting_reference: boardDecisionData.meeting_reference,
        decision_summary: boardDecisionData.decision_summary,
        vote_result: boardDecisionData.vote_result,
        minutes_url: boardDecisionData.minutes_url,
        resolution_number: boardDecisionData.resolution_number,
      });
      setInitiatives((prev) =>
        prev.map((i) =>
          i.id === boardDecisionInitiativeId
            ? { ...i, board_decisions: [...i.board_decisions, decision] }
            : i
        )
      );
      setBoardDecisionInitiativeId(null);
      setBoardDecisionData({ meeting_date: "", decision_type: "approval" });
      toast.success("Board decision linked");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to link board decision");
    }
  };

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
      <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Strategic Initiatives</h2>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
        >
          <Plus className="h-4 w-4" /> Add Initiative
        </button>
      </div>

      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {loading ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">Loading initiatives...</div>
        ) : loadError ? (
          <div className="p-8 text-center">
            <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mb-3">{loadError}</p>
            <button
              onClick={load}
              className="px-3 py-1.5 text-sm bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-rose hover:text-white"
            >
              Retry
            </button>
          </div>
        ) : initiatives.length === 0 ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            No initiatives yet. Add your first strategic initiative.
          </div>
        ) : (
          initiatives.map((initiative) => {
            const totalMilestones = initiative.milestones.length;
            const completedMilestones = initiative.milestones.filter((m) => m.completed).length;

            return (
              <div key={initiative.id} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{initiative.title}</h3>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[initiative.status] || statusColors.planning}`}
                      >
                        {statusLabels[initiative.status] || initiative.status}
                      </span>
                      {initiative.board_approved && (
                        <span className="text-xs text-status-success-700 dark:text-status-success-300">
                          Board approved{initiative.board_approval_date ? ` ${new Date(initiative.board_approval_date).toLocaleDateString()}` : ""}
                        </span>
                      )}
                    </div>

                    {initiative.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mb-2">
                        {initiative.description}
                      </p>
                    )}

                    <div className="flex gap-2 flex-wrap text-xs">
                      {initiative.priority && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded">
                          Priority {initiative.priority}
                        </span>
                      )}
                      {initiative.completion_percentage != null && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                          {initiative.completion_percentage}% complete
                        </span>
                      )}
                      {initiative.target_completion_date && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded">
                          Target: {new Date(initiative.target_completion_date).toLocaleDateString()}
                        </span>
                      )}
                      {totalMilestones > 0 && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded">
                          {completedMilestones}/{totalMilestones} milestones
                        </span>
                      )}
                    </div>

                    {initiative.milestones.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {initiative.milestones.map((m) => (
                          <div key={m.id} className="flex items-center gap-2 text-sm">
                            <CheckCircle
                              className={`h-4 w-4 flex-shrink-0 ${m.completed ? "text-status-success-600" : "text-lsc-dark/30 dark:text-lsc-cream/30"}`}
                              aria-hidden="true"
                            />
                            <span
                              className={`flex-1 ${m.completed ? "line-through text-lsc-dark/50 dark:text-lsc-cream/50" : "text-lsc-dark dark:text-lsc-cream"}`}
                            >
                              {m.title}
                            </span>
                            {m.target_date && !m.completed && (
                              <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                                {new Date(m.target_date).toLocaleDateString()}
                              </span>
                            )}
                            {!m.completed && (
                              <button
                                onClick={() => completeMilestone(m)}
                                className="text-xs px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded hover:bg-status-success-200"
                                aria-label={`Complete milestone ${m.title}`}
                              >
                                Complete
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {initiative.board_decisions.length > 0 && (
                      <div className="mt-2 space-y-0.5">
                        {initiative.board_decisions.map((d) => (
                          <div key={d.id} className="flex items-center gap-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                            <Gavel className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                            <span>
                              {d.decision_type} — {new Date(d.meeting_date).toLocaleDateString()}
                              {d.meeting_reference ? ` (${d.meeting_reference})` : ""}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {milestoneInitiativeId === initiative.id && (
                      <div className="mt-3 flex gap-2 items-end">
                        <div className="flex-1">
                          <input
                            type="text"
                            value={milestoneTitle}
                            onChange={(e) => setMilestoneTitle(e.target.value)}
                            placeholder="Milestone title"
                            className="w-full px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
                            autoFocus
                          />
                        </div>
                        <input
                          type="date"
                          value={milestoneTargetDate}
                          onChange={(e) => setMilestoneTargetDate(e.target.value)}
                          className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
                        />
                        <button
                          onClick={addMilestone}
                          disabled={!milestoneTitle.trim()}
                          className="px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm disabled:opacity-50"
                        >
                          Add
                        </button>
                        <button
                          onClick={() => { setMilestoneInitiativeId(null); setMilestoneTitle(""); setMilestoneTargetDate(""); }}
                          className="px-3 py-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() => {
                        setMilestoneInitiativeId(milestoneInitiativeId === initiative.id ? null : initiative.id);
                        setMilestoneTitle("");
                        setMilestoneTargetDate("");
                      }}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                      title="Add milestone"
                      aria-label={`Add milestone to ${initiative.title}`}
                    >
                      <CheckCircle className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      onClick={() => {
                        setBoardDecisionInitiativeId(initiative.id);
                        setBoardDecisionData({ meeting_date: "", decision_type: "approval" });
                      }}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                      title="Link board decision"
                      aria-label={`Link board decision to ${initiative.title}`}
                    >
                      <Gavel className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      onClick={() => openEdit(initiative)}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                      aria-label={`Edit initiative ${initiative.title}`}
                    >
                      <Edit2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => setDeleteConfirm({ id: initiative.id, title: initiative.title })}
                        className="p-2 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded"
                        aria-label={`Delete initiative ${initiative.title}`}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {showModal && (
        <InitiativeModal
          editing={editing}
          setEditing={setEditing}
          onSave={saveInitiative}
          onClose={() => setShowModal(false)}
        />
      )}

      {boardDecisionInitiativeId != null && (
        <BoardDecisionModal
          data={boardDecisionData}
          setData={setBoardDecisionData}
          onSave={saveBoardDecision}
          onClose={() => setBoardDecisionInitiativeId(null)}
        />
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Initiative?"
        message={`Are you sure you want to delete "${deleteConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteConfirm) confirmDelete(deleteConfirm.id); }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </div>
  );
}
