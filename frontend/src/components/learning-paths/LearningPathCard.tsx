/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react";
import { Link } from "react-router-dom";
import { Clock, BookOpen, GraduationCap, Code, Shield, Lightbulb, Target, Compass, Rocket } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface LearningPathCardProps {
  id: number;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  difficulty: string | null;
  estimated_hours: number | null;
  total_courses?: number;
  progress?: number;
  is_enrolled?: boolean;
  status?: "draft" | "published" | "archived";
}

interface PathTheme {
  icon: LucideIcon;
  from: string;
  to: string;
}

const PATH_KEYWORDS: [string[], PathTheme][] = [
  [['digital', 'tech', 'computer'], { icon: Code, from: 'from-sky-400', to: 'to-blue-600' }],
  [['security', 'safety', 'privacy'], { icon: Shield, from: 'from-red-400', to: 'to-rose-600' }],
  [['leadership', 'management', 'staff'], { icon: Target, from: 'from-lsc-rose', to: 'to-violet-600' }],
  [['beginner', 'intro', 'getting started', 'essentials'], { icon: Compass, from: 'from-emerald-400', to: 'to-green-600' }],
  [['advanced', 'expert', 'mastery'], { icon: Rocket, from: 'from-orange-400', to: 'to-red-500' }],
  [['creative', 'maker', 'design'], { icon: Lightbulb, from: 'from-status-warning-400', to: 'to-yellow-600' }],
  [['literacy', 'reading', 'book'], { icon: BookOpen, from: 'from-fuchsia-400', to: 'to-pink-600' }],
];

function getPathTheme(title: string): PathTheme {
  const lower = title.toLowerCase();
  for (const [keywords, theme] of PATH_KEYWORDS) {
    if (keywords.some(k => lower.includes(k))) return theme;
  }
  const hash = [...title].reduce((h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0);
  const fallbacks: PathTheme[] = [
    { icon: GraduationCap, from: 'from-teal-400', to: 'to-cyan-600' },
    { icon: BookOpen, from: 'from-violet-400', to: 'to-category-600' },
    { icon: Compass, from: 'from-lime-400', to: 'to-green-600' },
  ];
  return fallbacks[Math.abs(hash) % fallbacks.length]!;
}

export const LearningPathCard: React.FC<LearningPathCardProps> = ({
  id,
  title,
  description,
  thumbnail_url,
  difficulty,
  estimated_hours,
  total_courses = 0,
  progress = 0,
  is_enrolled = false,
  status = "published",
}) => {
  const difficultyColors = {
    beginner: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-400",
    intermediate: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300",
    advanced: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300",
  };

  const defaultColor = "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream";
  const colorClass = difficultyColors[difficulty as keyof typeof difficultyColors] || defaultColor;
  const theme = getPathTheme(title);
  const Icon = theme.icon;

  return (
    <Link
      to={`/learning-paths/${id}`}
      className="block bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden border border-lsc-border dark:border-earth-700"
    >
      <div className="relative h-48">
        {thumbnail_url ? (
          <img src={thumbnail_url} alt={title} className="w-full h-full object-cover" />
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${theme.from} ${theme.to} flex items-center justify-center relative overflow-hidden`}>
            <div className="absolute inset-0 opacity-10" style={{
              backgroundImage: 'radial-gradient(circle at 20% 80%, white 1px, transparent 1px), radial-gradient(circle at 80% 20%, white 1px, transparent 1px)',
              backgroundSize: '30px 30px',
            }} />
            <Icon className="w-16 h-16 text-white/80 relative z-10 drop-shadow-sm" aria-hidden="true" />
          </div>
        )}
        {status !== "published" && !is_enrolled && (
          <div className="absolute top-2 right-2 bg-status-warning-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
            Coming Soon
          </div>
        )}
        {is_enrolled && (
          <div className="absolute top-2 right-2 bg-status-success-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
            Enrolled
          </div>
        )}
        {difficulty && (
          <div className={`absolute bottom-2 left-2 ${colorClass} px-3 py-1 rounded-full text-sm font-semibold capitalize`}>
            {difficulty}
          </div>
        )}
      </div>

      <div className="p-5">
        <h3 className="font-serif text-xl font-bold mb-2 text-lsc-dark dark:text-lsc-cream line-clamp-2" title={title}>{title}</h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 line-clamp-2" title={description || "No description available"}>{description || "No description available"}</p>

        <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {estimated_hours !== null && estimated_hours > 0 && (
            <div className="flex items-center gap-1" title="Estimated total time">
              <Clock className="w-4 h-4" />
              <span>{estimated_hours < 1 ? `${Math.round(estimated_hours * 60)}m` : `${estimated_hours}h`}</span>
            </div>
          )}
          {total_courses > 0 && (
            <div className="flex items-center gap-1">
              <BookOpen className="w-4 h-4" />
              <span>{total_courses} {total_courses === 1 ? 'course' : 'courses'}</span>
            </div>
          )}
        </div>

        {is_enrolled && progress !== undefined && (
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Progress</span>
              <span className="font-semibold text-lsc-rose dark:text-lsc-rose-light">{progress}%</span>
            </div>
            <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2">
              <div
                className="bg-lsc-rose h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </Link>
  );
};
