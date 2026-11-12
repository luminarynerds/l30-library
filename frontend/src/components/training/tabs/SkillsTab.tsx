/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SkillsTab - Skills training tab for the staff training dashboard.
 *
 * Owns its own skill view state (list/create/edit/assessment/progress) so the
 * parent shell does not need to know about the SkillView state machine.
 */
import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { CheckCircle, XCircle } from 'lucide-react';
import { SkillsList } from '../SkillsList';
import { SkillCreate } from '../SkillCreate';
import { SkillEdit } from '../SkillEdit';
import { SkillAssessment } from '../SkillAssessment';
import { SkillUserProgress } from '../SkillUserProgress';
import type { Skill } from '../types';

type SkillView = 'list' | 'create' | 'edit' | 'assessment' | 'progress';

export function SkillsTab(): React.ReactElement {
  const [skillView, setSkillView] = useState<SkillView>('list');
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [skillListKey, setSkillListKey] = useState(0);

  const showSkillToast = (message: string, type: 'success' | 'error') => {
    if (type === 'success') {
      toast.success(message, {
        icon: <CheckCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose" />,
      });
    } else {
      toast.error(message, {
        icon: <XCircle aria-hidden="true" className="w-5 h-5 text-status-danger-600" />,
      });
    }
  };

  const handleAddSkillClick = () => {
    setSelectedSkill(null);
    setSkillView('create');
  };
  const handleEditSkillClick = (skill: Skill) => {
    setSelectedSkill(skill);
    setSkillView('edit');
  };
  const handleViewSkillClick = (skill: Skill) => {
    setSelectedSkill(skill);
    setSkillView('progress');
  };
  const handleAssessmentSkillClick = (skill: Skill) => {
    setSelectedSkill(skill);
    setSkillView('assessment');
  };
  const handleSkillCreateSuccess = () => {
    setSkillListKey((prev) => prev + 1);
    setSkillView('list');
  };
  const handleSkillEditSuccess = () => {
    setSkillListKey((prev) => prev + 1);
    setSkillView('list');
  };
  const handleCloseSkillModal = () => {
    setSkillView('list');
    setSelectedSkill(null);
  };

  return (
    <>
      {skillView === 'list' && (
        <SkillsList
          key={skillListKey}
          onAddClick={handleAddSkillClick}
          onEditClick={handleEditSkillClick}
          onViewClick={handleViewSkillClick}
          onAssessmentClick={handleAssessmentSkillClick}
        />
      )}
      <SkillCreate
        isOpen={skillView === 'create'}
        onClose={handleCloseSkillModal}
        onSuccess={handleSkillCreateSuccess}
        onShowToast={showSkillToast}
      />
      <SkillEdit
        isOpen={skillView === 'edit'}
        skill={selectedSkill}
        onClose={handleCloseSkillModal}
        onSuccess={handleSkillEditSuccess}
        onShowToast={showSkillToast}
      />
      <SkillAssessment
        isOpen={skillView === 'assessment'}
        skillId={selectedSkill?.id || null}
        skillName={selectedSkill?.name || null}
        onClose={handleCloseSkillModal}
        onSuccess={() => {
          setSkillListKey((prev) => prev + 1);
          setSkillView('list');
        }}
        onShowToast={showSkillToast}
      />
      <SkillUserProgress
        isOpen={skillView === 'progress'}
        skillId={selectedSkill?.id || null}
        skillName={selectedSkill?.name || null}
        onClose={handleCloseSkillModal}
        onShowToast={showSkillToast}
      />
    </>
  );
}
