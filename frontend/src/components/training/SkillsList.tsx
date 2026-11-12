/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useMemo } from 'react';
import { ChevronRight, Trash2, Edit, Eye, Plus, Search, Filter, Loader2, GraduationCap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import type { Skill } from './types';
import type { CourseBrief } from './api';
import { skillsApi, learningApi } from './api';
import ConfirmDialog from '../ConfirmDialog';
import { useTranslation} from '@/i18n'

function SkillCoursesDisclosure({ skill }: { skill: Skill }): React.ReactElement {
  const [expanded, setExpanded] = useState(false);
  const skillIdNum = Number(skill.id);
  const panelId = `skill-courses-panel-${skill.id}`;
  const buttonId = `skill-courses-toggle-${skill.id}`;

  const {
    data: courses,
    isLoading,
    isError,
  } = useQuery<CourseBrief[]>({
    queryKey: ['courses-for-skill', skillIdNum],
    queryFn: () => learningApi.getCoursesForSkill(skillIdNum),
    enabled: expanded && Number.isFinite(skillIdNum),
    staleTime: 60_000,
  });

  const count = courses?.length ?? 0;
  const triggerLabel = expanded
    ? 'Hide courses'
    : `Show courses that build this skill${
        courses && !isLoading ? ` (${count})` : ''
      }`;

  return (
    <div className="mt-2">
      <button
        id={buttonId}
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        aria-controls={panelId}
        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
      >
        <ChevronRight
          aria-hidden="true"
          className={`w-3.5 h-3.5 motion-safe:transition-transform ${
            expanded ? 'rotate-90' : ''
          }`}
        />
        <span>{triggerLabel}</span>
      </button>
      {expanded && (
        <div
          id={panelId}
          role="region"
          aria-labelledby={buttonId}
          className="mt-2 min-h-[40px] rounded-lg border border-lsc-border bg-lsc-cream/40 dark:border-earth-700 dark:bg-earth-900/40 p-3"
        >
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <Loader2
                aria-hidden="true"
                className="w-4 h-4 motion-safe:animate-spin"
              />
              <span>Loading courses…</span>
            </div>
          )}
          {isError && !isLoading && (
            <p className="text-sm text-status-danger-600 dark:text-status-danger-400">
              Could not load courses for this skill. Try again later.
            </p>
          )}
          {!isLoading && !isError && courses && courses.length === 0 && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              No courses build this skill yet.
            </p>
          )}
          {!isLoading && !isError && courses && courses.length > 0 && (
            <ul className="space-y-1.5">
              {courses.map((c) => (
                <li key={c.id} className="text-sm">
                  <a
                    href={`/learn/course/${c.id}`}
                    className="text-lsc-rose dark:text-lsc-rose-light hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
                  >
                    {c.title}
                  </a>
                  <span className="ml-2 text-lsc-dark/60 dark:text-lsc-cream/60">
                    Level taught: {c.level_taught}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

interface FiltersState {
  search: string;
  category: string;
  sort: 'name' | 'category' | 'recently_created';
}

export const SkillsList: React.FC<{
  onAddClick: () => void;
  onEditClick: (skill: Skill) => void;
  onViewClick: (skill: Skill) => void;
  onAssessmentClick: (skill: Skill) => void;
}> = ({ onAddClick, onEditClick, onViewClick, onAssessmentClick }) => {
  const { t } = useTranslation()
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FiltersState>({
    search: '',
    category: '',
    sort: 'name',
  });
  const [categories, setCategories] = useState<string[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteSkillConfirm, setDeleteSkillConfirm] = useState<{ id: string; name: string } | null>(null);

  const loadSkills = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const apiFilters: { category?: string; search?: string } = {};
      if (filters.category) apiFilters.category = filters.category;
      if (filters.search) apiFilters.search = filters.search;
      const data = await skillsApi.listSkills(apiFilters);
      setSkills(data);
      const uniqueCategories = Array.from(new Set(data.map((s) => s.category))).sort();
      setCategories(uniqueCategories);
    } catch (_err) {
      setError(_err instanceof Error ? _err.message : 'Failed to load skills');
    } finally {
      setLoading(false);
    }
  }, [filters.category, filters.search]);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const handleDelete = async (id: string) => {
    try {
      setDeleting(id);
      await skillsApi.deleteSkill(id);
      setSkills((prev) => prev.filter((s) => s.id !== id));
      setDeleteSkillConfirm(null);
    } catch (_err) {
      setError(_err instanceof Error ? _err.message : 'Failed to delete skill');
    } finally {
      setDeleting(null);
    }
  };

  const sortedSkills = useMemo(() => {
    return [...skills].sort((a, b) => {
      switch (filters.sort) {
        case 'category':
          return a.category.localeCompare(b.category);
        case 'recently_created':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'name':
        default:
          return a.name.localeCompare(b.name);
      }
    });
  }, [filters.sort, skills]);

  if (loading && skills.length === 0) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Staff Skills & Training
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Manage staff competencies and assessments
          </p>
        </div>
        <button
          onClick={onAddClick}
          className="inline-flex items-center gap-2 rounded-xl bg-lsc-rose px-4 py-2.5 font-medium text-white hover:bg-lsc-rose dark:bg-lsc-rose-light dark:hover:bg-lsc-rose transition-colors"
        >
          <Plus aria-hidden="true" className="w-5 h-5" />
          Add Skill
        </button>
      </div>

      {/* Filters */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-3 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={t('components.training.skillsList.searchSkillsByName')}
            aria-label={t('components.training.skillsList.searchSkillsByName2')}
            value={filters.search}
            onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
            className="w-full rounded-xl border border-lsc-border bg-lsc-white py-2.5 pl-10 pr-4 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-lsc-brown dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
          />
        </div>

        {/* Filters row */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <Filter aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <select
              id="skills-category-filter"
              aria-label={t('aria.training.filterByCategory')}
              value={filters.category}
              onChange={(e) => setFilters((prev) => ({ ...prev, category: e.target.value }))}
              className="flex-1 rounded-xl border border-lsc-border bg-lsc-white px-3 py-2.5 text-lsc-dark dark:border-earth-700 dark:bg-lsc-brown dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Sort */}
          <select
            id="skills-sort-filter"
            aria-label={t('aria.training.sortSkillsBy')}
            value={filters.sort}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                sort: e.target.value as FiltersState['sort'],
              }))
            }
            className="rounded-xl border border-lsc-border bg-lsc-white px-3 py-2.5 text-lsc-dark dark:border-earth-700 dark:bg-lsc-brown dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
          >
            <option value="name">Sort by Name</option>
            <option value="category">Sort by Category</option>
            <option value="recently_created">Recently Created</option>
          </select>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="rounded-xl border border-status-danger-300 bg-status-danger-50 p-4 text-status-danger-700 dark:border-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-200">
          {error}
        </div>
      )}

      {/* Empty state */}
      {sortedSkills.length === 0 && !loading && (
        <div className="rounded-xl border-2 border-dashed border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-earth-800 p-12 text-center">
          <GraduationCap aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No skills found. Create your first skill to get started.
          </p>
        </div>
      )}

      {/* Table */}
      {sortedSkills.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-lsc-border bg-lsc-white dark:border-earth-700 dark:bg-earth-800 shadow-sm">
          <table className="w-full">
            <thead className="border-b border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Proficiency Levels
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Assessments
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {sortedSkills.map((skill) => (
                <tr
                  key={skill.id}
                  className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
                >
                  <td className="px-6 py-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream align-top">
                    <div>{skill.name}</div>
                    {/*
                     * Wave 5: lazy disclosure of courses that build this
                     * skill. Collapsed by default; expanding it triggers
                     * GET /api/v1/learning/skills/{id}/courses on first
                     * open and caches the result.
                     */}
                    <SkillCoursesDisclosure skill={skill} />
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className="inline-block rounded-full bg-lsc-cream dark:bg-lsc-brown/30 px-3 py-1 text-xs font-medium text-lsc-rose dark:text-lsc-cream">
                      {skill.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex flex-wrap gap-2">
                      {skill.proficiency_levels?.map((level) => (
                        <span
                          key={level}
                          className={`inline-block rounded-full px-2 py-1 text-xs font-medium capitalize ${
                            level === 'beginner'
                              ? 'bg-lsc-cream text-lsc-dark dark:bg-lsc-brown dark:text-earth-300'
                              : level === 'intermediate'
                              ? 'bg-lsc-cream text-lsc-rose dark:bg-lsc-dark/30 dark:text-lsc-rose-light'
                              : 'bg-lsc-cream text-lsc-rose dark:bg-lsc-brown/30 dark:text-lsc-rose-light'
                          }`}
                        >
                          {level}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <button
                      onClick={() => onAssessmentClick(skill)}
                      className="hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
                    >
                      {skill.assessments_count} question{skill.assessments_count !== 1 ? 's' : ''}
                    </button>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => onViewClick(skill)}
                        className="rounded-xl p-2 text-lsc-rose hover:bg-lsc-cream dark:text-lsc-rose-light dark:hover:bg-lsc-brown transition-colors"
                        title="View progress"
                      >
                        <Eye aria-hidden="true" className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onEditClick(skill)}
                        className="rounded-xl p-2 text-lsc-rose hover:bg-lsc-cream dark:text-lsc-rose-light dark:hover:bg-lsc-brown transition-colors"
                        title="Edit skill"
                      >
                        <Edit aria-hidden="true" className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteSkillConfirm({ id: skill.id, name: skill.name })}
                        disabled={deleting === skill.id}
                        className="rounded-xl p-2 text-status-danger-600 hover:bg-status-danger-50 dark:bg-status-danger-900/20 disabled:opacity-50 dark:text-status-danger-400 dark:hover:bg-lsc-brown transition-colors"
                        aria-label={`Delete skill ${skill.name}`}
                      >
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer info */}
      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Showing {sortedSkills.length} of {skills.length} skills
      </div>

      <ConfirmDialog
        isOpen={!!deleteSkillConfirm}
        title="Delete Skill?"
        message={`Are you sure you want to delete "${deleteSkillConfirm?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteSkillConfirm) handleDelete(deleteSkillConfirm.id) }}
        onCancel={() => setDeleteSkillConfirm(null)}
        loading={!!deleting}
      />
    </div>
  );
};
