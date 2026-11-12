/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react";
import { BookOpen, DollarSign, Users, MessageSquare, ChevronUp, ChevronDown } from "lucide-react";
import type { ReportStats } from "./BoardReportTypes";

export function NarrativePromptsPanel({ data }: { data: ReportStats }) {
  const [expanded, setExpanded] = useState(true);
  const prompts = data.narrative_prompts;

  if (!prompts) return null;

  const categories = [
    { key: "circulation" as const, label: "Circulation", icon: BookOpen, color: "text-lsc-rose dark:text-lsc-rose-light" },
    { key: "financial" as const, label: "Financial", icon: DollarSign, color: "text-status-success-600 dark:text-status-success-400" },
    { key: "patrons" as const, label: "Patrons", icon: Users, color: "text-status-warning-600 dark:text-status-warning-400" },
    { key: "general" as const, label: "General", icon: MessageSquare, color: "text-category-600 dark:text-category-400" },
  ];

  return (
    <div className="mt-6 bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-6 text-left"
      >
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-category-600" />
          Discussion Prompts for Board
        </h3>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        ) : (
          <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        )}
      </button>

      {expanded && (
        <div className="px-6 pb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.map(({ key, label, icon: Icon, color }) => {
            const items = prompts[key];
            if (!items || items.length === 0) return null;

            return (
              <div key={key} className="bg-earth-50 dark:bg-earth-800 rounded-lg p-4">
                <h4 className={`text-sm font-semibold ${color} mb-2 flex items-center gap-2`}>
                  <Icon className="w-4 h-4" />
                  {label}
                </h4>
                <ul className="space-y-2">
                  {items.map((prompt, idx) => (
                    <li key={idx} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                      {prompt}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
