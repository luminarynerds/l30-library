# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Training Skills & Gap Analysis API
Handles skills catalog, user skills, assessments, and gap analysis
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.learning import (Course, RoleRequiredSkill, Skill,
                                SkillAssessmentQuestion, UserSkill)
from ...models.user import User
from .auth import get_current_user
from .dependencies import is_admin, is_staff_or_admin

router = APIRouter(prefix="/training", tags=["training"])


# ============ SCHEMAS ============


class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str


class SkillCreate(SkillBase):
    proficiency_levels: List[str] = []


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    proficiency_levels: Optional[List[str]] = None  # Accept but don't store yet


class SkillResponse(SkillBase):
    id: str  # Convert to string for frontend compatibility
    is_active: bool
    created_at: Optional[str] = None  # Format as ISO string
    updated_at: Optional[str] = None  # Format as ISO string
    proficiency_levels: List[str] = []
    assessments_count: int = 0
    associated_courses: List[str] = []  # Optional, for future use

    class Config:
        from_attributes = True


class UserSkillResponse(BaseModel):
    id: int
    user_id: int
    skill_id: int
    current_level: int
    assessed_at: Optional[datetime]
    skill_name: str

    class Config:
        from_attributes = True


class SkillGap(BaseModel):
    skill_id: int
    skill_name: str
    skill_category: str
    current_level: int
    required_level: int
    gap_size: int
    is_mandatory: bool
    priority: str
    recommended_courses: List[dict] = []


class GapAnalysisResponse(BaseModel):
    total_skills_required: int
    skills_at_level: int
    skills_with_gaps: int
    gaps: List[SkillGap]


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"
    options: List[dict] = []
    difficulty_level: int = 1
    explanation: Optional[str] = None
    sort_order: int = 0


class QuestionResponse(BaseModel):
    id: int
    skill_id: int
    question_text: str
    question_type: str
    options: List[dict]
    difficulty_level: int
    explanation: Optional[str]
    sort_order: int

    class Config:
        from_attributes = True


# ============ SKILLS CATALOG ============


@router.get("/skills", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available skills."""
    query = select(Skill).options(selectinload(Skill.questions))

    if active_only:
        query = query.where(Skill.is_active == True)

    if category:
        query = query.where(Skill.category == category)

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Skill.name.ilike(f"%{safe_search}%"))

    result = await db.execute(query.order_by(Skill.category, Skill.name))
    skills = result.scalars().all()

    # Enrich skills with computed fields
    enriched_skills = []
    for skill in skills:
        skill_dict = {
            'id': str(skill.id),  # Convert int to string
            'name': skill.name,
            'description': skill.description,
            'category': skill.category,
            'is_active': skill.is_active,
            'created_at': skill.created_at.isoformat() if skill.created_at else None,
            'updated_at': skill.updated_at.isoformat() if skill.updated_at else None,
            'proficiency_levels': ['beginner', 'intermediate', 'expert'],
            'assessments_count': len(skill.questions) if skill.questions else 0,
            'associated_courses': [],
        }
        enriched_skills.append(SkillResponse(**skill_dict))

    return enriched_skills


# ============ GAP ANALYSIS ============


@router.get("/skills/gap-analysis", response_model=GapAnalysisResponse)
async def get_skill_gap_analysis(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Compare user current skill levels to role requirements.
    Returns skills with gaps and recommended courses.
    """
    if not is_staff_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Staff access required for gap analysis"
        )

    role_name = str(current_user.role)

    requirements_result = await db.execute(
        select(RoleRequiredSkill)
        .options(selectinload(RoleRequiredSkill.skill))
        .where(RoleRequiredSkill.role == role_name)
    )
    requirements = requirements_result.scalars().all()

    if not requirements:
        return GapAnalysisResponse(
            total_skills_required=0, skills_at_level=0, skills_with_gaps=0, gaps=[]
        )

    user_skills_result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == current_user.id)
    )
    user_skills = {
        us.skill_id: us.current_level for us in user_skills_result.scalars().all()
    }

    gaps = []
    skills_at_level = 0

    for req in requirements:
        current_level = user_skills.get(req.skill_id, 0)
        gap_size = req.required_level - current_level

        if gap_size <= 0:
            skills_at_level += 1
            continue

        if req.is_mandatory and gap_size >= 3:
            priority = "high"
        elif req.is_mandatory or gap_size >= 2:
            priority = "medium"
        else:
            priority = "low"

        gaps.append(
            SkillGap(
                skill_id=req.skill_id,
                skill_name=req.skill.name,
                skill_category=req.skill.category,
                current_level=current_level,
                required_level=req.required_level,
                gap_size=gap_size,
                is_mandatory=req.is_mandatory,
                priority=priority,
                recommended_courses=[],
            )
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: (priority_order[x.priority], -x.gap_size))

    return GapAnalysisResponse(
        total_skills_required=len(requirements),
        skills_at_level=skills_at_level,
        skills_with_gaps=len(gaps),
        gaps=gaps,
    )


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get skill details."""
    # Load skill with questions eagerly
    result = await db.execute(
        select(Skill)
        .where(Skill.id == skill_id)
        .options(selectinload(Skill.questions))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Enrich with computed fields
    return SkillResponse(
        id=str(skill.id),  # Convert to string
        name=skill.name,
        description=skill.description,
        category=skill.category,
        is_active=skill.is_active,
        created_at=skill.created_at.isoformat() if skill.created_at else None,
        updated_at=skill.updated_at.isoformat() if skill.updated_at else None,
        proficiency_levels=['beginner', 'intermediate', 'expert'],
        assessments_count=len(skill.questions) if skill.questions else 0,
        associated_courses=[],
    )


@router.post("/skills", response_model=SkillResponse)
async def create_skill(
    skill: SkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new skill (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can create skills")

    existing = await db.execute(select(Skill).where(Skill.name == skill.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Skill with this name already exists"
        )

    # Note: proficiency_levels from frontend is validation data, not stored in DB yet
    # Remove it from the dump before creating the model
    skill_data = skill.model_dump(exclude={'proficiency_levels'})
    db_skill = Skill(**skill_data)
    db.add(db_skill)
    await db.commit()
    await db.refresh(db_skill)

    # Return formatted response
    return SkillResponse(
        id=str(db_skill.id),
        name=db_skill.name,
        description=db_skill.description,
        category=db_skill.category,
        is_active=db_skill.is_active,
        created_at=db_skill.created_at.isoformat() if db_skill.created_at else None,
        updated_at=db_skill.updated_at.isoformat() if db_skill.updated_at else None,
        proficiency_levels=['beginner', 'intermediate', 'expert'],
        assessments_count=0,
        associated_courses=[],
    )


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: int,
    skill_update: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update skill (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can update skills")

    # Load skill with questions eagerly for response
    result = await db.execute(
        select(Skill)
        .where(Skill.id == skill_id)
        .options(selectinload(Skill.questions))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Update fields, excluding proficiency_levels which is validation data
    update_data = skill_update.model_dump(exclude_unset=True, exclude={'proficiency_levels'})
    for field, value in update_data.items():
        setattr(skill, field, value)

    await db.commit()
    await db.refresh(skill)

    # Return formatted response
    return SkillResponse(
        id=str(skill.id),
        name=skill.name,
        description=skill.description,
        category=skill.category,
        is_active=skill.is_active,
        created_at=skill.created_at.isoformat() if skill.created_at else None,
        updated_at=skill.updated_at.isoformat() if skill.updated_at else None,
        proficiency_levels=['beginner', 'intermediate', 'expert'],
        assessments_count=len(skill.questions) if skill.questions else 0,
        associated_courses=[],
    )


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete skill (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can delete skills")

    skill = await get_or_404(db, Skill, skill_id, "Skill not found")

    skill.is_active = False
    await db.commit()

    return {"message": "Skill deactivated"}


# ============ SKILLS SUMMARY (current user) ============


class MySkillsSummary(BaseModel):

    skills_covered: int = Field(
        ...,
        description=(
            "Count of skills where the user is at competent level or above "
            "(current_level >= 3 on the 1-5 scale)."
        ),
    )


@router.get("/skills/me/summary", response_model=MySkillsSummary)
async def get_my_skills_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return a count of the current user's skills at competent level (>=3) or above.

    Used by the staff training dashboard to show real progress metrics
    in place of the previous fake-XP footer.
    """
    result = await db.execute(
        select(func.count(UserSkill.id)).where(
            UserSkill.user_id == current_user.id,
            UserSkill.current_level >= 3,
        )
    )
    count = result.scalar() or 0
    return MySkillsSummary(skills_covered=int(count))


# ============ SKILL QUESTIONS ============


@router.get("/skills/{skill_id}/questions", response_model=List[QuestionResponse])
async def get_skill_questions(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get assessment questions for a skill."""
    result = await db.execute(
        select(SkillAssessmentQuestion)
        .where(SkillAssessmentQuestion.skill_id == skill_id)
        .order_by(SkillAssessmentQuestion.sort_order)
    )
    return result.scalars().all()


@router.post("/skills/{skill_id}/questions", response_model=QuestionResponse)
async def add_skill_question(
    skill_id: int,
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add assessment question to skill (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can add questions")

    skill_result = await db.execute(select(Skill).where(Skill.id == skill_id))
    if not skill_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Skill not found")

    db_question = SkillAssessmentQuestion(skill_id=skill_id, **question.model_dump())
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)

    return db_question


@router.delete("/skills/{skill_id}/questions/{question_id}")
async def delete_skill_question(
    skill_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete assessment question (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can delete questions")

    result = await db.execute(
        select(SkillAssessmentQuestion).where(
            SkillAssessmentQuestion.id == question_id,
            SkillAssessmentQuestion.skill_id == skill_id,
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()

    return {"message": "Question deleted"}


@router.post("/skills/{skill_id}/questions/reorder")
async def reorder_skill_questions(
    skill_id: int,
    order_map: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reorder assessment questions (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admins can reorder questions")

    # Convert keys to integers
    question_ids = [int(qid) for qid in order_map.keys()]

    if not question_ids:
        return {"message": "No questions to reorder"}

    # Fetch all questions in a single query (fixes N+1)
    result = await db.execute(
        select(SkillAssessmentQuestion).where(
            SkillAssessmentQuestion.id.in_(question_ids),
            SkillAssessmentQuestion.skill_id == skill_id,
        )
    )
    questions = {q.id: q for q in result.scalars().all()}

    # Update sort orders in memory
    for question_id, new_order in order_map.items():
        qid = int(question_id)
        if qid in questions:
            questions[qid].sort_order = new_order

    await db.commit()
    return {"message": "Questions reordered"}


# ============ USER SKILLS ============


@router.get("/skills/{skill_id}/users")
async def get_skill_users(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get users with this skill and their levels (staff/admin only)."""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Staff access required")

    result = await db.execute(
        select(UserSkill)
        .where(UserSkill.skill_id == skill_id)
        .order_by(UserSkill.current_level.desc())
    )
    user_skills = result.scalars().all()

    user_ids = [us.user_id for us in user_skills]
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = {u.id: u for u in users_result.scalars().all()}
    else:
        users = {}

    return [
        {
            "user_id": us.user_id,
            "user_name": (
                users[us.user_id].full_name if us.user_id in users else "Unknown"
            ),
            "current_level": us.current_level,
            "assessed_at": us.assessed_at,
        }
        for us in user_skills
    ]
