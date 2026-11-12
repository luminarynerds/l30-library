/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import toast from 'react-hot-toast';
import {
  createFocusTimeBlock,
  getFocusTimeBlocks,
  getFocusTimeSettings,
  FocusWorkType,
} from '@/api/focus-time-api'
import {
  Loader2,
  Plus,
  Calendar,
  Clock,
  BookOpen,
  Code,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'

interface FocusTimeSchedulerProps {
  onSuccess?: () => void
}

const WORK_TYPE_OPTIONS: { value: FocusWorkType; label: string; icon: React.ReactNode }[] = [
  { value: 'cataloging', label: 'Cataloging', icon: <BookOpen className="w-4 h-4" /> },
  { value: 'programming', label: 'Programming', icon: <Code className="w-4 h-4" /> },
  { value: 'writing', label: 'Writing', icon: <BookOpen className="w-4 h-4" /> },
  { value: 'analysis', label: 'Data Analysis', icon: <BookOpen className="w-4 h-4" /> },
  { value: 'research', label: 'Research', icon: <BookOpen className="w-4 h-4" /> },
  {
    value: 'strategic_planning',
    label: 'Strategic Planning',
    icon: <BookOpen className="w-4 h-4" />,
  },
  {
    value: 'collection_development',
    label: 'Collection Development',
    icon: <BookOpen className="w-4 h-4" />,
  },
  { value: 'training', label: 'Training', icon: <BookOpen className="w-4 h-4" /> },
  {
    value: 'system_maintenance',
    label: 'System Maintenance',
    icon: <Code className="w-4 h-4" />,
  },
  {
    value: 'content_creation',
    label: 'Content Creation',
    icon: <BookOpen className="w-4 h-4" />,
  },
  { value: 'other', label: 'Other', icon: <BookOpen className="w-4 h-4" /> },
]

export const FocusTimeScheduler: React.FC<FocusTimeSchedulerProps> = ({ onSuccess }) => {
  const { t } = useTranslation()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    start_time: '',
    end_time: '',
    work_type: 'cataloging' as FocusWorkType,
    description: '',
    backup_contact_id: '',
    is_recurring: false,
    recurrence_rule: '',
  })

  // Fetch settings
  const { data: settingsData } = useQuery({
    queryKey: ['focusTimeSettings'],
    queryFn: getFocusTimeSettings,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Fetch current blocks
  const { data: blocksData, refetch: refetchBlocks } = useQuery({
    queryKey: ['focusTimeBlocks'],
    queryFn: () => getFocusTimeBlocks(),
    staleTime: 1000 * 60, // 1 minute
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof createFocusTimeBlock>[0]) =>
      createFocusTimeBlock(data),
    onSuccess: () => {
      toast.success(t('components.staff.focusTimeScheduler.focusTimeBlockCreatedSuccessfully'))
      setFormData({
        start_time: '',
        end_time: '',
        work_type: 'cataloging',
        description: '',
        backup_contact_id: '',
        is_recurring: false,
        recurrence_rule: '',
      })
      setShowForm(false)
      refetchBlocks()
      onSuccess?.()
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.staff.failedToCreateFocusTime'))
    },
  })

  const handleInputChange = (
    field: string,
    value: string | boolean
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.start_time || !formData.end_time) {
      toast.error(t('components.staff.focusTimeScheduler.pleaseSelectStartAndEnd'))
      return
    }

    const startTime = new Date(formData.start_time)
    const endTime = new Date(formData.end_time)

    if (endTime <= startTime) {
      toast.error(t('components.staff.focusTimeScheduler.endTimeMustBeAfter'))
      return
    }

    const settings = settingsData?.settings
    if (settings) {
      const durationMinutes = (endTime.getTime() - startTime.getTime()) / (1000 * 60)

      if (durationMinutes < settings.min_duration_minutes) {
        toast.error(t('toast.staff.minimumDurationIsMindurationminutesMinutes', { mindurationminutes: settings.min_duration_minutes }))
        return
      }

      if (durationMinutes > settings.max_duration_hours * 60) {
        toast.error(t('toast.staff.maximumDurationIsMaxdurationhoursHours', { maxdurationhours: settings.max_duration_hours }))
        return
      }
    }

    createMutation.mutate(clean({
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
      work_type: formData.work_type,
      description: formData.description || undefined,
      backup_contact_id: formData.backup_contact_id
        ? parseInt(formData.backup_contact_id)
        : undefined,
      is_recurring: formData.is_recurring,
      recurrence_rule: formData.recurrence_rule || undefined,
    }))
  }

  const settings = settingsData?.settings
  const blocks = blocksData?.blocks || []
  const upcomingBlocks = blocks.filter(
    (b) => new Date(b.start_time) > new Date() && b.status !== 'cancelled'
  )

  return (
    <div className="space-y-4">
      {/* Create New Block Button */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-serif font-bold">Focus Time Management</h2>
        <Button onClick={() => setShowForm(!showForm)} variant="default">
          <Plus className="w-4 h-4 mr-2" />
          Schedule Focus Time
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{t('components.staff.focusTimeScheduler.scheduleProtectedWorkTime')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Work Type */}
              <div className="space-y-2">
                <Label htmlFor="work_type">Work Type *</Label>
                <Select
                  value={formData.work_type}
                  onValueChange={(value) =>
                    handleInputChange('work_type', value as FocusWorkType)
                  }
                >
                  <SelectTrigger id="work_type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WORK_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Date/Time */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="start_time">Start Time *</Label>
                  <Input
                    id="start_time"
                    type="datetime-local"
                    value={formData.start_time}
                    onChange={(e) => handleInputChange('start_time', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="end_time">End Time *</Label>
                  <Input
                    id="end_time"
                    type="datetime-local"
                    value={formData.end_time}
                    onChange={(e) => handleInputChange('end_time', e.target.value)}
                  />
                </div>
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">{t('components.staff.focusTimeScheduler.whatWillYouBeWorking')}</Label>
                <Textarea
                  id="description"
                  placeholder={t('components.staff.focusTimeScheduler.describeYourFocusWork')}
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  rows={3}
                />
              </div>

              {/* Backup Contact */}
              <div className="space-y-2">
                <Label htmlFor="backup_contact">Backup Contact (Optional)</Label>
                <Input
                  id="backup_contact"
                  type="number"
                  placeholder={t('components.staff.focusTimeScheduler.staffMemberIdForEmergencies')}
                  value={formData.backup_contact_id}
                  onChange={(e) => handleInputChange('backup_contact_id', e.target.value)}
                />
              </div>

              {/* Recurring */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_recurring"
                    checked={formData.is_recurring}
                    onChange={(e) => handleInputChange('is_recurring', e.target.checked)}
                  />
                  <Label htmlFor="is_recurring">Make this recurring</Label>
                </div>
                {formData.is_recurring && (
                  <Input
                    placeholder={t('components.staff.focusTimeScheduler.recurrenceRuleEGFreq')}
                    value={formData.recurrence_rule}
                    onChange={(e) => handleInputChange('recurrence_rule', e.target.value)}
                  />
                )}
              </div>

              {/* Info Messages */}
              {settings && (
                <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded p-3">
                  <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
                    {settings.requires_manager_approval
                      ? '✓ Your focus time will require manager approval'
                      : '✓ Your focus time is automatically approved'}
                  </p>
                  <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
                    Min: {settings.min_duration_minutes}min | Max: {settings.max_duration_hours}h
                    | Max {settings.max_blocks_per_week} blocks/week
                  </p>
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 motion-safe:animate-spin" />
                      Scheduling...
                    </>
                  ) : (
                    'Schedule Focus Time'
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Upcoming Focus Blocks */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Your Upcoming Focus Blocks
          </CardTitle>
        </CardHeader>
        <CardContent>
          {upcomingBlocks.length === 0 ? (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.focusTimeScheduler.noUpcomingFocusBlocksScheduled')}</p>
          ) : (
            <div className="space-y-3">
              {upcomingBlocks.map((block) => (
                <div
                  key={block.id}
                  className="border rounded-lg p-4 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          variant={
                            block.status === 'approved'
                              ? 'default'
                              : block.status === 'PENDING_APPROVAL'
                                ? 'secondary'
                                : 'destructive'
                          }
                        >
                          {block.status}
                        </Badge>
                        <span className="font-semibold">
                          {
                            WORK_TYPE_OPTIONS.find((opt) => opt.value === block.work_type)
                              ?.label
                          }
                        </span>
                      </div>
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          {new Date(block.start_time).toLocaleString()} -
                          {new Date(block.end_time).toLocaleTimeString()}
                        </div>
                        {block.description && (
                          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{block.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="ml-4">
                      {block.status === 'approved' ? (
                        <CheckCircle2 className="w-6 h-6 text-status-success-600" />
                      ) : block.status === 'PENDING_APPROVAL' ? (
                        <AlertCircle className="w-6 h-6 text-status-warning-600" />
                      ) : (
                        <AlertCircle className="w-6 h-6 text-status-danger-600" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
