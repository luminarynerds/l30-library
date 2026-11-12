/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Comprehensive Volunteer Management Frontend Components
 *
 * Features:
 * - Volunteer profile creation and management
 * - Application submission and tracking
 * - Background check status
 * - Training completion records
 * - Shift scheduling and sign-up
 * - Hour logging and tracking
 * - Skill profile and matching
 * - Milestone achievements (100 hours!)
 * - Communication history
 * - Recognition and appreciation
 * - Reference letter generation
 * - Volunteer dashboard
 */

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Calendar, Clock, Award, CheckCircle2, AlertCircle, TrendingUp, Gift, MapPin } from 'lucide-react'
import { volunteerApi } from '@/api/domains/admin/volunteer-api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { getVolunteerRoles, getSkillLevels } from '@/api/staff-api/volunteers';
import type { VolunteerRoleOption, SkillLevelOption } from '@/api/staff-api/volunteers';
import { useTranslation} from '@/i18n'
import { t } from '@/i18n'
import { parseDate } from '@/utils/format-utils';

// ============================================================================
// TypeScript Interfaces
// ============================================================================

interface Milestone {
  id: number
  milestone_type: string
  achieved_at?: string
}

interface VolunteerProfile {
  id: number
  name?: string
  primary_role_category: string
  status: string
  phone?: string
  max_hours_per_week: number
  joined_at?: string
  total_hours?: number
  total_shifts?: number
}

interface Shift {
  id: number
  title: string
  description?: string
  shift_date: string
  start_time: string
  end_time?: string
  location?: string
  spots_available?: number
  status?: string
}

interface ShiftSignup {
  id: number
  shift_id: number
  status: string
  shift?: Shift
}

interface HourLog {
  id: number
  activity_type: string
  date: string
  hours: number
  status: string
}

interface Training {
  id: number
  training_type: string | null
  status: string
  completed_at?: string
  expires_at?: string
}

interface Skill {
  id: number
  skill_name: string
  proficiency_level: string
}

interface SkillMatch {
  id: number
  match_score: number
  matched_skills: string[]
}

interface Appreciation {
  id: number
  appreciation_type: string
  description?: string
  given_at: string
  made_public?: boolean
}

// ============================================================================
// Volunteer Dashboard Component
// ============================================================================

// Plain-language labels for HourLogStatus enum values.
const HOUR_LOG_STATUS_LABELS: Record<string, string> = {
  pending: 'Draft',
  submitted: 'Awaiting verification',
  verified: 'Verified',
  rejected: 'Not approved',
}

// Plain-language labels for VolunteerStatus enum values.
const VOLUNTEER_STATUS_LABELS: Record<string, string> = {
  pending_background: 'Background check pending',
  pending_training: 'Training pending',
  pending_approval: 'Awaiting approval',
  active: 'Active',
  inactive: 'Inactive',
  on_leave: 'On leave',
  suspended: 'Suspended',
  terminated: 'No longer volunteering',
}

export const VolunteerDashboard: React.FC = () => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { t: _t } = useTranslation()
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch volunteer profile
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['volunteer', 'profile'],
    queryFn: () => volunteerApi.getVolunteerProfile(),
  });

  const hasProfile = Boolean(profile?.id);

  // Fetch milestones (only if profile exists)
  const { data: milestones } = useQuery({
    queryKey: ['volunteer', 'milestones'],
    queryFn: () => volunteerApi.getMilestones(),
    enabled: hasProfile,
  });

  // Fetch hours summary (only if profile exists)
  const { data: hoursSummary } = useQuery({
    queryKey: ['volunteer', 'hours'],
    queryFn: () => volunteerApi.getHoursSummary(),
    enabled: hasProfile,
  });

  // Fetch volunteer roles configuration
  const { data: volunteerRoles } = useQuery({
    queryKey: ['volunteer', 'config', 'roles'],
    queryFn: () => getVolunteerRoles(''),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch skill levels configuration
  const { data: skillLevels } = useQuery({
    queryKey: ['volunteer', 'config', 'skill-levels'],
    queryFn: () => getSkillLevels(''),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (profileLoading) {
    return <div>Loading volunteer profile...</div>;
  }

  if (!hasProfile) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center space-y-4">
        <h2 className="text-2xl font-serif font-bold">Volunteer with us</h2>
        <p className="text-earth-600 dark:text-earth-400">
          You don't have a volunteer profile yet. Apply to become a volunteer
          and you'll be able to sign up for shifts, log hours, and track
          milestones here.
        </p>
        <a
          href="/volunteer/apply"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-accent text-white hover:opacity-90"
        >
          Apply to volunteer
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Hours"
          value={profile?.total_hours || 0}
          icon={<Clock className="h-4 w-4" />}
          color="accent"
        />
        <StatCard
          title="Shifts Completed"
          value={profile?.total_shifts || 0}
          icon={<Calendar className="h-4 w-4" />}
          color="success"
        />
        <StatCard
          title="Status"
          value={VOLUNTEER_STATUS_LABELS[profile?.status ?? ''] ?? profile?.status ?? 'Unknown'}
          icon={<CheckCircle2 className="h-4 w-4" />}
          color="category"
        />
        <StatCard
          title="Pending Hours"
          value={hoursSummary?.pending_hours || 0}
          icon={<AlertCircle className="h-4 w-4" />}
          color="warning"
        />
      </div>

      {/* Milestones Section */}
      {milestones && milestones.length > 0 && (
        <Card className="border-2 border-status-warning-300 dark:border-status-warning-700 bg-status-warning-50 dark:bg-status-warning-900/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5 text-status-warning-600" />
              Milestone Achievements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {milestones.map((milestone: Milestone) => (
                <Badge key={milestone.id} className="bg-status-warning-600">
                  {milestone.milestone_type.replace(/_/g, ' ')}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="shifts">Shifts</TabsTrigger>
          <TabsTrigger value="hours">Hours</TabsTrigger>
          <TabsTrigger value="training">Training</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="recognition">Recognition</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <OverviewTab profile={profile} />
        </TabsContent>

        <TabsContent value="shifts" className="space-y-4">
          <ShiftsTab availableRoles={volunteerRoles || []} />
        </TabsContent>

        <TabsContent value="hours" className="space-y-4">
          <HoursTab />
        </TabsContent>

        <TabsContent value="training" className="space-y-4">
          <TrainingTab />
        </TabsContent>

        <TabsContent value="skills" className="space-y-4">
          <SkillsTab availableSkillLevels={skillLevels || []} />
        </TabsContent>

        <TabsContent value="recognition" className="space-y-4">
          <RecognitionTab />
        </TabsContent>
      </Tabs>
    </div>
  );
};

// ============================================================================
// Overview Tab
// ============================================================================

const OverviewTab: React.FC<{ profile: VolunteerProfile }> = ({ profile }) => {
  const rows: Array<[string, React.ReactNode]> = [
    ['Name', profile?.name || '—'],
    ['Primary role', <span key="role" className="capitalize">{(profile?.primary_role_category ?? '').replace(/_/g, ' ')}</span>],
    ['Status', <Badge key="status">{VOLUNTEER_STATUS_LABELS[profile?.status ?? ''] ?? profile?.status}</Badge>],
    ['Phone', profile?.phone || '—'],
    ['Max hours/week', `${profile?.max_hours_per_week ?? '—'} hours`],
    ['Joined', profile?.joined_at ? new Date(profile.joined_at).toLocaleDateString() : '—'],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Information</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-x-10 gap-y-3 sm:grid-cols-2">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-baseline justify-between gap-4 border-b border-lsc-border/60 pb-2">
              <dt className="text-sm text-earth-600 dark:text-earth-400">{label}</dt>
              <dd className="text-sm text-right">{value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// Shifts Tab
// ============================================================================

interface ShiftsTabProps {
  availableRoles?: VolunteerRoleOption[];
}

const ShiftsTab: React.FC<ShiftsTabProps> = ({ availableRoles = [] }) => {
  const [showSignupDialog, setShowSignupDialog] = useState(false);
  const [roleFilter, setRoleFilter] = useState('');
  const queryClient = useQueryClient();

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data: shifts, isLoading: _isLoading } = useQuery({
    queryKey: ['volunteer', 'shifts', 'available', roleFilter],
    queryFn: () => volunteerApi.getAvailableShifts(roleFilter || undefined) as Promise<Shift[]>,
  });

  const { data: myShifts } = useQuery({
    queryKey: ['volunteer', 'shifts', 'my'],
    queryFn: () => volunteerApi.getMyShifts(),
  });

  const signupMutation = useMutation({
    mutationFn: (shiftId: number) => volunteerApi.signupForShift(shiftId),
    onSuccess: () => {
      toast.success('Signed up for shift');
      queryClient.invalidateQueries({ queryKey: ['volunteer', 'shifts'] });
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : 'Could not sign up for shift');
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-serif text-lg font-semibold">Available Shifts</h3>
        <Button onClick={() => setShowSignupDialog(true)}>Find Shifts</Button>
      </div>

      <ShiftList
        shifts={shifts || []}
        onSignup={(shiftId) => signupMutation.mutate(shiftId)}
        signupPending={signupMutation.isPending}
      />

      {myShifts && myShifts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>My Upcoming Shifts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {myShifts.map((signup: ShiftSignup) => (
                <div key={signup.id} className="flex justify-between items-center p-2 border rounded">
                  <div>
                    <p className="font-medium">{signup.shift?.title ?? '—'}</p>
                    <p className="text-sm text-earth-600 dark:text-earth-400">
                      {parseDate(signup.shift?.shift_date ?? '')?.toLocaleDateString() ?? '-'} {signup.shift?.start_time}
                    </p>
                  </div>
                  <Badge>{signup.status}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <ShiftSignupDialog
        open={showSignupDialog}
        onOpenChange={setShowSignupDialog}
        availableRoles={availableRoles}
        onSearch={(role) => {
          setRoleFilter(role);
          setShowSignupDialog(false);
        }}
      />
    </div>
  );
};

const ShiftList: React.FC<{
  shifts: Shift[];
  onSignup: (shiftId: number) => void;
  signupPending?: boolean;
}> = ({ shifts, onSignup, signupPending = false }) => {
  if (shifts.length === 0) {
    return <p className="text-sm text-earth-600 dark:text-earth-400">No open shifts right now. Check back soon.</p>;
  }
  return (
    <div className="grid grid-cols-1 gap-3">
      {shifts.map((shift: Shift) => (
        <Card key={shift.id}>
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-serif font-semibold">{shift.title}</h4>
                <p className="text-sm text-earth-600 dark:text-earth-400">{shift.description}</p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-earth-600 dark:text-earth-400">
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                    {parseDate(shift.shift_date)?.toLocaleDateString() ?? '-'}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                    {shift.start_time} – {shift.end_time}
                  </span>
                  {shift.location && (
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                      {shift.location}
                    </span>
                  )}
                </div>
                <div className="mt-2">
                  <span className="text-sm">
                    {shift.spots_available} spots available
                  </span>
                </div>
              </div>
              <Button size="sm" disabled={signupPending} onClick={() => onSignup(shift.id)}>
                Sign Up
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

interface ShiftSignupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availableRoles?: VolunteerRoleOption[];
  onSearch: (roleFilter: string) => void;
}

const ShiftSignupDialog: React.FC<ShiftSignupDialogProps> = ({
  open,
  onOpenChange,
  availableRoles = [],
  onSearch,
}) => {
  const { t } = useTranslation()
  const [roleFilter, setRoleFilter] = useState('');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('components.volunteerManagement.findAndSignUpFor')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger>
              <SelectValue placeholder={t('placeholder.volunteerManagement.filterByRole')} />
            </SelectTrigger>
            <SelectContent>
              {availableRoles.length > 0 ? (
                availableRoles.map((role) => (
                  <SelectItem key={role.key} value={role.key}>
                    {role.label}
                  </SelectItem>
                ))
              ) : (
                <>
                  <SelectItem value="delivery">Delivery</SelectItem>
                  <SelectItem value="programming">Programming</SelectItem>
                  <SelectItem value="shelving">Shelving</SelectItem>
                  <SelectItem value="reader_advisory">Reader Advisory</SelectItem>
                  <SelectItem value="administrative">Administrative</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
          <Button className="w-full" onClick={() => onSearch(roleFilter)}>Search Shifts</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ============================================================================
// Hours Tab
// ============================================================================

const HoursTab: React.FC = () => {
  const [showLogDialog, setShowLogDialog] = useState(false);

  const { data: hourLogs } = useQuery({
    queryKey: ['volunteer', 'hours', 'logs'],
    queryFn: () => volunteerApi.getHourLogs(),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-serif text-lg font-semibold">Hour Logs</h3>
        <Button onClick={() => setShowLogDialog(true)}>Log Hours</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Hour Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">Verified Hours</p>
              <p className="text-3xl font-bold">{hourLogs?.total_verified_hours || 0}</p>
            </div>
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">Pending Hours</p>
              <p className="text-3xl font-bold text-status-warning-600">{hourLogs?.pending_hours || 0}</p>
            </div>
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">Status</p>
              <p className="text-sm mt-2">
                <TrendingUp className="h-4 w-4 inline mr-1" />
                On Track
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {hourLogs?.logs && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Logs</CardTitle>
          </CardHeader>
          <CardContent>
            {hourLogs.logs.length === 0 && (
              <p className="text-sm text-earth-600 dark:text-earth-400">
                No hours logged yet. Use "Log Hours" above to record your first shift.
              </p>
            )}
            <div className="space-y-2">
              {hourLogs.logs.map((log: HourLog) => (
                <div key={log.id} className="flex justify-between items-center p-2 border rounded">
                  <div>
                    <p className="font-medium capitalize">{log.activity_type.replace(/_/g, ' ')}</p>
                    <p className="text-sm text-earth-600 dark:text-earth-400">{log.date}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{log.hours}h</p>
                    <Badge variant={log.status === 'verified' ? 'default' : 'outline'}>
                      {HOUR_LOG_STATUS_LABELS[log.status] ?? log.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <HourLogDialog open={showLogDialog} onOpenChange={setShowLogDialog} />
    </div>
  );
};

const HourLogDialog: React.FC<{ open: boolean; onOpenChange: (open: boolean) => void }> = ({
  open,
  onOpenChange,
}) => {
  const { t } = useTranslation()
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    date: new Date().toISOString().slice(0, 10),
    hours: '',
    activity_type: 'shift_work',
    description: '',
  });

  // Same query the dashboard runs; served from cache.
  const { data: profile } = useQuery({
    queryKey: ['volunteer', 'profile'],
    queryFn: () => volunteerApi.getVolunteerProfile(),
  });

  const logMutation = useMutation({
    mutationFn: () =>
      volunteerApi.logHours(profile.id, {
        log_date: formData.date,
        hours: parseFloat(formData.hours),
        activity_type: formData.activity_type,
        description: formData.description || undefined,
      }),
    onSuccess: () => {
      toast.success('Hours logged — staff will verify them soon');
      queryClient.invalidateQueries({ queryKey: ['volunteer', 'hours'] });
      setFormData({
        date: new Date().toISOString().slice(0, 10),
        hours: '',
        activity_type: 'shift_work',
        description: '',
      });
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : 'Could not log hours');
    },
  });

  const hoursValue = parseFloat(formData.hours);
  const canSubmit = Boolean(profile?.id) && !Number.isNaN(hoursValue) && hoursValue > 0 && !logMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Log Volunteer Hours</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label htmlFor="hour-log-date" className="text-sm font-medium">Date</label>
            <Input
              id="hour-log-date"
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="hour-log-hours" className="text-sm font-medium">Hours</label>
            <Input
              id="hour-log-hours"
              type="number"
              placeholder={t('placeholder.volunteerManagement.3')}
              step="0.5"
              value={formData.hours}
              onChange={(e) => setFormData({ ...formData, hours: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="hour-log-activity-type" className="text-sm font-medium">Activity Type</label>
            <Select value={formData.activity_type} onValueChange={(value) =>
              setFormData({ ...formData, activity_type: value })
            }>
              <SelectTrigger id="hour-log-activity-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="shift_work">Shift Work</SelectItem>
                <SelectItem value="training">Training</SelectItem>
                <SelectItem value="event">Event</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label htmlFor="hour-log-description" className="text-sm font-medium">Description</label>
            <Textarea
              id="hour-log-description"
              placeholder={t('components.volunteerManagement.whatDidYouDo')}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>
          <Button className="w-full" disabled={!canSubmit} onClick={() => logMutation.mutate()}>
            {logMutation.isPending ? 'Logging…' : 'Log Hours'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ============================================================================
// Training Tab
// ============================================================================

const TrainingTab: React.FC = () => {
  const { t } = useTranslation()
  const { data: trainings } = useQuery({
    queryKey: ['volunteer', 'training'],
    queryFn: () => volunteerApi.getTraining(),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Training Records</CardTitle>
        <CardDescription>{t('components.volunteerManagement.trackYourTrainingCompletionAnd')}</CardDescription>
      </CardHeader>
      <CardContent>
        {(!trainings || trainings.length === 0) && (
          <p className="text-sm text-earth-600 dark:text-earth-400">
            No training assigned yet. Staff will add any required training here.
          </p>
        )}
        <div className="space-y-3">
          {trainings?.map((training: Training) => (
            <div key={training.id} className="flex items-center justify-between p-3 border rounded">
              <div className="flex-1">
                <p className="font-medium">{training.training_type ?? 'Training'}</p>
                <p className="text-sm text-earth-600 dark:text-earth-400">
                  {training.status === 'completed' ? (
                    <>Completed {training.completed_at ? new Date(training.completed_at).toLocaleDateString() : '—'}</>
                  ) : (
                    <>Expires {training.expires_at ? new Date(training.expires_at).toLocaleDateString() : '—'}</>
                  )}
                </p>
              </div>
              <Badge>{training.status}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// Skills Tab
// ============================================================================

interface SkillsTabProps {
  availableSkillLevels?: SkillLevelOption[];
}

const SkillsTab: React.FC<SkillsTabProps> = ({ availableSkillLevels = [] }) => {
  const { t } = useTranslation()
  const [showSkillDialog, setShowSkillDialog] = useState(false);

  const { data: skills } = useQuery({
    queryKey: ['volunteer', 'skills'],
    queryFn: () => volunteerApi.getSkills(),
  });

  const { data: matches } = useQuery({
    queryKey: ['volunteer', 'skill-matches'],
    queryFn: () => volunteerApi.getSkillMatches(),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <h3 className="font-serif text-lg font-semibold">Your Skills</h3>
        <Button onClick={() => setShowSkillDialog(true)}>Add Skill</Button>
      </div>

      {skills && skills.length > 0 ? (
        <Card>
          <CardContent className="pt-4">
            <div className="flex flex-wrap gap-2">
              {skills.map((skill: Skill) => (
                <Badge key={skill.id} variant="outline">
                  {skill.skill_name} ({skill.proficiency_level})
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <p className="text-sm text-earth-600 dark:text-earth-400">
          No skills yet. Add one so staff can match you to volunteer opportunities.
        </p>
      )}

      {matches && matches.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Matched Opportunities</CardTitle>
            <CardDescription>{t('components.volunteerManagement.opportunitiesThatMatchYourSkills')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {matches.map((match: SkillMatch) => (
              <div key={match.id} className="p-3 border rounded">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">Match Score: {match.match_score}%</p>
                    <p className="text-sm text-earth-600 dark:text-earth-400">
                      Matched: {match.matched_skills.join(', ')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <AddSkillDialog open={showSkillDialog} onOpenChange={setShowSkillDialog} availableSkillLevels={availableSkillLevels} />
    </div>
  );
};

interface AddSkillDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availableSkillLevels?: SkillLevelOption[];
}

const AddSkillDialog: React.FC<AddSkillDialogProps> = ({
  open,
  onOpenChange,
  availableSkillLevels = [],
}) => {
  const queryClient = useQueryClient();
  const [skillName, setSkillName] = useState('');
  const [proficiency, setProficiency] = useState('intermediate');
  const [description, setDescription] = useState('');

  const { data: profile } = useQuery({
    queryKey: ['volunteer', 'profile'],
    queryFn: () => volunteerApi.getVolunteerProfile(),
  });

  const addMutation = useMutation({
    mutationFn: () =>
      volunteerApi.addSkill(profile.id, {
        skill_name: skillName.trim(),
        proficiency_level: proficiency,
        description: description.trim() || undefined,
      }),
    onSuccess: () => {
      toast.success('Skill added');
      queryClient.invalidateQueries({ queryKey: ['volunteer', 'skills'] });
      queryClient.invalidateQueries({ queryKey: ['volunteer', 'skill-matches'] });
      setSkillName('');
      setProficiency('intermediate');
      setDescription('');
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : 'Could not add skill');
    },
  });

  const canSubmit = Boolean(profile?.id) && skillName.trim().length > 0 && !addMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a Skill</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Input
            placeholder={t('placeholder.volunteerManagement.skillName')}
            value={skillName}
            onChange={(e) => setSkillName(e.target.value)}
          />
          <Select value={proficiency} onValueChange={setProficiency}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableSkillLevels.length > 0 ? (
                availableSkillLevels.map((level) => (
                  <SelectItem key={level.key} value={level.key}>
                    {level.label}
                  </SelectItem>
                ))
              ) : (
                <>
                  <SelectItem value="beginner">Beginner</SelectItem>
                  <SelectItem value="intermediate">Intermediate</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                  <SelectItem value="expert">Expert</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
          <Textarea
            placeholder={t('placeholder.volunteerManagement.describeYourExperience')}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button className="w-full" disabled={!canSubmit} onClick={() => addMutation.mutate()}>
            {addMutation.isPending ? 'Adding…' : 'Add Skill'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ============================================================================
// Recognition Tab
// ============================================================================

const RecognitionTab: React.FC = () => {
  const { t } = useTranslation()
  const { data: appreciation } = useQuery({
    queryKey: ['volunteer', 'appreciation'],
    queryFn: () => volunteerApi.getAppreciation(),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gift className="h-5 w-5" />
            Recognition & Appreciation
          </CardTitle>
        </CardHeader>
        <CardContent>
          {appreciation && appreciation.length > 0 ? (
            <div className="space-y-3">
              {appreciation.map((record: Appreciation) => (
                <div key={record.id} className="p-3 border rounded">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium capitalize">{record.appreciation_type.replace('_', ' ')}</p>
                      <p className="text-sm text-earth-600 dark:text-earth-400">{record.description}</p>
                      <p className="text-xs mt-1">
                        {new Date(record.given_at).toLocaleDateString()}
                      </p>
                    </div>
                    {record.made_public && (
                      <Badge variant="outline">Public</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t('components.volunteerManagement.noRecognitionYet', 'No recognition yet.')}</p>
              <p className="mt-2 text-sm text-earth-600 dark:text-earth-400">{t('components.volunteerManagement.keepUpGreatWork', 'Keep up the great work!')}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ============================================================================
// Stat Card Component
// ============================================================================

const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}> = ({ title, value, icon, color }) => {
  // Keys match what callers pass (accent/success/category/warning).
  const colorClasses = {
    accent: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light',
    success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300',
    category: 'bg-category-50 dark:bg-category-900/20 text-category-700 dark:text-category-300',
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300',
  };

  return (
    <Card className={colorClasses[color as keyof typeof colorClasses]}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-sm font-medium opacity-70">{title}</p>
            <p className="text-2xl font-bold mt-2 leading-tight break-words capitalize">{value}</p>
          </div>
          <div className="opacity-50 shrink-0">{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
};

export default VolunteerDashboard;
