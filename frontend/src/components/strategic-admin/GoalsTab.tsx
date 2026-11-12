/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, Edit2, Trash2, Eye, EyeOff, Users, GripVertical, MessageCircle } from "lucide-react";
import { CommentCountBadge } from "../StrategicComments";
import { RichTextDisplay } from "../RichTextEditor";
import { Goal } from "./strategic-types";

interface Props {
  goals: Goal[];
  draggedGoalId: number | null;
  dragOverGoalId: number | null;
  viewingGoalId: number | null;
  onDragStart: (e: React.DragEvent, goalId: number) => void;
  onDragOver: (e: React.DragEvent, goalId: number) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent, goalId: number) => void;
  onDragEnd: () => void;
  onAdd: () => void;
  onEdit: (goal: Goal) => void;
  onDelete: (id: number, title: string) => void;
  onToggleComments: (goalId: number) => void;
}

export default function GoalsTab({
  goals,
  draggedGoalId,
  dragOverGoalId,
  viewingGoalId,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  onDragEnd,
  onAdd,
  onEdit,
  onDelete,
  onToggleComments,
}: Props) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
      <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
        <div>
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Strategic Goals</h2>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
            Drag goals to reorder them
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onAdd}
            className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
          >
            <Plus className="h-4 w-4" /> Add Goal
          </button>
        </div>
      </div>
      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {goals.length === 0 ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            No goals yet. Add your first strategic goal.
          </div>
        ) : (
          goals.map((goal) => (
            <div
              key={goal.id}
              draggable
              onDragStart={(e) => onDragStart(e, goal.id!)}
              onDragOver={(e) => onDragOver(e, goal.id!)}
              onDragLeave={onDragLeave}
              onDrop={(e) => onDrop(e, goal.id!)}
              onDragEnd={onDragEnd}
              className={`p-4 flex items-start gap-3 transition-colors ${
                draggedGoalId === goal.id ? "opacity-50 bg-lsc-cream/50 dark:bg-earth-700/50" : ""
              } ${
                dragOverGoalId === goal.id ? "bg-lsc-rose/10 border-l-4 border-lsc-rose" : ""
              }`}
            >
              <div className="flex-shrink-0 pt-1 cursor-grab active:cursor-grabbing">
                <GripVertical className="h-5 w-5 text-lsc-dark/30 dark:text-lsc-cream/60 hover:text-lsc-dark/70 dark:hover:text-lsc-cream/70" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{goal.title}</h3>
                  {goal.is_public ? (
                    <span title="Public"><Eye className="h-4 w-4 text-status-success-600" aria-hidden="true" /></span>
                  ) : (
                    <span title="Private"><EyeOff className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" /></span>
                  )}
                  {goal.staff_can_update && (
                    <span title="Staff can update"><Users className="h-4 w-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" /></span>
                  )}
                  <CommentCountBadge count={goal.comment_count || 0} />
                </div>
                {goal.description && (
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2">
                    <RichTextDisplay content={goal.description} />
                  </div>
                )}
                <div className="flex gap-2 mt-2 text-xs flex-wrap">
                  {goal.category && (
                    <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded">
                      {goal.category}
                    </span>
                  )}
                  {goal.department && (
                    <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                      {goal.department}
                    </span>
                  )}
                  <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                    {goal.progress}%
                  </span>
                </div>
              </div>
              <div className="flex gap-1 flex-shrink-0">
                <button
                  onClick={() => onToggleComments(goal.id!)}
                  className={`p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded ${viewingGoalId === goal.id ? "text-lsc-rose bg-lsc-cream dark:bg-lsc-brown" : "text-lsc-dark/70 dark:text-lsc-cream/70"}`}
                  aria-label={`${viewingGoalId === goal.id ? "Hide" : "View"} comments for ${goal.title}`}
                >
                  <MessageCircle className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  onClick={() => onEdit(goal)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                  aria-label={`Edit goal ${goal.title}`}
                >
                  <Edit2 className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  onClick={() => onDelete(goal.id!, goal.title)}
                  className="p-2 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded"
                  aria-label={`Delete goal ${goal.title}`}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
