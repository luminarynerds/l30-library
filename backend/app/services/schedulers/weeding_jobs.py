# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal
from ...core.email import send_email, COLORS
from ...core.logging import get_logger
from ...models.job_failure import JobSeverity
from ...services.weeding_service import get_weeding_summary, run_weeding_analysis
from ..job_failure_service import JobExecutionContext

settings = get_settings()
logger = get_logger(__name__)


async def scheduled_weeding_analysis() -> None:
    async with JobExecutionContext(
        job_id="scheduled_weeding_analysis",
        job_name="Scheduled Weeding Analysis",
        severity=JobSeverity.LOW,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            from ...models.multi_branch import SystemSettings

            settings_row = await db.execute(
                select(SystemSettings).limit(1)
            )
            org_settings = settings_row.scalar_one_or_none()

            weeding_config: dict = {}
            if org_settings and org_settings.configuration:
                weeding_config = (org_settings.configuration or {}).get(
                    "weeding_schedule", {}
                )

            min_score = float(weeding_config.get("min_crew_score", 50))
            max_results = int(weeding_config.get("max_results", 200))
            notify_email = weeding_config.get("notify_email", "")
            auto_approve_duplicates = weeding_config.get(
                "auto_approve_duplicates", False
            )
            auto_approve_never_circulated = weeding_config.get(
                "auto_approve_never_circulated", False
            )
            never_circ_years = int(
                weeding_config.get("never_circulated_years", 5)
            )

            try:
                candidates = await run_weeding_analysis(
                    db=db,
                    staff_user_id=0,
                    min_crew_score=min_score,
                    max_results=max_results,
                )

                candidates_created = len(candidates)
                auto_approved = 0

                if auto_approve_duplicates or auto_approve_never_circulated:
                    from ...models.weeding import WeedingReason, WeedingStatus

                    for candidate in candidates:
                        should_approve = False

                        if (
                            auto_approve_duplicates
                            and candidate.reason == WeedingReason.DUPLICATE
                        ):
                            should_approve = True

                        if (
                            auto_approve_never_circulated
                            and candidate.never_circulated
                            and candidate.years_since_acquisition is not None
                            and candidate.years_since_acquisition >= never_circ_years
                        ):
                            should_approve = True

                        if should_approve:
                            candidate.status = WeedingStatus.APPROVED
                            candidate.approved_at = datetime.now(timezone.utc)
                            candidate.approval_notes = (
                                "Auto-approved by scheduled weeding analysis"
                            )
                            auto_approved += 1

                    await db.commit()

                summary = await get_weeding_summary(db)

                ctx.record_success()
                ctx.add_metric("candidates_created", candidates_created)
                ctx.add_metric("auto_approved", auto_approved)
                ctx.items_processed = candidates_created
                ctx.items_succeeded = candidates_created

                logger.info(
                    "Scheduled weeding analysis completed",
                    extra={
                        "candidates_created": candidates_created,
                        "auto_approved": auto_approved,
                        "total_active": summary.get("total_candidates", 0),
                    },
                )

                if notify_email:
                    await _send_weeding_analysis_email(
                        email=notify_email,
                        candidates_created=candidates_created,
                        auto_approved=auto_approved,
                        summary=summary,
                    )

            except Exception as e:
                logger.error(
                    f"Scheduled weeding analysis failed: {e}",
                    exc_info=True,
                )
                ctx.record_failure(error=e, entity_type="weeding_analysis")
                raise


async def _send_weeding_analysis_email(
    email: str,
    candidates_created: int,
    auto_approved: int,
    summary: dict,
) -> None:
    subject = f"Weeding Analysis Complete: {candidates_created} new candidates"

    total = summary.get("total_candidates", 0)
    outdated = summary.get("outdated_items", 0)
    duplicates = summary.get("total_duplicates_excess", 0)
    never_circ = summary.get("never_circulated_items", 0)
    sections_over = summary.get("sections_over_capacity", 0)

    auto_line = ""
    if auto_approved > 0:
        auto_line = f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']};">Auto-Approved</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']}; text-align: right; font-weight: bold;">{auto_approved}</td>
        </tr>"""

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Weeding Analysis Report</h2>
        <p>The scheduled weeding analysis has completed. Here is a summary:</p>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']};">New Candidates Found</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']}; text-align: right; font-weight: bold;">{candidates_created}</td>
            </tr>{auto_line}
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']};">Total Active Candidates</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']}; text-align: right; font-weight: bold;">{total}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']};">Outdated Content</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']}; text-align: right;">{outdated}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']};">Excess Duplicates</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']}; text-align: right;">{duplicates}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']};">Never Circulated</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['divider']}; text-align: right;">{never_circ}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px;">Sections Over Capacity</td>
                <td style="padding: 8px 12px; text-align: right;">{sections_over}</td>
            </tr>
        </table>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{settings.frontend_url}/staff/weeding"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Review Candidates
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}<br>
            This is an automated weeding analysis report.
        </p>
    </div>
    """

    try:
        await send_email(email, subject, html_content)
        logger.info(f"Weeding analysis email sent to {email}")
    except Exception as e:  # noqa: BLE001  # email dispatch boundary - log not raise
        logger.warning(f"Failed to send weeding analysis email: {e}")
