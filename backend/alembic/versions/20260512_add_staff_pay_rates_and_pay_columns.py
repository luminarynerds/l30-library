"""Add staff_pay_rates table, payroll pay columns, system settings reporting fields

Revision ID: 20260512_pay_rates
Revises: mood_categories_001
Create Date: 2026-05-12

"""
from alembic import op
import sqlalchemy as sa

revision = "20260512_pay_rates"
down_revision = "mood_categories_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. staff_pay_rates
    op.create_table(
        "staff_pay_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("hourly_rate > 0", name="ck_staff_pay_rates_positive"),
    )
    op.create_index("ix_staff_pay_rates_staff_effective",
                    "staff_pay_rates", ["staff_id", "effective_from"], unique=False)

    # 2. payroll_records.*_pay columns
    for col in ("hourly_rate_at_pay", "regular_pay", "overtime_pay", "holiday_pay",
                "weekend_differential_pay", "evening_differential_pay", "total_pay"):
        op.add_column("payroll_records", sa.Column(col, sa.Numeric(10, 2), nullable=True))

    # 3. system_settings.fte_annual_hours, .volunteer_hour_value
    op.add_column("system_settings", sa.Column("fte_annual_hours", sa.Integer(), nullable=True, server_default="2080"))
    op.add_column("system_settings", sa.Column("volunteer_hour_value", sa.Numeric(10, 2), nullable=True, server_default="33.49"))


def downgrade() -> None:
    op.drop_column("system_settings", "volunteer_hour_value")
    op.drop_column("system_settings", "fte_annual_hours")
    for col in ("total_pay", "evening_differential_pay", "weekend_differential_pay",
                "holiday_pay", "overtime_pay", "regular_pay", "hourly_rate_at_pay"):
        op.drop_column("payroll_records", col)
    op.drop_index("ix_staff_pay_rates_staff_effective", table_name="staff_pay_rates")
    op.drop_table("staff_pay_rates")
