/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useRef } from 'react';
import { Search, Filter, Loader2, Users } from 'lucide-react';
import type { UserSkillProgress, ProficiencyLevel } from './types';
import { skillsApi } from './api';
import { Modal } from '../ui/Modal';
import { useTranslation } from '@/i18n'

interface Props {
  isOpen: boolean;
  skillId: string | null;
  skillName: string | null;
  onClose: () => void;
  onShowToast?: (message: string, type: 'success' | 'error') => void;
}

interface FiltersState {
  search: string;
  proficiency: ProficiencyLevel | '';
}

const PROFICIENCY_COLORS: Record<ProficiencyLevel, { bg: string; text: string; dot: string }> = {
  beginner: {
    bg: 'bg-lsc-cream dark:bg-lsc-brown',
    text: 'text-lsc-dark dark:text-lsc-cream',
    dot: 'bg-lsc-rose',
  },
  intermediate: {
    bg: 'bg-lsc-cream dark:bg-lsc-dark/30',
    text: 'text-lsc-rose dark:text-lsc-rose-light',
    dot: 'bg-lsc-rose',
  },
  advanced: {
    bg: 'bg-lsc-cream dark:bg-lsc-brown/30',
    text: 'text-lsc-rose dark:text-lsc-rose-light',
    dot: 'bg-lsc-rose',
  },
};

export const SkillUserProgress: React.FC<Props> = ({ isOpen, skillId, skillName, onClose, onShowToast }) => {
  const { t } = useTranslation()
  const [users, setUsers] = useState<UserSkillProgress[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<FiltersState>({
    search: '',
    proficiency: '',
  });

  // Track mounted state to prevent state updates after unmount
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const loadUserProgress = React.useCallback(async () => {
    try {
      setLoading(true);
      const data = await skillsApi.getUserProgress(skillId!);
      if (mountedRef.current) {
        setUsers(data);
      }
    } catch (_err) {
      if (mountedRef.current) {
        const errorMessage = _err instanceof Error ? _err.message : 'Failed to load staff progress';
        onShowToast?.(errorMessage, 'error');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [skillId, onShowToast]);

  useEffect(() => {
    if (isOpen && skillId) {
      loadUserProgress();
    }
  }, [isOpen, skillId, loadUserProgress]);

  const filteredUsers = users
    .filter((user) => {
      const matchesSearch = user.user_name.toLowerCase().includes(filters.search.toLowerCase());
      const matchesProficiency = !filters.proficiency || user.current_proficiency === filters.proficiency;
      return matchesSearch && matchesProficiency;
    })
    .sort((a, b) => {
      const proficiencyOrder = { beginner: 1, intermediate: 2, advanced: 3 };
      const profDiff = proficiencyOrder[b.current_proficiency] - proficiencyOrder[a.current_proficiency];
      if (profDiff !== 0) return profDiff;
      return a.user_name.localeCompare(b.user_name);
    });

  const getProficiencyBadgeColor = (level: ProficiencyLevel) => {
    return PROFICIENCY_COLORS[level];
  };

  const getProgressPercentage = (user: UserSkillProgress): number => {
    if (user.total_assessments === 0) return 0;
    return Math.round((user.assessments_passed / user.total_assessments) * 100);
  };

  if (!isOpen || !skillId) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Staff Progress"
      size="2xl"
    >
      {/* Subtitle */}
      <div className="mb-6 pb-4 border-b border-lsc-border dark:border-earth-700">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{skillName}</p>
      </div>

      {/* Filters */}
      <div className="mb-6 space-y-3 rounded-xl bg-lsc-cream dark:bg-lsc-brown/50 p-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-3 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={t('components.training.skillUserProgress.searchStaffByName')}
            aria-label={t('components.training.skillUserProgress.searchStaffByName2')}
            value={filters.search}
            onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
            className="w-full rounded-xl border border-lsc-border bg-lsc-white py-2.5 pl-10 pr-4 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
          />
        </div>

        {/* Proficiency Filter */}
        <div className="flex items-center gap-2">
          <Filter aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <select
            id="proficiency-level-filter"
            aria-label={t('components.training.skillUserProgress.filterByProficiencyLevel')}
            value={filters.proficiency}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                proficiency: e.target.value as FiltersState['proficiency'],
              }))
            }
            className="flex-1 rounded-xl border border-lsc-border bg-lsc-white px-3 py-2.5 text-lsc-dark dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
          >
            <option value="">All Proficiency Levels</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
        </div>
      )}

      {/* Empty state */}
      {!loading && users.length === 0 && (
        <div className="rounded-xl border-2 border-dashed border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50 p-12 text-center">
          <Users aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.training.skillUserProgress.noStaffHaveStartedThis')}</p>
        </div>
      )}

      {/* No results */}
      {!loading && users.length > 0 && filteredUsers.length === 0 && (
        <div className="rounded-xl border-2 border-dashed border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50 p-12 text-center">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.training.skillUserProgress.noStaffMatchYourFilters')}</p>
        </div>
      )}

      {/* Table */}
      {!loading && filteredUsers.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-lsc-border dark:border-earth-700">
          <table className="w-full">
            <thead className="border-b border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Staff Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Proficiency Level
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Assessments Passed
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70">
                  Last Assessed
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border bg-lsc-white dark:divide-earth-700 dark:bg-earth-800">
              {filteredUsers.map((user) => {
                const colors = getProficiencyBadgeColor(user.current_proficiency);
                const progressPercent = getProgressPercentage(user);
                const lastAssessedDate = user.last_assessed ? new Date(user.last_assessed) : null;

                return (
                  <tr key={user.user_id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {user.user_name}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 ${colors.bg}`}>
                        <span className={`h-2 w-2 rounded-full ${colors.dot}`}></span>
                        <span className={`capitalize font-medium ${colors.text}`}>
                          {user.current_proficiency}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                      <div className="flex items-center gap-2">
                        <span>
                          {user.assessments_passed}/{user.total_assessments}
                        </span>
                        {user.total_assessments > 0 && (
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-lsc-cream dark:bg-lsc-brown">
                            <div
                              className={`h-full ${
                                progressPercent >= 80
                                  ? 'bg-lsc-rose'
                                  : progressPercent >= 50
                                    ? 'bg-lsc-rose'
                                    : 'bg-status-danger-500'
                              }`}
                              style={{ width: `${progressPercent}%` }}
                            ></div>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 overflow-hidden rounded-full bg-lsc-cream dark:bg-lsc-brown">
                          <div
                            className={`h-full ${
                              user.score >= 80
                                ? 'bg-lsc-rose'
                                : user.score >= 50
                                  ? 'bg-lsc-rose'
                                  : 'bg-status-danger-500'
                            }`}
                            style={{ width: `${Math.min(user.score, 100)}%` }}
                          ></div>
                        </div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{user.score.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {lastAssessedDate ? (
                        <>
                          <div>{lastAssessedDate.toLocaleDateString()}</div>
                          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {lastAssessedDate.toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                        </>
                      ) : (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Not yet assessed</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 flex items-center justify-between pt-6 border-t border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Showing {filteredUsers.length} of {users.length} staff
        </div>
        <button
          onClick={onClose}
          className="rounded-xl border border-lsc-border px-6 py-2.5 font-medium text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:text-lsc-cream/70 dark:hover:bg-lsc-brown transition-colors"
        >
          Close
        </button>
      </div>
    </Modal>
  );
};
