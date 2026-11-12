/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle2, Circle, Lock, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

interface PathStep {
  courseId: number
  title: string
  status: 'completed' | 'in_progress' | 'locked' | 'available'
  completedAt?: string
}

interface LearningPathRoadmapProps {
  steps: PathStep[]
}

const STATUS_CONFIG = {
  completed: {
    icon: CheckCircle2,
    iconClass: 'text-status-success-600 dark:text-status-success-400',
    lineClass: 'border-status-success-300 dark:border-status-success-700',
    bgClass: '',
    label: 'Completed',
  },
  in_progress: {
    icon: ArrowRight,
    iconClass: 'text-lsc-rose dark:text-lsc-rose-light',
    lineClass: 'border-lsc-rose/30',
    bgClass: 'ring-2 ring-lsc-rose/30 bg-lsc-rose/5 dark:bg-lsc-rose/10',
    label: 'In progress',
  },
  locked: {
    icon: Lock,
    iconClass: 'text-earth-400 dark:text-earth-600',
    lineClass: 'border-earth-200 dark:border-earth-700 border-dashed',
    bgClass: 'opacity-60',
    label: 'Locked',
  },
  available: {
    icon: Circle,
    iconClass: 'text-earth-400 dark:text-earth-500',
    lineClass: 'border-earth-200 dark:border-earth-700',
    bgClass: '',
    label: 'Available',
  },
}

export default function LearningPathRoadmap({ steps }: LearningPathRoadmapProps) {
  if (steps.length === 0) return null

  return (
    <ol className="relative space-y-0" aria-label="Learning path progress">
      {steps.map((step, idx) => {
        const config = STATUS_CONFIG[step.status]
        const Icon = config.icon
        const isLast = idx === steps.length - 1
        const isClickable = step.status !== 'locked'

        const content = (
          <div className={`flex items-center gap-3 p-3 rounded-lg ${config.bgClass}`}>
            <div className="flex-shrink-0">
              <Icon className={`w-5 h-5 ${config.iconClass}`} aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
                {step.title}
              </p>
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                {step.status === 'completed' && step.completedAt
                  ? `Completed ${new Date(step.completedAt).toLocaleDateString()}`
                  : config.label}
              </p>
            </div>
          </div>
        )

        return (
          <li key={step.courseId} aria-label={`${step.title} - ${config.label}`}>
            {isClickable ? (
              <Link to={`/learn/course/${step.courseId}`} className="block hover:bg-lsc-cream/50 dark:hover:bg-earth-800/50 rounded-lg transition-colors">
                {content}
              </Link>
            ) : (
              content
            )}
            {!isLast && (
              <div className={`ml-[22px] h-4 border-l-2 ${config.lineClass}`} aria-hidden="true" />
            )}
          </li>
        )
      })}
    </ol>
  )
}

export type { PathStep }
