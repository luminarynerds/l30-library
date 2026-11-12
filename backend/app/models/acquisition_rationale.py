# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class BehaviorTag(Base):
    __tablename__ = 'behavior_tags'

    id = Column(Integer, primary_key=True)
    slug = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SignalType(StrEnum):
    DESK_QUESTION = 'desk_question'
    PURCHASE_REQUEST = 'purchase_request'
    AGENT_CONVERSATION = 'agent_conversation'
    STAFF_OBSERVATION = 'staff_observation'
    REVIEW_PUBLICATION = 'review_publication'
    AWARDS_LIST = 'awards_list'
    BANNED_ELSEWHERE = 'banned_elsewhere'
    COMMUNITY_REQUEST = 'community_request'
    GAP_IN_COLLECTION = 'gap_in_collection'
    REPLACEMENT = 'replacement'
    OTHER = 'other'


class WeedingCondition(StrEnum):
    EPHEMERAL_2YR = 'ephemeral_2yr'
    CURRENT_5YR = 'current_5yr'
    FOUNDATIONAL_INDEFINITE = 'foundational_indefinite'
    CIRC_THRESHOLD = 'circ_threshold'
    DAMAGED_ONLY = 'damaged_only'
    SIGNAL_PERSISTENCE = 'signal_persistence'
    NEVER_WEED = 'never_weed'


class AcquisitionRationale(TimestampMixin, Base):
    __tablename__ = 'acquisition_rationales'

    id = Column(Integer, primary_key=True)
    catalog_item_id = Column(
        Integer, ForeignKey('catalog_items.id', ondelete='CASCADE'),
        unique=True, nullable=False,
    )
    created_by_id = Column(
        Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
    )

    signal_type = Column(
        SQLEnum(
            SignalType,
            name='signaltype',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    signal_ref_table = Column(String(50), nullable=True)
    signal_ref_id = Column(Integer, nullable=True)
    signal_note = Column(Text, nullable=True)

    policy_clause = Column(String(100), nullable=True)

    primary_use_case_slug = Column(
        String(64),
        ForeignKey('behavior_tags.slug', ondelete='RESTRICT'),
        nullable=False,
    )
    secondary_use_case_slugs = Column(ARRAY(String(64)), nullable=False, default=list)

    weeding_condition = Column(
        SQLEnum(
            WeedingCondition,
            name='weedingcondition',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False, default=WeedingCondition.CURRENT_5YR,
    )
    weeding_signal_note = Column(Text, nullable=True)

    anticipated_challenge_reasons = Column(ARRAY(String(64)), nullable=False, default=list)
    anticipated_challenge_acknowledged = Column(Boolean, nullable=False, default=False)

    patron_visible = Column(Boolean, nullable=False, default=False)
    public_summary = Column(Text, nullable=True)

    catalog_item = relationship('CatalogItem', back_populates='acquisition_rationale')
    primary_use_case = relationship('BehaviorTag', foreign_keys=[primary_use_case_slug])
    created_by = relationship('User', foreign_keys=[created_by_id])
