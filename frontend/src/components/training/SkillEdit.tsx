/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import type { Skill, ProficiencyLevel } from './types';
import { skillsApi } from './api';
import { Modal } from '../ui/Modal';
import { useTranslation} from '@/i18n'

interface Props {
  isOpen: boolean;
  skill: Skill | null;
  onClose: () => void;
  onSuccess: () => void;
  onShowToast?: (message: string, type: 'success' | 'error') => void;
}

const PROFICIENCY_LEVELS: ProficiencyLevel[] = ['beginner', 'intermediate', 'advanced'];

export const SkillEdit: React.FC<Props> = ({ isOpen, skill, onClose, onSuccess, onShowToast }) => {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    proficiency_levels: [] as ProficiencyLevel[],
  });
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [proficiencyChanged, setProficiencyChanged] = useState(false);

  const loadSkillData = React.useCallback(async () => {
    try {
      if (!skill) return;
      const fullSkill = await skillsApi.getSkill(skill.id);
      setFormData({
        name: fullSkill.name,
        description: fullSkill.description,
        category: fullSkill.category,
        proficiency_levels: fullSkill.proficiency_levels,
      });
      setProficiencyChanged(false);
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Failed to load skill';
      setErrors({ submit: errorMessage });
      onShowToast?.(errorMessage, 'error');
    } finally {
      setInitialLoading(false);
    }
  }, [skill, onShowToast]);

  useEffect(() => {
    if (isOpen && skill) {
      setInitialLoading(true);
      loadSkillData();
    }
  }, [isOpen, skill, loadSkillData]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Skill name is required';
    }

    if (!formData.category.trim()) {
      newErrors.category = 'Category is required';
    }

    if (formData.proficiency_levels.length === 0) {
      newErrors.proficiency_levels = 'At least one proficiency level must be selected';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm() || !skill) {
      return;
    }

    try {
      setLoading(true);

      await skillsApi.updateSkill(skill.id, {
        id: skill.id,
        name: formData.name.trim(),
        description: formData.description.trim(),
        category: formData.category.trim(),
        proficiency_levels: formData.proficiency_levels,
      });

      onShowToast?.('Skill updated successfully', 'success');
      onSuccess();
      onClose();
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Failed to update skill';
      setErrors({ submit: errorMessage });
      onShowToast?.(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleProficiencyChange = (level: ProficiencyLevel) => {
    const newLevels = formData.proficiency_levels.includes(level)
      ? formData.proficiency_levels.filter((l) => l !== level)
      : [...formData.proficiency_levels, level];

    setFormData((prev) => ({ ...prev, proficiency_levels: newLevels }));

    if (skill && newLevels.length !== skill.proficiency_levels.length) {
      setProficiencyChanged(true);
    } else if (skill) {
      const hasChanged = newLevels.some((l) => !skill.proficiency_levels.includes(l));
      setProficiencyChanged(hasChanged);
    }
  };

  if (!isOpen || !skill) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Skill"
      size="lg"
    >
      {/* Loading state */}
      {initialLoading && (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
        </div>
      )}

      {!initialLoading && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error message */}
          {errors.submit && (
            <div className="rounded-xl border border-status-danger-300 bg-status-danger-50 p-4 text-status-danger-700 dark:border-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-200">
              {errors.submit}
            </div>
          )}

          {/* Proficiency Changed Warning */}
          {proficiencyChanged && (
            <div className="flex gap-3 rounded-xl border border-lsc-border bg-lsc-cream p-4 dark:border-earth-800 dark:bg-lsc-dark/20">
              <AlertCircle aria-hidden="true" className="w-5 h-5 flex-shrink-0 text-lsc-rose dark:text-lsc-rose-light" />
              <div className="text-sm text-lsc-dark dark:text-lsc-rose-light/50">
                <p className="font-medium">Proficiency levels changed</p>
                <p>{t('components.training.skillEdit.staffWhoAlreadyHaveExpertise')}</p>
              </div>
            </div>
          )}

          {/* Skill Name */}
          <div>
            <label className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream/70">
              Skill Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder={t('placeholder.training.egReferenceInterviewTechniques')}
              className="mt-2 w-full rounded-xl border border-lsc-border bg-lsc-white px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-lsc-brown dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream/70">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder={t('components.training.skillEdit.describeWhatThisSkillEncompasses')}
              rows={4}
              className="mt-2 w-full rounded-xl border border-lsc-border bg-lsc-white px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-lsc-brown dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream/70">
              Category *
            </label>
            <input
              type="text"
              value={formData.category}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, category: e.target.value }))
              }
              placeholder={t('placeholder.training.egCirculationReferenceTechnical')}
              className="mt-2 w-full rounded-xl border border-lsc-border bg-lsc-white px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-lsc-brown dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            />
            {errors.category && (
              <p className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{errors.category}</p>
            )}
          </div>

          {/* Proficiency Levels */}
          <div>
            <label className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream/70">
              Proficiency Levels *
            </label>
            <div className="mt-3 space-y-2">
              {PROFICIENCY_LEVELS.map((level) => (
                <label
                  key={level}
                  className={`flex items-center gap-3 rounded-xl border p-4 transition-colors cursor-pointer ${
                    formData.proficiency_levels.includes(level)
                      ? 'border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-dark/20'
                      : 'border-lsc-border hover:bg-lsc-cream dark:border-earth-700 dark:hover:bg-lsc-brown'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={formData.proficiency_levels.includes(level)}
                    onChange={() => handleProficiencyChange(level)}
                    className="h-4 w-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                  />
                  <span className="capitalize text-lsc-dark dark:text-lsc-cream font-medium">
                    {level}
                  </span>
                </label>
              ))}
            </div>
            {errors.proficiency_levels && (
              <p className="mt-2 text-sm text-status-danger-600 dark:text-status-danger-400">{errors.proficiency_levels}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-lsc-border px-4 py-2.5 font-medium text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:text-lsc-cream/70 dark:hover:bg-lsc-brown transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-xl bg-lsc-rose px-4 py-2.5 font-medium text-white hover:bg-lsc-rose disabled:opacity-50 dark:bg-lsc-rose-light dark:hover:bg-lsc-rose transition-colors"
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
};
