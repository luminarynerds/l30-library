/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AssignCourseModal — manager-driven course assignment (Wave 4).
 *
 * Wraps the staff portal's `<Modal>` (which already handles ESC dismissal,
 * focus trap, focus restore on close, body scroll lock). We layer:
 *   - Initial focus on the course `<select>` when the modal opens.
 *   - Plain-language labels ("Assign training", "Required") per CLAUDE.md
 *     accessibility guidance — never "Create enrollment record".
 *   - A `role="alert"` region above the form for submit failures so AT
 *     users get the error announced without polling.
 *   - `aria-busy` on the submit button while the request is pending.
 *
 * The native `<input type="date">` and `<select>` are intentional — replacing
 * them with custom widgets risks trapping keyboard focus, which is
 * particularly bad for ND users.
 *
 * Internal note: the form is split into a child component (`AssignCourseForm`)
 * keyed by `member.user_id`. Mount/unmount, not effects, drives state reset —
 * sidesteps the "setState in useEffect" anti-pattern flagged by lint.
 */
import React, { useMemo, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Modal } from '@/components/ui/Modal';
import {
  learningApi,
  type CourseListItem,
  type TeamMemberProgress,
} from '../api';

export interface AssignCourseModalProps {
  isOpen: boolean;
  member: TeamMemberProgress | null;
  onClose: () => void;
  /** Called after a successful assignment so the parent can refetch. */
  onSuccess: () => void;
}

export function AssignCourseModal({
  isOpen,
  member,
  onClose,
  onSuccess,
}: AssignCourseModalProps): React.ReactElement | null {
  if (!isOpen || member == null) return null;
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Assign training to ${member.name}`}
      size="md"
    >
      {/*
        `key` forces a clean remount per member — fresh local state without
        a useEffect/setState dance. Closing the modal also unmounts the
        form (since the parent passes `isOpen=false`), so any in-flight
        local UI state is discarded.
      */}
      <AssignCourseForm
        key={member.user_id}
        member={member}
        onClose={onClose}
        onSuccess={onSuccess}
      />
    </Modal>
  );
}

interface AssignCourseFormProps {
  member: TeamMemberProgress;
  onClose: () => void;
  onSuccess: () => void;
}

function AssignCourseForm({
  member,
  onClose,
  onSuccess,
}: AssignCourseFormProps): React.ReactElement {
  const queryClient = useQueryClient();
  const courseSelectRef = useRef<HTMLSelectElement | null>(null);

  const [courseId, setCourseId] = React.useState<number | ''>('');
  const [dueDate, setDueDate] = React.useState<string>('');
  const [isRequired, setIsRequired] = React.useState<boolean>(true);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const { data: allCourses = [], isLoading: coursesLoading } = useQuery<
    CourseListItem[]
  >({
    queryKey: ['all-courses'],
    queryFn: learningApi.getAllCourses,
    retry: 1,
  });

  // Alphabetical-by-title for predictable scanning. We sort defensively
  // in case the API ever changes order.
  const sortedCourses = useMemo(
    () => [...allCourses].sort((a, b) => a.title.localeCompare(b.title)),
    [allCourses],
  );

  // Initial focus: the spec wants the course select focused on open.
  // <Modal>'s FocusTrap handles trap + restore-on-close; we just supplement
  // initial focus here. No setState involved → not flagged by lint.
  useEffect(() => {
    const handle = window.setTimeout(() => {
      courseSelectRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(handle);
  }, []);

  const assignMutation = useMutation({
    mutationFn: () => {
      if (courseId === '') {
        throw new Error('Pick a course before assigning.');
      }
      return learningApi.assignCourse({
        user_id: member.user_id,
        course_id: Number(courseId),
        // Empty string from the date input → omit. Otherwise interpret as
        // start-of-day local time, then ISO-stringify.
        due_at: dueDate
          ? new Date(`${dueDate}T00:00:00`).toISOString()
          : null,
        is_required: isRequired,
      });
    },
    onSuccess: () => {
      const courseTitle =
        sortedCourses.find((c) => c.id === Number(courseId))?.title ??
        'training';
      toast.success(`Assigned ${courseTitle} to ${member.name}.`);
      queryClient.invalidateQueries({ queryKey: ['team-progress'] });
      onSuccess();
      onClose();
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "We couldn't assign that training. Please try again.";
      setErrorMessage(message);
    },
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (courseId === '') {
      setErrorMessage('Pick a course before assigning.');
      return;
    }
    setErrorMessage(null);
    assignMutation.mutate();
  };

  const isPending = assignMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/*
        Submit-failure live region. role="alert" forces AT to announce
        immediately; we still keep it visible so sighted users see it too.
      */}
      {errorMessage && (
        <div
          role="alert"
          className="rounded-lg border border-status-danger-300 dark:border-status-danger-800 bg-status-danger-50 dark:bg-status-danger-900/20 px-3 py-2 text-sm text-status-danger-800 dark:text-status-danger-200"
        >
          {errorMessage}
        </div>
      )}

      <div>
        <label
          htmlFor="assign-course"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream"
        >
          Course
        </label>
        <select
          id="assign-course"
          ref={courseSelectRef}
          aria-label="Select a course"
          value={courseId}
          onChange={(e) =>
            setCourseId(e.target.value === '' ? '' : Number(e.target.value))
          }
          disabled={coursesLoading || isPending}
          required
          className="mt-1 w-full rounded-lg bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-700 px-3 py-2 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">
            {coursesLoading ? 'Loading courses…' : 'Pick a course…'}
          </option>
          {sortedCourses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label
          htmlFor="assign-due-date"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream"
        >
          Due date
        </label>
        <input
          id="assign-due-date"
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          aria-describedby="assign-due-date-hint"
          disabled={isPending}
          className="mt-1 w-full rounded-lg bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-700 px-3 py-2 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        />
        <p
          id="assign-due-date-hint"
          className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          Optional — leave blank for no deadline. The course's default
          duration will apply.
        </p>
      </div>

      <div>
        <label className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
          <input
            type="checkbox"
            checked={isRequired}
            onChange={(e) => setIsRequired(e.target.checked)}
            disabled={isPending}
            className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
          />
          <span className="font-medium">Required</span>
        </label>
        <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          Required training appears in the Required section for the staffer.
        </p>
      </div>

      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onClose}
          disabled={isPending}
          className="px-4 py-2 rounded-lg text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending || courseId === ''}
          aria-busy={isPending}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 disabled:opacity-50"
        >
          {isPending ? 'Assigning…' : 'Assign training'}
        </button>
      </div>
    </form>
  );
}
