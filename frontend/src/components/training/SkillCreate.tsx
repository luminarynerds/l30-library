/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react';
import type { ProficiencyLevel, SkillCreatePayload } from './types';
import { skillsApi } from './api';
import { Modal } from '../ui/Modal';
import { useTranslation} from '@/i18n'

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  onShowToast?: (message: string, type: 'success' | 'error') => void;
}

const PROFICIENCY_LEVELS: ProficiencyLevel[] = ['beginner', 'intermediate', 'advanced'];

export const SkillCreate: React.FC<Props> = ({ isOpen, onClose, onSuccess, onShowToast }) => {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    proficiency_levels: [] as ProficiencyLevel[],
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Please enter a name for this skill.';
    }

    if (!formData.category.trim()) {
      newErrors.category = 'Please choose a category for this skill.';
    }

    if (formData.proficiency_levels.length === 0) {
      newErrors.proficiency_levels = 'Please select at least one proficiency level.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleFieldBlur = (fieldName: string) => {
    setTouched((prev) => ({ ...prev, [fieldName]: true }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setTouched({
      name: true,
      category: true,
      proficiency_levels: true,
    });

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      const payload: SkillCreatePayload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        category: formData.category.trim(),
        proficiency_levels: formData.proficiency_levels,
      };

      await skillsApi.createSkill(payload);

      onShowToast?.('Skill created successfully', 'success');
      setFormData({
        name: '',
        description: '',
        category: '',
        proficiency_levels: [],
      });
      setErrors({});
      setTouched({});
      onSuccess();
      onClose();
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Could not create this skill right now. Please try again.';
      setErrors({ submit: errorMessage });
      onShowToast?.(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleProficiencyChange = (level: ProficiencyLevel) => {
    setFormData((prev) => ({
      ...prev,
      proficiency_levels: prev.proficiency_levels.includes(level)
        ? prev.proficiency_levels.filter((l) => l !== level)
        : [...prev.proficiency_levels, level],
    }));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Skill"
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Submit error */}
        {errors.submit && (
          <div className="rounded-xl border border-status-danger-300 bg-status-danger-50 p-4 text-status-danger-700 dark:border-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-200">
            {errors.submit}
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
            onBlur={() => handleFieldBlur('name')}
            placeholder={t('placeholder.training.egReferenceInterviewTechniques')}
            className={`mt-2 w-full rounded-xl border px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 ${
              touched.name && errors.name
                ? 'border-status-danger-300 bg-status-danger-50 dark:border-status-danger-700 dark:bg-status-danger-900'
                : 'border-lsc-border bg-lsc-white dark:border-earth-700 dark:bg-lsc-brown'
            }`}
            aria-invalid={touched.name && !!errors.name}
            aria-describedby={touched.name && errors.name ? 'name-error' : undefined}
          />
          {touched.name && errors.name && (
            <p id="name-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">
              {errors.name}
            </p>
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
            placeholder={t('components.training.skillCreate.describeWhatThisSkillEncompasses')}
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
            onBlur={() => handleFieldBlur('category')}
            placeholder={t('placeholder.training.egCirculationReferenceTechnical')}
            className={`mt-2 w-full rounded-xl border px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 ${
              touched.category && errors.category
                ? 'border-status-danger-300 bg-status-danger-50 dark:border-status-danger-700 dark:bg-status-danger-900'
                : 'border-lsc-border bg-lsc-white dark:border-earth-700 dark:bg-lsc-brown'
            }`}
            aria-invalid={touched.category && !!errors.category}
            aria-describedby={touched.category && errors.category ? 'category-error' : undefined}
          />
          {touched.category && errors.category && (
            <p id="category-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">
              {errors.category}
            </p>
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
                  touched.proficiency_levels && errors.proficiency_levels
                    ? 'border-status-danger-300 bg-status-danger-50 dark:border-status-danger-700 dark:bg-status-danger-900'
                    : formData.proficiency_levels.includes(level)
                    ? 'border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-dark/20'
                    : 'border-lsc-border hover:bg-lsc-cream dark:border-earth-700 dark:hover:bg-lsc-brown'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.proficiency_levels.includes(level)}
                  onChange={() => {
                    handleProficiencyChange(level);
                    handleFieldBlur('proficiency_levels');
                  }}
                  className="h-4 w-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                <span className="capitalize text-lsc-dark dark:text-lsc-cream font-medium">
                  {level}
                </span>
              </label>
            ))}
          </div>
          {touched.proficiency_levels && errors.proficiency_levels && (
            <p id="proficiency_levels-error" className="mt-2 text-sm text-status-danger-600 dark:text-status-danger-400">
              {errors.proficiency_levels}
            </p>
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
            {loading ? 'Creating...' : 'Create Skill'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
