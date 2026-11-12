/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, PlayCircle, ClipboardList, Download } from 'lucide-react';
import { RubricViewer } from '../components/rubrics/RubricViewer';
import { rubricsApi } from '../components/rubrics/api';
import type { Rubric, RubricAssessment } from '../components/rubrics/types';
import PageContainer from '@/components/layout/PageContainer'

export default function RubricDetailPage() {
  const { rubricId } = useParams<{ rubricId: string }>();
  const navigate = useNavigate();
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [assessments, setAssessments] = useState<RubricAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'view' | 'assessments'>('view');

  const loadAssessments = async () => {
    try {
      const data = await rubricsApi.listAssessments(Number(rubricId));
      setAssessments(data);
    } catch {
      // User might not be logged in, which is fine - silently skip loading assessments
    }
  };


  const loadRubric = async () => {
    try {
      setLoading(true);
      const data = await rubricsApi.get(Number(rubricId));
      setRubric(data);
    } catch (_err) {
      setError(_err instanceof Error ? _err.message : 'Failed to load rubric');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    if (rubricId) {
      loadRubric();
      loadAssessments();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rubricId]);

  const handleExportCSV = () => {
    if (!rubric) return;

    const levels = Object.keys(rubric.level_labels).sort((a, b) => Number(b) - Number(a));
    const criteria = rubric.criteria || [];

    // Build CSV content
    const headers = ['Criteria', ...levels.map((l) => `${rubric.level_labels[l]} (${l})`)];
    const rows = criteria.map((c) => {
      return [
        c.name,
        ...levels.map((l) => (c.levels[l] || []).join('; ')),
      ];
    });

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')),
    ].join('\n');

    // Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${rubric.title.replace(/[^a-z0-9]/gi, '_')}_rubric.csv`;
    link.click();
  };

  if (loading) {
    return (
      <PageContainer width="wide" className="py-12">
        <div className="text-center">
          <Loader2 className="h-12 w-12 motion-safe:animate-spin text-earth-600 mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading rubric...</p>
        </div>
      </PageContainer>
    );
  }

  if (error || !rubric) {
    return (
      <PageContainer width="wide" className="py-12">
        <div className="text-center">
          <p className="text-status-danger-500 mb-4">{error || 'Rubric not found'}</p>
          <Link to="/rubrics" className="text-lsc-rose dark:text-lsc-rose-light hover:underline">
            Back to Rubrics
          </Link>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer width="wide" className="py-8">
      {/* Back Link */}
      <Link
        to="/rubrics"
        className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-white mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Rubrics
      </Link>

      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('view')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'view'
                ? 'bg-earth-100 text-lsc-rose dark:bg-earth-800/40 dark:text-lsc-rose-light'
                : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
            }`}
          >
            View Rubric
          </button>
          <button
            onClick={() => setActiveTab('assessments')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'assessments'
                ? 'bg-earth-100 text-lsc-rose dark:bg-earth-800/40 dark:text-lsc-rose-light'
                : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
            }`}
          >
            <ClipboardList className="h-4 w-4" />
            My Assessments
            {assessments.length > 0 && (
              <span className="bg-earth-500 text-white text-xs px-2 py-0.5 rounded-full">
                {assessments.length}
              </span>
            )}
          </button>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
          <button
            onClick={() => navigate(`/rubrics/${rubric.id}/assess`)}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 flex items-center gap-2"
          >
            <PlayCircle className="h-4 w-4" />
            Start Assessment
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'view' && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
          <RubricViewer rubric={rubric} />
        </div>
      )}

      {activeTab === 'assessments' && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            My Assessments
          </h2>

          {assessments.length === 0 ? (
            <div className="text-center py-8">
              <ClipboardList className="h-12 w-12 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                You haven't completed any assessments with this rubric yet.
              </p>
              <button
                onClick={() => navigate(`/rubrics/${rubric.id}/assess`)}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
              >
                Start Your First Assessment
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {assessments.map((assessment) => (
                <div
                  key={assessment.id}
                  className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 cursor-pointer"
                  onClick={() => navigate(`/rubrics/${rubric.id}/assess/${assessment.id}`)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => navigate(`/rubrics/${rubric.id}/assess/${assessment.id}`))(); } }}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {assessment.target_identifier}
                      </h3>
                      {assessment.target_description && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {assessment.target_description}
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <div
                        className={`text-lg font-bold ${
                          assessment.percentage && assessment.percentage >= 75
                            ? 'text-status-success-600 dark:text-status-success-400'
                            : assessment.percentage && assessment.percentage >= 50
                            ? 'text-status-warning-600 dark:text-status-warning-400'
                            : 'text-status-danger-600 dark:text-status-danger-400'
                        }`}
                      >
                        {assessment.percentage !== undefined ? `${assessment.percentage}%` : 'In Progress'}
                      </div>
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {assessment.total_score} / {assessment.max_possible_score}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span>
                      {assessment.is_complete ? (
                        <span className="text-status-success-600 dark:text-status-success-400">Completed</span>
                      ) : (
                        <span className="text-status-warning-600 dark:text-status-warning-400">Draft</span>
                      )}
                    </span>
                    <span>
                      {new Date(assessment.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </PageContainer>
  );
}
