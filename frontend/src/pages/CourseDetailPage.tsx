/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/no-unused-expressions */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { BookOpen, Clock, ChevronDown, ChevronRight, FileText, CheckCircle, AlertTriangle, Lock, ArrowLeft, Download, Star, Share2, MessageSquare, Info, SearchX } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/api';
import { isApiError } from '@/lib/api-client';
import toast from 'react-hot-toast';
import { ModuleSessions } from '../components/learning/ModuleSessions';
import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'
import { useTranslation} from '@/i18n'
import { addToRecentlyViewed } from '../services/learning-storage'
import { CourseThumbnail } from '../components/training'

interface Lesson { id: number; title: string; lesson_type: string; estimated_minutes: number | null; sensory_notes: string | null; is_preview?: boolean; }
interface Module { id: number; title: string; description: string | null; lessons: Lesson[]; }
interface Course { id: number; title: string; description: string | null; estimated_minutes: number | null; sensory_warning: string | null; thumbnail_url?: string | null; modules: Module[]; prerequisite_course_ids?: number[]; }

interface PrerequisiteCourse {
  id: number;
  title: string;
  completed: boolean;
}

interface PrerequisitesStatus {
  prerequisites: PrerequisiteCourse[];
  all_met: boolean;
  missing_count: number;
}

interface CourseReview {
  id: number;
  user_name: string;
  rating: number;
  comment: string;
  created_at: string;
}

interface CourseRatingSummary {
  average_rating: number;
  total_reviews: number;
  rating_distribution: { [key: number]: number };
}

export default function CourseDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated } = useAuth();
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [expandedModules, setExpandedModules] = useState<Set<number>>(new Set());
  const [hasCertificate, setHasCertificate] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [userRating, setUserRating] = useState(0);
  const [userComment, setUserComment] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [ratingSummary, setRatingSummary] = useState<CourseRatingSummary | null>(null);
  const [reviews, setReviews] = useState<CourseReview[]>([]);
  const [reviewsUnavailable, setReviewsUnavailable] = useState(false);
  const [prerequisites, setPrerequisites] = useState<PrerequisitesStatus | null>(null);
  const [loadingPrereqs, setLoadingPrereqs] = useState(false);

  useEffect(() => {
    if (id) {
      // Fetch course details - public endpoint for patron-level courses
      api.get(`${API_BASE}/learning/courses/${id}`).then(data => {
        setCourse(data);
        if (data.modules.length > 0) setExpandedModules(new Set([data.modules[0].id]));

        // Fire-and-forget view tracking for authenticated users. Uses the
        // shared learning-storage helper which posts to /learning/courses/{id}/view
        // AND updates the localStorage recently-viewed list (kept in sync
        // with the lesson-viewer flow).
        if (isAuthenticated && data?.id != null && data?.title) {
          void addToRecentlyViewed({ id: data.id, title: data.title });
        }

        // Fetch prerequisites if course has any
        if (data.prerequisite_course_ids && data.prerequisite_course_ids.length > 0) {
          setLoadingPrereqs(true);
          api.get(`${API_BASE}/learning/courses/${id}/prerequisites`)
            .then(prereqs => setPrerequisites(prereqs))
            .catch(err => Sentry.captureException(err instanceof Error ? err : new Error(String(err))))
            .finally(() => setLoadingPrereqs(false));
        }
      }).catch(err => {
        if (isApiError(err) && err.status === 404) {
          setNotFound(true);
          Sentry.captureMessage(`Course not found: course=${id}`, 'warning');
        } else {
          Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
          setError('Unable to load course');
        }
      }).finally(() => setLoading(false));

      // Only fetch enrollment status for authenticated users
      if (isAuthenticated) {
        api.get(`${API_BASE}/learning/my-courses`).then(courses => {
          const myCourse = courses.find((c: { course: { id: number } }) => c.course.id === Number(id));
          setIsEnrolled(!!myCourse);
          if (myCourse?.enrollment?.completed_at) {
            setHasCertificate(true);
          }
        }).catch((err) => {
          Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        });
      }

      // Fetch course reviews from API
      api.get(`${API_BASE}/learning/courses/${id}/reviews`).then(data => {
        if (data.summary) {
          setRatingSummary(data.summary);
        }
        if (data.reviews) {
          setReviews(data.reviews);
        }
      }).catch((err) => {
        // Reviews endpoint failed - report to Sentry and surface a soft notice in the UI
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        setRatingSummary(null);
        setReviews([]);
        setReviewsUnavailable(true);
      });
    } else { setLoading(false); }
  }, [id, isAuthenticated]);

  const handleSubmitReview = async () => {
    if (userRating === 0) {
      toast.error(t('courseDetail.pleaseSelectARating'));
      return;
    }
    setSubmittingReview(true);
    try {
      await api.post(`${API_BASE}/learning/courses/${id}/reviews`, {
        rating: userRating,
        comment: userComment,
      });
      // Optimistically update the UI
      const newReview: CourseReview = {
        id: Date.now(),
        user_name: 'You',
        rating: userRating,
        comment: userComment,
        created_at: new Date().toISOString().split('T')[0] ?? '',
      };
      setReviews(prev => [newReview, ...prev]);
      setRatingSummary(prev => prev ? {
        ...prev,
        total_reviews: prev.total_reviews + 1,
        average_rating: ((prev.average_rating * prev.total_reviews) + userRating) / (prev.total_reviews + 1),
      } : null);
      setShowReviewForm(false);
      setUserRating(0);
      setUserComment('');
      toast.success(t('courseDetail.thankYouForYourReview'));
    } catch {
      toast.error(t('courseDetail.unableToSubmitReviewPlease'));
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleShareCertificate = async () => {
    const shareUrl = `${window.location.origin}/learn/certificate/${id}`;
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Certificate of Completion - ${course?.title}`,
          text: `I just completed "${course?.title}" at the Library Learning Center!`,
          url: shareUrl,
        });
      } catch {
        // User cancelled or share failed
      }
    } else {
      navigator.clipboard.writeText(shareUrl);
      toast.success(t('courseDetail.certificateLinkCopiedToClipboard'));
    }
  };

  const handleEnroll = async () => {
    setEnrolling(true);
    try {
      await api.post(`${API_BASE}/learning/courses/${id}/enroll`);
      setIsEnrolled(true);
      toast.success(t('courseDetail.successfullyEnrolledInCourse'));
    } catch (err: unknown) {
      const apiErr = err as { status?: number; data?: { detail?: string }; message?: string };
      if (apiErr.status === 400) {
        // Check if this is a prerequisite error
        const detail = apiErr.data?.detail || apiErr.message || '';
        if (detail.toLowerCase().includes('prerequisite')) {
          toast.error(detail);
        } else if (detail.toLowerCase().includes('already enrolled')) {
          setIsEnrolled(true);
        } else {
          toast.error(detail || t('toast.courseDetail.unableToEnrollPleaseTry'));
        }
      } else {
        toast.error(t('courseDetail.unableToEnrollPleaseTry'));
      }
    }
    setEnrolling(false);
  };

  const handleDownloadCertificate = async () => {
    // Binary download (PDF certificate). fetchApi() assumes JSON, so we keep
    // raw fetch here and attach the Bearer token manually via getAccessToken().
    const token = getAccessToken();
    if (!token) {
      return;
    }
    try {
      // eslint-disable-next-line no-restricted-syntax -- Certificate PDF binary download; fetchApi parses JSON
      const response = await fetch(`${API_BASE}/learning/certificates/${id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to download certificate');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `certificate-${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    }
  };

  const toggleModule = (moduleId: number) => setExpandedModules(prev => { const next = new Set(prev); next.has(moduleId) ? next.delete(moduleId) : next.add(moduleId); return next; });
  const totalLessons = course?.modules.reduce((sum, m) => sum + m.lessons.length, 0) || 0;

  if (loading) return <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4"><div className="max-w-4xl mx-auto motion-safe:animate-pulse"><div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded-xl"></div></div></div>;

  if (notFound || (!loading && !course && !error)) return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <Link to="/learn/catalog" className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline mb-6"><ArrowLeft aria-hidden="true" className="w-4 h-4" />{t('courseDetail.backToCatalog', 'Back to Catalog')}</Link>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
          <SearchX aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/50 dark:text-lsc-cream/50 opacity-50 mb-4" />
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('courseDetail.courseNotFound', 'Course not found')}</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('courseDetail.courseNotFoundBody', "This course doesn't exist or may have been removed.")}</p>
          <Link to="/learn/catalog" className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-4 py-2 rounded-lg font-medium">
            <BookOpen aria-hidden="true" className="w-4 h-4" />{t('courseDetail.browseCourses', 'Browse courses')}
          </Link>
        </div>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <Link to="/learn/catalog" className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline mb-6"><ArrowLeft aria-hidden="true" className="w-4 h-4" />{t('courseDetail.backToCatalog', 'Back to Catalog')}</Link>
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 px-4 py-3 rounded-xl">{error}</div>
      </div>
    </div>
  );

  if (!course) return null;

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <Link to="/learn/catalog" className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline mb-6"><ArrowLeft aria-hidden="true" className="w-4 h-4" />{t('courseDetail.backToCatalog', 'Back to Catalog')}</Link>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden mb-8">
          <CourseThumbnail title={course.title} {...(course.thumbnail_url ? { thumbnailUrl: course.thumbnail_url } : {})} size="lg" className="w-full" />
          <div className="p-6 md:p-8">
            <h1 className="text-2xl md:text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">{course.title}</h1>
            {course.description && <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{course.description}</p>}
            {course.sensory_warning && <div className="flex items-start gap-3 bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-800 text-lsc-rose dark:text-lsc-rose-light px-4 py-3 rounded-xl mb-4"><AlertTriangle aria-hidden="true" className="w-5 h-5 mt-0.5" /><div><strong>{t('courseDetail.sensoryNote', 'Sensory Note:')}</strong> {course.sensory_warning}</div></div>}

            {/* Prerequisites Section - Accessible and neurodivergent-friendly */}
            {prerequisites && prerequisites.prerequisites.length > 0 && (
              <div
                className={`mb-6 p-4 rounded-xl border-2 ${
                  prerequisites.all_met
                    ? 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800'
                    : 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800'
                }`}
                role="region"
                aria-label={t('aria.courseDetail.coursePrerequisites')}
              >
                <h2 className="flex items-center gap-2 font-medium text-lsc-dark dark:text-lsc-cream mb-3">
                  <Info aria-hidden="true" className="w-5 h-5" />
                  <span>{t('courseDetail.prerequisites', 'Prerequisites')}</span>
                  {prerequisites.all_met ? (
                    <span className="ml-auto text-sm text-status-success-600 dark:text-status-success-400 flex items-center gap-1">
                      <CheckCircle aria-hidden="true" className="w-4 h-4" />
                      <span>{t('courseDetail.allCompleted', 'All completed')}</span>
                    </span>
                  ) : (
                    <span className="ml-auto text-sm text-status-warning-600 dark:text-status-warning-400">
                      {prerequisites.missing_count} {t('courseDetail.remaining', 'remaining')}
                    </span>
                  )}
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                  {prerequisites.all_met
                    ? t('courseDetail.prereqsAllMet', "Great job! You've completed all prerequisites for this course.")
                    : t('courseDetail.prereqsCompleteFirst', 'Complete these courses first to unlock enrollment:')}
                </p>
                <ul className="space-y-2" aria-label={t('courseDetail.listOfPrerequisiteCourses')}>
                  {prerequisites.prerequisites.map((prereq) => (
                    <li key={prereq.id}>
                      <Link
                        to={`/learn/course/${prereq.id}`}
                        className={`flex items-center gap-3 p-3 rounded-xl transition-colors ${
                          prereq.completed
                            ? 'bg-status-success-100 dark:bg-status-success-900/30 hover:bg-status-success-200 dark:hover:bg-status-success-900/50'
                            : 'bg-lsc-white dark:bg-earth-800 hover:bg-lsc-cream dark:hover:bg-lsc-brown'
                        }`}
                      >
                        {prereq.completed ? (
                          <CheckCircle
                            aria-hidden="true"
                            className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0"
                          />
                        ) : (
                          <Lock
                            aria-hidden="true"
                            className="w-5 h-5 text-status-warning-500 dark:text-status-warning-400 flex-shrink-0"
                          />
                        )}
                        <span className="flex-1 text-lsc-dark dark:text-lsc-cream">
                          {prereq.title}
                        </span>
                        {prereq.completed ? (
                          <span className="text-xs text-status-success-600 dark:text-status-success-400 font-medium">
                            {t('courseDetail.completed', 'Completed')}
                          </span>
                        ) : (
                          <span className="text-xs text-status-warning-600 dark:text-status-warning-400 font-medium">
                            {t('courseDetail.required', 'Required')}
                          </span>
                        )}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {loadingPrereqs && (
              <div className="mb-6 p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <div className="w-4 h-4 border-2 border-lsc-rose border-t-transparent rounded-full motion-safe:animate-spin" aria-hidden="true" />
                  <span>{t('courseDetail.checkingPrerequisites', 'Checking prerequisites...')}</span>
                </div>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6"><span className="flex items-center gap-1"><BookOpen aria-hidden="true" className="w-4 h-4" />{course.modules.length} {t('courseDetail.modules', 'modules')}</span><span className="flex items-center gap-1"><FileText aria-hidden="true" className="w-4 h-4" />{totalLessons} {t('courseDetail.lessons', 'lessons')}</span>{course.estimated_minutes && <span className="flex items-center gap-1"><Clock aria-hidden="true" className="w-4 h-4" />~{course.estimated_minutes} {t('courseDetail.min', 'min')}</span>}</div>
            {isEnrolled ? (
              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-2 text-status-success-600 dark:text-status-success-400"><CheckCircle aria-hidden="true" className="w-5 h-5" />{t('courseDetail.youreEnrolled', "You're enrolled")}</span>
                {course.modules[0]?.lessons[0] && <Link to={`/learn/course/${course.id}/lesson/${course.modules[0].lessons[0].id}`} className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-6 py-2.5 rounded-xl font-medium">{t('courseDetail.startLearning', 'Start Learning')}<ChevronRight aria-hidden="true" className="w-5 h-5" /></Link>}
                {hasCertificate && (
                  <>
                    <button onClick={handleDownloadCertificate} className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-5 py-2.5 rounded-xl font-medium">
                      <Download aria-hidden="true" className="w-4 h-4" />{t('courseDetail.downloadCertificate', 'Download Certificate')}
                    </button>
                    <button onClick={handleShareCertificate} className="inline-flex items-center gap-2 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream px-5 py-2.5 rounded-xl font-medium hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80">
                      <Share2 aria-hidden="true" className="w-4 h-4" />{t('courseDetail.share', 'Share')}
                    </button>
                  </>
                )}
              </div>
            ) : isAuthenticated ? (
              <div className="flex flex-col gap-3">
                {/* Show warning if prerequisites aren't met */}
                {prerequisites && !prerequisites.all_met && (
                  <p className="text-sm text-status-warning-600 dark:text-status-warning-400 flex items-center gap-2" role="alert">
                    <Lock aria-hidden="true" className="w-4 h-4" />
                    {t('courseDetail.completePrereqsFirst', 'Complete the prerequisite courses above before enrolling')}
                  </p>
                )}
                <button
                  onClick={handleEnroll}
                  disabled={enrolling || !!(prerequisites && !prerequisites.all_met)}
                  className="bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-medium w-fit"
                  aria-disabled={!!(prerequisites && !prerequisites.all_met)}
                >
                  {enrolling ? t('courseDetail.enrolling', 'Enrolling...') : t('courseDetail.enrollNowFree', 'Enroll Now')}
                </button>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <Link to="/account" className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-8 py-3 rounded-xl font-medium">
                  {t('courseDetail.signInToEnrollFree', 'Sign In to Enroll')}
                  <ChevronRight aria-hidden="true" className="w-5 h-5" />
                </Link>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('courseDetail.createAFreeAccountTo')}</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
          <div className="p-6 border-b border-lsc-border dark:border-earth-700"><h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('courseDetail.courseContent', 'Course Content')}</h2></div>
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {course.modules.map(module => (
              <div key={module.id}>
                <button onClick={() => toggleModule(module.id)} aria-expanded={expandedModules.has(module.id)} aria-label={`${t('courseDetail.toggle', 'Toggle')} ${module.title} ${t('courseDetail.moduleSingular', 'module')}`} className="w-full px-6 py-4 flex items-center justify-between hover:bg-lsc-cream dark:hover:bg-lsc-brown/50">
                  <div className="flex items-center gap-3">{expandedModules.has(module.id) ? <ChevronDown aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" /> : <ChevronRight aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />}<div className="text-left"><h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{module.title}</h3><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{module.lessons.length} {t('courseDetail.lessons', 'lessons')}</p></div></div>
                </button>
                {expandedModules.has(module.id) && (<>
                  <div className="bg-lsc-cream dark:bg-lsc-dark/50 px-6 py-2">
                    {module.lessons.map((lesson, idx) => (
                      <div key={lesson.id}>
                        {(isEnrolled || lesson.is_preview) ? (
                          <Link to={`/learn/course/${course.id}/lesson/${lesson.id}`} className="flex items-center gap-3 py-3 hover:bg-lsc-white dark:bg-earth-800 dark:hover:bg-lsc-brown rounded-xl px-3 -mx-3 group">
                            <span className="w-6 h-6 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center text-xs">{idx + 1}</span>
                            <FileText aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                            <span className="flex-1 text-lsc-dark dark:text-earth-300 group-hover:text-lsc-rose dark:text-lsc-rose-light">{lesson.title}</span>
                            {!isEnrolled && lesson.is_preview && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400">
                                {t('courseDetail.freePreview', 'Preview')}
                              </span>
                            )}
                            {lesson.estimated_minutes && <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{lesson.estimated_minutes} {t('courseDetail.min', 'min')}</span>}
                          </Link>
                        ) : (
                          <div className="flex items-center gap-3 py-3 px-3 -mx-3 opacity-60"><span className="w-6 h-6 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center text-xs">{idx + 1}</span><FileText aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" /><span className="flex-1 text-lsc-dark dark:text-earth-300">{lesson.title}</span><Lock aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" /></div>
                        )}
                      </div>
                    ))}
                  </div>
                  <ModuleSessions moduleId={module.id} moduleTitle={module.title} />
                </>)}
              </div>
            ))}
          </div>
        </div>

        {/* Ratings & Reviews Section */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden mt-8">
          <div className="p-6 border-b border-lsc-border dark:border-earth-700">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <MessageSquare aria-hidden="true" className="w-5 h-5" />
                {t('courseDetail.ratingsAndReviews', 'Ratings & Reviews')}
              </h2>
              {hasCertificate && !showReviewForm && (
                <button
                  onClick={() => setShowReviewForm(true)}
                  className="text-sm text-lsc-rose hover:underline"
                >
                  {t('courseDetail.writeAReview', 'Write a review')}
                </button>
              )}
            </div>
          </div>

          <div className="p-6">
            {reviewsUnavailable && (
              <div
                role="status"
                className="mb-4 flex items-start gap-2 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 text-status-warning-700 dark:text-status-warning-300 px-4 py-3 rounded-xl text-sm"
              >
                <AlertTriangle aria-hidden="true" className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>Reviews temporarily unavailable. Please try again later.</span>
              </div>
            )}
            {/* Rating Summary */}
            {ratingSummary && ratingSummary.total_reviews > 0 && (
              <div className="flex flex-col sm:flex-row gap-6 mb-6 pb-6 border-b border-lsc-border dark:border-earth-700">
                <div className="text-center">
                  <p className="text-4xl font-bold text-lsc-dark dark:text-lsc-cream">{ratingSummary.average_rating.toFixed(1)}</p>
                  <div className="flex justify-center gap-1 my-2">
                    {[1, 2, 3, 4, 5].map(star => (
                      <Star
                        key={star}
                        className={`w-5 h-5 ${star <= Math.round(ratingSummary.average_rating) ? 'text-status-warning-400 fill-yellow-400' : 'text-lsc-border dark:text-earth-300'}`}
                      />
                    ))}
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{ratingSummary.total_reviews} {t('courseDetail.reviews', 'reviews')}</p>
                </div>
                <div className="flex-1">
                  {[5, 4, 3, 2, 1].map(rating => {
                    const count = ratingSummary.rating_distribution[rating] || 0;
                    const percentage = ratingSummary.total_reviews > 0 ? (count / ratingSummary.total_reviews) * 100 : 0;
                    return (
                      <div key={rating} className="flex items-center gap-2 mb-1">
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-3">{rating}</span>
                        <Star className="w-3 h-3 text-status-warning-400 fill-yellow-400" />
                        <div className="flex-1 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                          <div className="h-full bg-status-warning-400 rounded-full" style={{ width: `${percentage}%` }} />
                        </div>
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 w-8">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Review Form */}
            {showReviewForm && (
              <div className="mb-6 pb-6 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">{t('courseDetail.writeYourReview', 'Write your review')}</h3>
                <div className="flex gap-1 mb-3">
                  {[1, 2, 3, 4, 5].map(star => (
                    <button
                      key={star}
                      onClick={() => setUserRating(star)}
                      className="p-1 hover:scale-110 transition-transform"
                      aria-label={`${t('courseDetail.rate', 'Rate')} ${star} ${t('courseDetail.stars', 'stars')}`}
                    >
                      <Star
                        className={`w-8 h-8 ${star <= userRating ? 'text-status-warning-400 fill-yellow-400' : 'text-lsc-border dark:text-earth-300'}`}
                      />
                    </button>
                  ))}
                </div>
                <textarea
                  value={userComment}
                  onChange={e => setUserComment(e.target.value)}
                  placeholder={t('courseDetail.shareYourThoughtsAboutThis')}
                  className="w-full p-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none h-24"
                />
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={handleSubmitReview}
                    disabled={submittingReview || userRating === 0}
                    className="px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium hover:brightness-90 disabled:opacity-50"
                  >
                    {submittingReview ? t('courseDetail.submitting', 'Submitting...') : t('courseDetail.submitReview', 'Submit Review')}
                  </button>
                  <button
                    onClick={() => { setShowReviewForm(false); setUserRating(0); setUserComment(''); }}
                    className="px-4 py-2 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl"
                  >
                    {t('courseDetail.cancel', 'Cancel')}
                  </button>
                </div>
              </div>
            )}

            {/* Reviews List */}
            {reviews.length > 0 ? (
              <div className="space-y-4">
                {reviews.map(review => (
                  <div key={review.id} className="pb-4 border-b border-lsc-border dark:border-earth-700 last:border-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-lsc-rose/20 flex items-center justify-center">
                          <span className="text-sm font-medium text-lsc-rose">{review.user_name?.charAt(0) ?? '?'}</span>
                        </div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{review.user_name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map(star => (
                          <Star
                            key={star}
                            className={`w-4 h-4 ${star <= review.rating ? 'text-status-warning-400 fill-yellow-400' : 'text-lsc-border dark:text-earth-300'}`}
                          />
                        ))}
                      </div>
                    </div>
                    {review.comment && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{review.comment}</p>
                    )}
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{review.created_at}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-4">{t('courseDetail.noReviewsYetBeThe')}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}