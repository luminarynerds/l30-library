/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useCallback } from 'react';
import {
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  Info,
  MessageSquare,
  ExternalLink,
} from 'lucide-react';
import type { Rubric, RubricAssessment as RubricAssessmentType, RubricCriterion } from './types';
import { rubricsApi } from './api';
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'

interface Props {
  rubric: Rubric;
  existingAssessment?: RubricAssessmentType | null;
  onSave?: (assessment: RubricAssessmentType) => void;
  onComplete?: (assessment: RubricAssessmentType) => void;
  showToast?: (message: string, type: 'success' | 'error') => void;
}

/**
 * Interactive rubric assessment component.
 * Allows users to score each criterion and add notes.
 */
export const RubricAssessment: React.FC<Props> = ({
  rubric,
  existingAssessment,
  onSave,
  onComplete,
  showToast,
}) => {
  const { t } = useTranslation()
  const [targetIdentifier, setTargetIdentifier] = useState(existingAssessment?.target_identifier || '');
  const [targetDescription, setTargetDescription] = useState(existingAssessment?.target_description || '');
  const [scores, setScores] = useState<Record<string, number>>(existingAssessment?.scores || {});
  const [notes, setNotes] = useState<Record<string, string>>(existingAssessment?.notes || {});
  const [overallNotes, setOverallNotes] = useState(existingAssessment?.overall_notes || '');
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assessmentId, setAssessmentId] = useState<number | null>(existingAssessment?.id || null);
  const [expandedNotes, setExpandedNotes] = useState<Record<string, boolean>>({});

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const criteria = rubric.criteria || [];
  const levels = Object.keys(rubric.level_labels).sort((a, b) => Number(b) - Number(a));

  // Calculate current score
  const calculateScore = useCallback(() => {
    let total = 0;
    let maxPossible = 0;

    criteria.forEach((criterion) => {
      const score = scores[String(criterion.id)] || 0;
      total += score * criterion.weight;
      maxPossible += rubric.max_score * criterion.weight;
    });

    return {
      total,
      maxPossible,
      percentage: maxPossible > 0 ? Math.round((total / maxPossible) * 100) : 0,
    };
  }, [criteria, scores, rubric.max_score]);

  const { total, maxPossible, percentage } = calculateScore();

  // Check if all criteria have been scored
  const allScored = criteria.every((c) => scores[String(c.id)] !== undefined);

  const handleScoreChange = (criterionId: number, score: number) => {
    setScores((prev) => ({
      ...prev,
      [String(criterionId)]: score,
    }));
  };

  const handleNoteChange = (criterionId: number, note: string) => {
    setNotes((prev) => ({
      ...prev,
      [String(criterionId)]: note,
    }));
  };

  const toggleNoteExpand = (criterionId: number) => {
    setExpandedNotes((prev) => ({
      ...prev,
      [String(criterionId)]: !prev[String(criterionId)],
    }));
  };

  const handleSave = async () => {
    if (!targetIdentifier.trim()) {
      setError('Please enter what you are assessing');
      return;
    }

    setError(null);
    setSaving(true);

    try {
      let assessment: RubricAssessmentType;

      if (assessmentId) {
        // Update existing
        assessment = await rubricsApi.updateAssessment(rubric.id, assessmentId, clean({
          target_identifier: targetIdentifier.trim(),
          target_description: targetDescription.trim() || undefined,
          scores,
          notes,
          overall_notes: overallNotes.trim() || undefined,
        }));
      } else {
        // Create new
        assessment = await rubricsApi.createAssessment(rubric.id, clean({
          rubric_id: rubric.id,
          target_identifier: targetIdentifier.trim(),
          target_description: targetDescription.trim() || undefined,
          scores,
          notes,
          overall_notes: overallNotes.trim() || undefined,
        }));
        setAssessmentId(assessment.id);
      }

      showToast?.('Assessment saved', 'success');
      onSave?.(assessment);
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to save';
      setError(message);
      showToast?.(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = async () => {
    if (!targetIdentifier.trim()) {
      setError('Please enter what you are assessing');
      return;
    }

    if (!allScored) {
      setError('Please score all criteria before completing');
      return;
    }

    setError(null);
    setCompleting(true);

    try {
      let assessment: RubricAssessmentType;

      if (assessmentId) {
        assessment = await rubricsApi.updateAssessment(rubric.id, assessmentId, clean({
          target_identifier: targetIdentifier.trim(),
          target_description: targetDescription.trim() || undefined,
          scores,
          notes,
          overall_notes: overallNotes.trim() || undefined,
          is_complete: true,
        }));
      } else {
        assessment = await rubricsApi.createAssessment(rubric.id, clean({
          rubric_id: rubric.id,
          target_identifier: targetIdentifier.trim(),
          target_description: targetDescription.trim() || undefined,
          scores,
          notes,
          overall_notes: overallNotes.trim() || undefined,
        }));
        // Then mark complete
        assessment = await rubricsApi.updateAssessment(rubric.id, assessment.id, {
          is_complete: true,
        });
      }

      showToast?.('Assessment completed!', 'success');
      onComplete?.(assessment);
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to complete';
      setError(message);
      showToast?.(message, 'error');
    } finally {
      setCompleting(false);
    }
  };

  const getScoreColor = (pct: number) => {
    if (pct >= 75) return 'text-status-success-600 dark:text-status-success-400';
    if (pct >= 50) return 'text-status-warning-600 dark:text-status-warning-400';
    return 'text-status-danger-600 dark:text-status-danger-400';
  };

  return (
    <div className="rubric-assessment">
      {/* Header with target info */}
      <div className="mb-6 p-4 bg-earth-50 dark:bg-earth-800/20 rounded-lg border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          Assessment Details
        </h3>
        <div className="space-y-4">
          <div>
            <label
              htmlFor="target-identifier"
              className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
            >
              What are you assessing? *
            </label>
            <input
              id="target-identifier"
              type="text"
              value={targetIdentifier}
              onChange={(e) => setTargetIdentifier(e.target.value)}
              placeholder={t('placeholder.rubrics.egChatgptCopilotMy')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light dark:bg-earth-800 dark:text-lsc-cream"
            />
          </div>
          <div>
            <label
              htmlFor="target-description"
              className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
            >
              Description (optional)
            </label>
            <textarea
              id="target-description"
              value={targetDescription}
              onChange={(e) => setTargetDescription(e.target.value)}
              rows={2}
              placeholder={t('components.rubrics.rubricAssessment.briefDescriptionOfWhatYou')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light dark:bg-earth-800 dark:text-lsc-cream"
            />
          </div>
        </div>
      </div>

      {/* Score Summary */}
      <div className="mb-6 p-4 bg-earth-50 dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Current Score</span>
            <div className={`text-3xl font-bold ${getScoreColor(percentage)}`}>
              {total} / {maxPossible}
            </div>
          </div>
          <div className="text-right">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Percentage</span>
            <div className={`text-3xl font-bold ${getScoreColor(percentage)}`}>
              {percentage}%
            </div>
          </div>
        </div>
        <div className="mt-3 w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              percentage >= 75 ? 'bg-status-success-500' : percentage >= 50 ? 'bg-status-warning-500' : 'bg-status-danger-500'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        {!allScored && (
          <p className="mt-2 text-sm text-status-warning-600 dark:text-status-warning-400 flex items-center gap-1">
            <Info className="h-4 w-4" />
            Score all criteria to complete the assessment
          </p>
        )}
      </div>

      {/* Criteria Assessment */}
      <div className="space-y-6">
        {criteria.map((criterion, idx) => (
          <CriterionAssessment
            key={criterion.id}
            criterion={criterion}
            levels={levels}
            levelLabels={rubric.level_labels}
            {...(scores[String(criterion.id)] !== undefined ? { selectedScore: scores[String(criterion.id)] } : {})}
            note={notes[String(criterion.id)] || ''}
            isNoteExpanded={expandedNotes[String(criterion.id)] || false}
            onScoreChange={(score) => handleScoreChange(criterion.id, score)}
            onNoteChange={(note) => handleNoteChange(criterion.id, note)}
            onToggleNote={() => toggleNoteExpand(criterion.id)}
            index={idx + 1}
          />
        ))}
      </div>

      {/* Overall Notes */}
      <div className="mt-6 p-4 bg-earth-50 dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <label
          htmlFor="overall-notes"
          className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2"
        >
          Overall Notes & Summary
        </label>
        <textarea
          id="overall-notes"
          value={overallNotes}
          onChange={(e) => setOverallNotes(e.target.value)}
          rows={4}
          placeholder={t('components.rubrics.rubricAssessment.addAnyOverallObservationsRecommendations')}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light dark:bg-earth-800 dark:text-lsc-cream"
        />
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg flex items-center gap-2 text-status-danger-700 dark:text-status-danger-300">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-end">
        <button
          onClick={handleSave}
          disabled={saving || completing}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 hover:bg-earth-50 dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <Loader2 className="h-4 w-4 motion-safe:animate-spin motion-reduce:animate-none" aria-hidden="true" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save Draft
        </button>
        <button
          onClick={handleComplete}
          disabled={saving || completing || !allScored}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-lsc-rose hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {completing ? (
            <Loader2 className="h-4 w-4 motion-safe:animate-spin motion-reduce:animate-none" aria-hidden="true" />
          ) : (
            <CheckCircle className="h-4 w-4" />
          )}
          Complete Assessment
        </button>
      </div>

      {/* Attribution */}
      {rubric.source_attribution && (
        <div className="mt-6 pt-4 border-t border-lsc-border dark:border-earth-700 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <p>{rubric.source_attribution}</p>
          {rubric.source_url && (
            <a
              href={rubric.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light mt-1"
            >
              View source <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      )}
    </div>
  );
};

// Sub-component for individual criterion assessment
interface CriterionAssessmentProps {
  criterion: RubricCriterion;
  levels: string[];
  levelLabels: Record<string, string>;
  selectedScore?: number;
  note: string;
  isNoteExpanded: boolean;
  onScoreChange: (score: number) => void;
  onNoteChange: (note: string) => void;
  onToggleNote: () => void;
  index: number;
}

const CriterionAssessment: React.FC<CriterionAssessmentProps> = ({
  criterion,
  levels,
  levelLabels,
  selectedScore,
  note,
  isNoteExpanded,
  onScoreChange,
  onNoteChange,
  onToggleNote,
  index,
}) => {
  const { t } = useTranslation()
  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
      {/* Criterion Header */}
      <div className="bg-earth-100 dark:bg-earth-800 px-4 py-3 flex items-center justify-between">
        <div>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mr-2">
            {index}.
          </span>
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
            {criterion.name}
          </span>
          {criterion.weight > 1 && (
            <span className="ml-2 text-xs bg-earth-100 dark:bg-earth-800 text-lsc-rose dark:text-lsc-rose-light px-2 py-0.5 rounded">
              {criterion.weight}x weight
            </span>
          )}
        </div>
        <button
          onClick={onToggleNote}
          className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
          title="Add note"
        >
          <MessageSquare className={`h-5 w-5 ${note ? 'fill-blue-500 text-earth-600' : ''}`} />
        </button>
      </div>

      {criterion.description && (
        <div className="px-4 py-2 bg-earth-50 dark:bg-earth-800 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700">
          {criterion.description}
        </div>
      )}

      {/* Level Options */}
      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {levels.map((level) => {
            const levelNum = Number(level);
            const isSelected = selectedScore === levelNum;
            const descriptors = criterion.levels[level] || [];

            return (
              <button
                key={level}
                onClick={() => onScoreChange(levelNum)}
                className={`
                  p-3 rounded-lg border-2 text-left transition-all
                  ${
                    isSelected
                      ? 'border-lsc-rose/50 bg-earth-50 dark:bg-earth-800/30'
                      : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-500'
                  }
                `}
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className={`font-semibold ${
                      isSelected ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-lsc-dark dark:text-lsc-cream'
                    }`}
                  >
                    {levelLabels[level] || `Level ${level}`}
                  </span>
                  <span
                    className={`text-lg font-bold ${
                      isSelected ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                    }`}
                  >
                    {level}
                  </span>
                </div>
                <ul className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                  {descriptors.slice(0, 2).map((desc, i) => (
                    <li key={`${level}-desc-${i}-${desc.slice(0, 20)}`} className="truncate" title={desc}>
                      {desc}
                    </li>
                  ))}
                  {descriptors.length > 2 && (
                    <li className="text-lsc-dark/70 dark:text-lsc-cream/70">+{descriptors.length - 2} more...</li>
                  )}
                </ul>
              </button>
            );
          })}
        </div>
      </div>

      {/* Note Section */}
      {isNoteExpanded && (
        <div className="px-4 pb-4">
          <textarea
            value={note}
            onChange={(e) => onNoteChange(e.target.value)}
            rows={2}
            placeholder={t('components.rubrics.rubricAssessment.addNotesForThisCriterion')}
            className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light dark:bg-earth-800 dark:text-lsc-cream"
          />
        </div>
      )}
    </div>
  );
};

export default RubricAssessment;
