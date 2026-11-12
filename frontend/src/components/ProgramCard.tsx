/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Calendar, Users, CheckCircle, Pause, Clock, TrendingUp, Flame } from 'lucide-react'
import { ReadingProgram, ReadingRegistration } from '@/api/api'
import { Button } from '@/components/ui/Button'
import { getProgramTypeConfig } from '@/config/program-types'
import { useTranslation } from '@/i18n'

interface ProgramCardProps {
  program: ReadingProgram
  isRegistered?: boolean
  registration?: ReadingRegistration
  onRegister: (program: ReadingProgram) => void
  onClick: () => void
  isFeatured?: boolean
}

export default function ProgramCard({
  program,
  isRegistered = false,
  registration,
  onRegister,
  onClick,
  isFeatured = false,
}: ProgramCardProps): React.ReactElement {
  const { language } = useTranslation()

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(language, { month: 'short', day: 'numeric' })
  }

  const getDaysRemaining = () => {
    const now = new Date()
    const end = new Date(program.end_date)
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
    return diff
  }

  const daysRemaining = getDaysRemaining()
  const isEndingSoon = daysRemaining > 0 && daysRemaining <= 7
  const hasEnded = daysRemaining <= 0

  const programTypeInfo = getProgramTypeConfig(program.program_type)
  const ProgramTypeIcon = programTypeInfo.icon

  const ageDisplay = program.target_age_min && program.target_age_max
    ? `Ages ${program.target_age_min}–${program.target_age_max}`
    : program.age_group || 'All ages'

  const progressPercentage = registration?.progress_percentage ?? 0

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`View details for ${program.name}`}
      className={`bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-5 hover:shadow-md transition-all cursor-pointer border focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:focus-visible:ring-lsc-rose-light ${
        isFeatured
          ? 'border-lsc-rose dark:border-lsc-rose-light ring-2 ring-lsc-rose/20 dark:ring-lsc-rose-light/20'
          : 'border-lsc-border dark:border-earth-700'
      } ${isEndingSoon && !hasEnded ? 'border-l-4 border-l-status-warning-500' : ''}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.()
        }
      }}
    >
      <div className="space-y-3">
        {/* Featured badge */}
        {isFeatured && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-lsc-rose dark:text-lsc-rose-light">
            <Flame className="w-3.5 h-3.5" aria-hidden="true" />
            Popular Program
          </div>
        )}

        {/* Header with type and badge */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className={`text-xs font-medium mb-1.5 flex items-center gap-1.5 w-fit px-2 py-0.5 rounded-full ${programTypeInfo.bgColor} ${programTypeInfo.textColor}`}>
              <ProgramTypeIcon className="w-3 h-3" aria-hidden="true" />
              {programTypeInfo.label}
            </div>
            <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream line-clamp-2" title={program.name}>
              {program.name}
            </h3>
          </div>
          {isRegistered && (
            <div className="flex-shrink-0">
              <div className="flex items-center gap-1 px-2 py-1 bg-status-success-100 dark:bg-status-success-900/30 rounded-full">
                <CheckCircle className="w-4 h-4 text-status-success-700 dark:text-status-success-400" aria-hidden="true" />
                <span className="text-xs font-medium text-status-success-700 dark:text-status-success-400">Joined</span>
              </div>
            </div>
          )}
        </div>

        {/* Description */}
        {program.description && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={program.description}>
            {program.description}
          </p>
        )}

        {/* Progress bar for registered users */}
        {isRegistered && registration && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5" aria-hidden="true" />
                Your Progress
              </span>
              <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{Math.round(progressPercentage)}%</span>
            </div>
            <div className="h-2.5 bg-lsc-cream dark:bg-lsc-brown/50 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-lsc-rose to-lsc-rose-light rounded-full transition-all duration-500"
                style={{ width: `${Math.min(progressPercentage, 100)}%` }}
              />
            </div>
            {registration.total_books > 0 && (
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/75">
                {registration.total_books} book{registration.total_books !== 1 ? 's' : ''} · {registration.total_minutes} min read
              </div>
            )}
          </div>
        )}

        {/* Urgency indicator */}
        {isEndingSoon && !hasEnded && program.is_active && (
          <div className="px-3 py-2 bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-400 text-xs font-medium rounded-lg flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            {daysRemaining === 1 ? 'Ends tomorrow!' : `Only ${daysRemaining} days left!`}
          </div>
        )}

        {/* Compact meta row — replaces the old 4-cell grid */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            {formatDate(program.start_date)} – {formatDate(program.end_date)}
          </span>
          <span className="flex items-center gap-1">
            <Users className="w-3.5 h-3.5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            {ageDisplay}
          </span>
          <span className="flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            {program.registration_count} participant{program.registration_count !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Status indicator */}
        {!program.is_active && (
          <div className="px-3 py-2 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs font-medium rounded-lg flex items-center gap-1">
            <Pause className="w-3 h-3" aria-hidden="true" />
            Not currently active
          </div>
        )}

        {/* Action button */}
        {!isRegistered && program.is_active && (() => {
          const now = new Date()
          const start = new Date(program.start_date)
          const hasStarted = now >= start
          return hasStarted ? (
            <Button variant="primary"
              onClick={(e) => {
                e.stopPropagation()
                onRegister(program)
              }}
            >
              Join Program
            </Button>
          ) : (
            <div className="px-3 py-2 bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs font-medium rounded-lg text-center">
              Registration opens {start.toLocaleDateString(language, { month: 'short', day: 'numeric' })}
            </div>
          )
        })()}
      </div>
    </div>
  )
}
