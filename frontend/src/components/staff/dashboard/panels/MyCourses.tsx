/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { GraduationCap } from 'lucide-react'
import { learningApi, CourseProgress } from '@/components/training/api'

export default function MyCourses() {
  const [courses, setCourses] = useState<CourseProgress[]>([])

  useEffect(() => {
    learningApi.getMyCourses()
      .then(setCourses)
      .catch(() => {})
  }, [])

  const active = courses.filter(c => !c.enrollment.completed_at)
  if (active.length === 0) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5">
          <GraduationCap className="w-3.5 h-3.5" aria-hidden="true" />
          My courses
        </p>
        <Link to="/staff/training" className="text-[11px] text-lsc-rose hover:underline">
          View all
        </Link>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {active.slice(0, 3).map(c => {
          const pct = c.total_lessons > 0 ? Math.round((c.completed_lessons / c.total_lessons) * 100) : 0
          return (
            <Link key={c.course.id} to={`/learn/course/${c.course.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-lsc-dark dark:text-lsc-cream truncate">{c.course.title}</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-1.5 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-lsc-rose rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0">
                    {pct}%
                  </span>
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
