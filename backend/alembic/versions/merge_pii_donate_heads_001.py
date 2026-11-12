"""merge pii-encryption and donate_config heads

Revision ID: merge_pii_donate_001
Revises: donate_config_001, pii_dob_encrypt_001
Create Date: 2026-06-11

Both chains branch from l30_waitlist_001: the PII-at-rest chain
(pii_name_encrypt_001 -> pii_email_encrypt_001 -> pii_dob_encrypt_001) and the
donate-config chain (series_position_001 -> donate_config_001). They touch
disjoint tables (users vs library_branding), so this is a no-op merge that just
reunifies the revision graph to a single head.
"""
from typing import Sequence, Union


revision: str = "merge_pii_donate_001"
down_revision: Union[str, Sequence[str], None] = ("donate_config_001", "pii_dob_encrypt_001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
