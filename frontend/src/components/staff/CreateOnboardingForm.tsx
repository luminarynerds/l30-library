/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import toast from 'react-hot-toast';
import { onboardingApi } from '@/api/staff-onboarding-api';
import { Loader2 } from 'lucide-react';
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { StaffPicker } from '@/components/staff/StaffPicker'

interface CreateOnboardingData {
  user_id: number
  position: string
  department: string
  start_date: string
  expected_completion_date: string
  manager_id?: number
  buddy_mentor_id?: number
  probation_end_date?: string
}

interface ApiError {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

interface CreateOnboardingFormProps {
  onSuccess?: () => void;
}

export const CreateOnboardingForm: React.FC<CreateOnboardingFormProps> = ({ onSuccess }) => {
  const { t } = useTranslation()
  const navigate = useNavigate();

  // user_id / manager_id / buddy_mentor_id are stamped by StaffPicker
  // selections (numbers or null). Storing them outside `formData` keeps
  // the string-only handleChange helper simple.
  const [userId, setUserId] = useState<number | null>(null);
  const [managerId, setManagerId] = useState<number | null>(null);
  const [buddyMentorId, setBuddyMentorId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    position: '',
    department: '',
    start_date: '',
    expected_completion_date: '',
    probation_end_date: '',
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateOnboardingData) => onboardingApi.createOnboarding(data),
    onSuccess: (_data) => {
      toast.success(t('toast.staff.onboardingCreatedSuccessfully'));
      onSuccess?.();
      navigate('/staff');
    },
    onError: (error: ApiError) => {
      toast.error(error.response?.data?.detail || t('toast.staff.failedToCreateOnboarding'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (userId === null || !formData.position || !formData.department || !formData.start_date || !formData.expected_completion_date) {
      toast.error(t('components.staff.createOnboardingForm.pleaseFillInAllRequired'));
      return;
    }

    createMutation.mutate(clean({
      user_id: userId,
      position: formData.position,
      department: formData.department,
      start_date: formData.start_date,
      expected_completion_date: formData.expected_completion_date,
      manager_id: managerId ?? undefined,
      buddy_mentor_id: buddyMentorId ?? undefined,
      ...(formData.probation_end_date ? { probation_end_date: formData.probation_end_date } : {}),
    }));
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Start New Onboarding</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Row 1: Staff Member and Position */}
          <div className="grid grid-cols-2 gap-4">
            <StaffPicker
              id="user_id"
              label="Staff Member"
              value={userId}
              onChange={setUserId}
              required
              helpText={t('components.staff.createOnboardingForm.theUniqueIdOfThe')}
              placeholder={t('components.staff.createOnboardingForm.enterStaffMemberId')}
            />
            <div className="space-y-2">
              <Label htmlFor="position" className="font-semibold">
                Position *
              </Label>
              <Input
                id="position"
                placeholder={t('placeholder.staff.egLibrarianReferenceAssistant')}
                value={formData.position}
                onChange={(e) => handleChange('position', e.target.value)}
                required
              />
            </div>
          </div>

          {/* Row 2: Department and Manager */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="department" className="font-semibold">
                Department *
              </Label>
              <Input
                id="department"
                placeholder={t('placeholder.staff.egCirculationReference')}
                value={formData.department}
                onChange={(e) => handleChange('department', e.target.value)}
                required
              />
            </div>
            <StaffPicker
              id="manager_id"
              label="Manager (Optional)"
              value={managerId}
              onChange={setManagerId}
              placeholder={t('components.staff.createOnboardingForm.staffMemberSDirectManager')}
            />
          </div>

          {/* Row 3: Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start_date" className="font-semibold">
                Start Date *
              </Label>
              <Input
                id="start_date"
                type="date"
                value={formData.start_date}
                onChange={(e) => handleChange('start_date', e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="expected_completion_date" className="font-semibold">
                Expected Completion Date *
              </Label>
              <Input
                id="expected_completion_date"
                type="date"
                value={formData.expected_completion_date}
                onChange={(e) => handleChange('expected_completion_date', e.target.value)}
                required
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.createOnboardingForm.typicallyDaysAfterStartDate')}</p>
            </div>
          </div>

          {/* Row 4: Buddy Mentor and Probation End */}
          <div className="grid grid-cols-2 gap-4">
            <StaffPicker
              id="buddy_mentor_id"
              label="Buddy/Mentor (Optional)"
              value={buddyMentorId}
              onChange={setBuddyMentorId}
              placeholder={t('components.staff.createOnboardingForm.idOfAssignedMentor')}
            />
            <div className="space-y-2">
              <Label htmlFor="probation_end_date">{t('components.staff.createOnboardingForm.probationEndDateOptional')}</Label>
              <Input
                id="probation_end_date"
                type="date"
                value={formData.probation_end_date}
                onChange={(e) => handleChange('probation_end_date', e.target.value)}
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.createOnboardingForm.defaultDaysFromStartDate')}</p>
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="flex justify-end gap-3 pt-6 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/staff')}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending}
              className="gap-2"
            >
              {createMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Create Onboarding
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
