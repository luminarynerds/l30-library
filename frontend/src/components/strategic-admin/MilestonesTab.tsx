/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, Edit2, Trash2, Eye, EyeOff, Award, Star } from "lucide-react";
import { Milestone } from "./strategic-types";

interface Props {
  milestones: Milestone[];
  onAdd: () => void;
  onEdit: (milestone: Milestone) => void;
  onDelete: (id: number, title: string) => void;
}

export default function MilestonesTab({ milestones, onAdd, onEdit, onDelete }: Props) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
      <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Milestones & Achievements</h2>
        <button
          onClick={onAdd}
          className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
        >
          <Plus className="h-4 w-4" /> Add Milestone
        </button>
      </div>
      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {milestones.length === 0 ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            No milestones yet. Celebrate your achievements!
          </div>
        ) : (
          milestones.map((milestone) => (
            <div key={milestone.id} className="p-4 flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Award className={`h-5 w-5 ${milestone.is_featured ? "text-lsc-rose" : "text-lsc-dark/70 dark:text-lsc-cream/70"}`} />
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{milestone.title}</h3>
                  {milestone.is_featured && <Star className="h-4 w-4 text-lsc-rose" aria-hidden="true" />}
                  {milestone.is_public ? (
                    <span title="Public"><Eye className="h-4 w-4 text-status-success-600" aria-hidden="true" /></span>
                  ) : (
                    <span title="Private"><EyeOff className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" /></span>
                  )}
                </div>
                {milestone.celebration_text && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{milestone.celebration_text}</p>
                )}
                <div className="flex gap-2 mt-2 text-xs">
                  <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded">
                    {milestone.milestone_type}
                  </span>
                  {milestone.achieved_date && (
                    <span className="px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded">
                      {new Date(milestone.achieved_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => onEdit(milestone)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                  aria-label={`Edit milestone ${milestone.title}`}
                >
                  <Edit2 className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  onClick={() => onDelete(milestone.id!, milestone.title)}
                  className="p-2 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded"
                  aria-label={`Delete milestone ${milestone.title}`}
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
