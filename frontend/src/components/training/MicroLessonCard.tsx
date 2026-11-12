/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * MicroLessonCard - Quick 5-minute micro-lessons
 *
 * Displays bite-sized training content for quick learning sessions.
 * Designed for busy staff who want to learn in small increments.
 */
import { Link } from 'react-router-dom';
import { Clock, Zap, BookOpen, ChevronRight, Play, CheckCircle } from 'lucide-react';
import { t } from '@/i18n'

export interface MicroLesson {
  id: number;
  title: string;
  description: string;
  estimatedMinutes: number;
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  isCompleted?: boolean;
  courseId?: number;
  lessonId?: number;
}

interface MicroLessonCardProps {
  lesson: MicroLesson;
  onStart?: (lesson: MicroLesson) => void;
  variant?: 'compact' | 'full';
}

const difficultyColors = {
  beginner: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  intermediate: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  advanced: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
};

const categoryIcons: Record<string, React.ReactNode> = {
  circulation: <BookOpen className="w-4 h-4" aria-hidden="true" />,
  technology: <Zap className="w-4 h-4" aria-hidden="true" />,
  default: <BookOpen className="w-4 h-4" aria-hidden="true" />,
};

export function MicroLessonCard({ lesson, onStart, variant = 'full' }: MicroLessonCardProps) {
  const isMicroLesson = lesson.estimatedMinutes <= 5;
  const CategoryIcon = categoryIcons[lesson.category] || categoryIcons.default;

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-3 p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/50 transition-colors">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
          {lesson.isCompleted ? (
            <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
          ) : (
            <Zap className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={lesson.title}>
            {lesson.title}
          </h4>
          <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            <Clock className="w-3 h-3" aria-hidden="true" />
            <span>{lesson.estimatedMinutes} min</span>
            {isMicroLesson && (
              <span className="px-1.5 py-0.5 bg-lsc-rose/20 text-lsc-rose rounded text-xs font-medium">
                Quick
              </span>
            )}
          </div>
        </div>
        {lesson.lessonId && lesson.courseId ? (
          <Link
            to={`/learn/course/${lesson.courseId}/lesson/${lesson.lessonId}`}
            className="flex-shrink-0 p-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
            aria-label={`Start ${lesson.title}`}
          >
            <Play className="w-4 h-4" aria-hidden="true" />
          </Link>
        ) : (
          <button
            onClick={() => onStart?.(lesson)}
            className="flex-shrink-0 p-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
            aria-label={`Start ${lesson.title}`}
          >
            <Play className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </div>
    );
  }

  return (
    <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
            {CategoryIcon}
          </div>
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">
            {lesson.category}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${difficultyColors[lesson.difficulty]}`}>
            {lesson.difficulty}
          </span>
          {lesson.isCompleted && (
            <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-label={t('aria.training.completed')} />
          )}
        </div>
      </div>

      <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream mb-2">
        {lesson.title}
      </h3>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 line-clamp-2" title={lesson.description}>
        {lesson.description}
      </p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" aria-hidden="true" />
            {lesson.estimatedMinutes} min
          </span>
          {isMicroLesson && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-lsc-rose/10 text-lsc-rose rounded-full text-xs font-medium">
              <Zap className="w-3 h-3" aria-hidden="true" />
              Quick Win
            </span>
          )}
        </div>

        {lesson.lessonId && lesson.courseId ? (
          <Link
            to={`/learn/course/${lesson.courseId}/lesson/${lesson.lessonId}`}
            className="inline-flex items-center gap-1 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
          >
            {lesson.isCompleted ? 'Review' : 'Start'}
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </Link>
        ) : (
          <button
            onClick={() => onStart?.(lesson)}
            className="inline-flex items-center gap-1 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
          >
            {lesson.isCompleted ? 'Review' : 'Start'}
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </div>
    </article>
  );
}

interface MicroLessonListProps {
  lessons: MicroLesson[];
  title?: string;
  showViewAll?: boolean;
  viewAllLink?: string;
  maxDisplay?: number;
  variant?: 'compact' | 'full';
  onStartLesson?: (lesson: MicroLesson) => void;
}

export function MicroLessonList({
  lessons,
  title = "5-Minute Micro-Lessons",
  showViewAll = false,
  viewAllLink = "/learn/micro-lessons",
  maxDisplay = 3,
  variant = 'full',
  onStartLesson,
}: MicroLessonListProps) {
  const displayLessons = lessons.slice(0, maxDisplay);
  const microLessons = displayLessons.filter(l => l.estimatedMinutes <= 5);

  if (!lessons.length) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <div className="text-center py-8">
          <Zap className="w-12 h-12 mx-auto text-lsc-rose/50 mb-3" aria-hidden="true" />
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            No micro-lessons available
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Check back soon for quick learning opportunities!
          </p>
        </div>
      </div>
    );
  }

  return (
    <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {title}
          </h2>
          {microLessons.length > 0 && (
            <span className="px-2 py-0.5 bg-lsc-rose/10 text-lsc-rose rounded-full text-xs font-medium">
              {microLessons.length} quick
            </span>
          )}
        </div>
        {showViewAll && (
          <Link
            to={viewAllLink}
            className="text-sm text-lsc-rose hover:text-lsc-rose/80 flex items-center gap-1"
          >
            View All
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </Link>
        )}
      </div>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        Quick lessons you can complete in 5 minutes or less. Perfect for a quick learning break!
      </p>

      <div className={variant === 'compact' ? 'space-y-2' : 'grid gap-4 md:grid-cols-2 lg:grid-cols-3'}>
        {displayLessons.map((lesson) => (
          <MicroLessonCard
            key={lesson.id}
            lesson={lesson}
            variant={variant}
            {...(onStartLesson !== undefined ? { onStart: onStartLesson } : {})}
          />
        ))}
      </div>
    </section>
  );
}

export default MicroLessonCard;
