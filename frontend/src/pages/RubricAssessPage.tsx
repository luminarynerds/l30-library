/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, CheckCircle } from 'lucide-react';
import { RubricAssessment } from '../components/rubrics/RubricAssessment';
import { rubricsApi } from '../components/rubrics/api';
import type { Rubric, RubricAssessment as RubricAssessmentType } from '../components/rubrics/types';
import PageContainer from '@/components/layout/PageContainer'

export default function RubricAssessPage() {
  const { rubricId, assessmentId } = useParams<{ rubricId: string; assessmentId?: string }>();
  const navigate = useNavigate();
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [existingAssessment, setExistingAssessment] = useState<RubricAssessmentType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const rubricData = await rubricsApi.get(Number(rubricId));
      setRubric(rubricData);

      if (assessmentId) {
        const assessmentData = await rubricsApi.getAssessment(
          Number(rubricId),
          Number(assessmentId)
        );
        setExistingAssessment(assessmentData);
      }
    } catch (_err) {
      setError(_err instanceof Error ? _err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    if (rubricId) {
      loadData();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rubricId, assessmentId]);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const handleComplete = (assessment: RubricAssessmentType) => {
    setCompleted(true);
    setExistingAssessment(assessment);
  };

  if (loading) {
    return (
      <PageContainer width="wide" className="py-12">
        <div className="text-center">
          <Loader2 className="h-12 w-12 motion-safe:animate-spin text-earth-600 mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p>
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

  if (completed && existingAssessment) {
    return (
      <PageContainer width="wide" className="py-12">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-8 text-center">
          <div className="w-16 h-16 bg-status-success-100 dark:bg-status-success-900/40 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-10 w-10 text-status-success-600 dark:text-status-success-400" />
          </div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Assessment Complete!
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            You've completed your assessment of "{existingAssessment.target_identifier}"
          </p>

          <div className="bg-earth-50 dark:bg-earth-800 rounded-lg p-6 mb-6">
            <div className="text-5xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-2">
              {existingAssessment.percentage}%
            </div>
            <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {existingAssessment.total_score} / {existingAssessment.max_possible_score} points
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to={`/rubrics/${rubric.id}`}
              className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700"
            >
              View Rubric
            </Link>
            <button
              onClick={() => {
                setCompleted(false);
                setExistingAssessment(null);
                navigate(`/rubrics/${rubric.id}/assess`);
              }}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
            >
              Start New Assessment
            </button>
          </div>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer width="wide" className="py-8">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg ${
            toast.type === 'success'
              ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/80 dark:text-status-success-200'
              : 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/80 dark:text-status-danger-200'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Back Link */}
      <Link
        to={`/rubrics/${rubric.id}`}
        className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-white mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to {rubric.title}
      </Link>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {existingAssessment ? 'Edit Assessment' : 'New Assessment'}
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Using: <span className="font-medium">{rubric.title}</span>
        </p>
      </div>

      {/* Assessment Form */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
        <RubricAssessment
          rubric={rubric}
          existingAssessment={existingAssessment}
          showToast={showToast}
          onComplete={handleComplete}
        />
      </div>
    </PageContainer>
  );
}
