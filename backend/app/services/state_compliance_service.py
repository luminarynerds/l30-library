# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.state_compliance import (
    ComplianceDashboardConfig,
    ConfidentialityStrength,
    DEFAULT_STATE_CONFIGS,
    DEFAULT_WCAG_21_AA_CRITERIA,
    LocalComplianceConfig,
    RegulationAlert,
    RegulationChangeStatus,
    RegulationMonitor,
    RegulationMonitoringSource,
    StateComplianceConfig,
    StateConfidentialityException,
    StateReportTemplate,
    VPATConformanceLevel,
    VPATCriterion,
    VPATReport,
)

logger = get_logger(__name__)


class StateComplianceService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config_cache: dict[str, StateComplianceConfig] = {}
        self._config_cache_max_entries = 100

    # =========================================================================
    # Configuration Management
    # =========================================================================

    async def get_state_config(self, state_code: str) -> Optional[StateComplianceConfig]:
        state_code = state_code.upper()

        # Check cache
        if state_code in self._config_cache:
            return self._config_cache[state_code]

        result = await self.db.execute(
            select(StateComplianceConfig).where(
                and_(
                    StateComplianceConfig.state_code == state_code,
                    StateComplianceConfig.is_active == True,
                )
            )
        )
        config = result.scalar_one_or_none()

        if config:
            self._config_cache[state_code] = config
            if len(self._config_cache) > self._config_cache_max_entries:
                oldest_key = next(iter(self._config_cache))
                del self._config_cache[oldest_key]

        return config

    async def get_all_state_configs(self) -> list[StateComplianceConfig]:
        result = await self.db.execute(
            select(StateComplianceConfig)
            .where(StateComplianceConfig.is_active == True)
            .order_by(StateComplianceConfig.state_name)
        )
        return list(result.scalars().all())

    async def initialize_default_configs(self) -> int:
        created = 0

        for config_data in DEFAULT_STATE_CONFIGS:
            # Check if already exists
            existing = await self.get_state_config(config_data["state_code"])
            if existing:
                continue

            config = StateComplianceConfig(**config_data)
            self.db.add(config)
            created += 1

        if created > 0:
            await self.db.commit()
            logger.info(f"Initialized {created} default state compliance configurations")

        return created

    # =========================================================================
    # Patron Confidentiality
    # =========================================================================

    async def validate_disclosure_request(
        self,
        state_code: str,
        request_type: str,
        record_type: str = "circulation",
        has_court_order: bool = False,
        has_subpoena: bool = False,
        has_warrant: bool = False,
        is_grand_jury: bool = False,
    ) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        if not config:
            # Default to strictest interpretation if no config
            return {
                "valid": False,
                "reason": f"No compliance configuration for state {state_code}",
                "requires_court_order": True,
                "patron_notification_required": True,
                "patron_notification_allowed": True,
            }

        # Check if record type is protected
        record_protected = True
        if record_type == "circulation" and not config.circulation_records_protected:
            record_protected = False
        elif record_type == "registration" and not config.registration_records_protected:
            record_protected = False
        elif record_type == "internet" and not config.internet_usage_protected:
            record_protected = False
        elif record_type == "programs" and not config.program_attendance_protected:
            record_protected = False

        if not record_protected:
            return {
                "valid": True,
                "reason": f"{record_type} records are not protected under {config.confidentiality_statute}",
                "record_protected": False,
                "patron_notification_required": False,
                "patron_notification_allowed": True,
            }

        # Check legal process requirements
        valid = False
        reason = ""

        if config.requires_court_order:
            if has_court_order or has_warrant:
                valid = True
                reason = "Court order or warrant provided"
            elif config.grand_jury_subpoena_required and is_grand_jury and has_subpoena:
                valid = True
                reason = "Grand jury subpoena provided"
            else:
                reason = f"Court order required under {config.confidentiality_statute}"
        elif config.subpoena_sufficient:
            if has_subpoena or has_court_order or has_warrant:
                valid = True
                reason = "Valid legal process provided"
            else:
                reason = "Valid subpoena, court order, or warrant required"
        else:
            # Most permissive - still need some legal process
            if has_subpoena or has_court_order or has_warrant:
                valid = True
                reason = "Legal process provided"
            else:
                reason = "Some form of legal process required"

        # Check for exceptions
        exceptions = await self._get_applicable_exceptions(state_code, record_type)

        return {
            "valid": valid,
            "reason": reason,
            "state_code": state_code,
            "confidentiality_statute": config.confidentiality_statute,
            "confidentiality_strength": str(config.confidentiality_strength),
            "record_protected": True,
            "requires_court_order": config.requires_court_order,
            "subpoena_sufficient": config.subpoena_sufficient,
            "grand_jury_subpoena_required": config.grand_jury_subpoena_required,
            "patron_notification_required": config.patron_notification_required,
            "patron_notification_allowed": config.patron_notification_allowed,
            "notification_delay_days": config.notification_delay_days,
            "applicable_exceptions": exceptions,
        }

    async def _get_applicable_exceptions(
        self, state_code: str, record_type: str
    ) -> list[dict]:
        result = await self.db.execute(
            select(StateConfidentialityException).where(
                and_(
                    StateConfidentialityException.state_code == state_code,
                    StateConfidentialityException.is_active == True,
                    (
                        StateConfidentialityException.applies_to_record_type.is_(None)
                        | (StateConfidentialityException.applies_to_record_type == record_type)
                    ),
                )
            )
        )
        exceptions = result.scalars().all()

        return [
            {
                "name": e.exception_name,
                "description": e.exception_description,
                "agency_type": e.applies_to_agency_type,
                "requires_emergency": e.requires_emergency,
                "requires_minor_involved": e.requires_minor_involved,
                "statute_reference": e.statute_reference,
            }
            for e in exceptions
        ]

    async def get_patron_notification_requirements(
        self, state_code: str
    ) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        if not config:
            return {
                "notification_required": True,
                "notification_allowed": True,
                "delay_days": 0,
            }

        return {
            "notification_required": config.patron_notification_required,
            "notification_allowed": config.patron_notification_allowed,
            "delay_days": config.notification_delay_days,
            "state_code": state_code,
            "confidentiality_strength": str(config.confidentiality_strength),
        }

    # =========================================================================
    # Data Retention
    # =========================================================================

    async def get_retention_periods(self, state_code: str) -> dict[str, int]:
        # System defaults
        defaults = {
            "checkout_record_retention_years": 7,
            "financial_record_retention_years": 7,
            "patron_data_retention_after_closure_days": 30,
            "system_log_retention_days": 365,
        }

        config = await self.get_state_config(state_code)

        if config:
            if config.checkout_record_retention_years is not None:
                defaults["checkout_record_retention_years"] = config.checkout_record_retention_years
            if config.financial_record_retention_years is not None:
                defaults["financial_record_retention_years"] = config.financial_record_retention_years
            if config.patron_data_retention_after_closure_days is not None:
                defaults["patron_data_retention_after_closure_days"] = config.patron_data_retention_after_closure_days
            if config.system_log_retention_days is not None:
                defaults["system_log_retention_days"] = config.system_log_retention_days

            # Ensure minimum financial retention
            defaults["financial_record_retention_years"] = max(
                defaults["financial_record_retention_years"],
                config.minimum_financial_retention_years
            )

        return defaults

    async def get_record_deletion_date(
        self,
        state_code: str,
        record_type: str,
        record_created_at: datetime,
    ) -> datetime:
        periods = await self.get_retention_periods(state_code)

        if record_type == "checkout":
            years = periods["checkout_record_retention_years"]
        elif record_type == "financial":
            years = periods["financial_record_retention_years"]
        elif record_type == "patron":
            days = periods["patron_data_retention_after_closure_days"]
            return record_created_at + timedelta(days=days)
        elif record_type == "log":
            days = periods["system_log_retention_days"]
            return record_created_at + timedelta(days=days)
        else:
            years = 7  # Default fallback

        return record_created_at.replace(year=record_created_at.year + years)

    # =========================================================================
    # Law Enforcement Response
    # =========================================================================

    async def get_le_response_requirements(self, state_code: str) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        if not config:
            return {
                "response_deadline_days": 30,
                "extension_allowed": True,
                "extension_max_days": 30,
                "legal_review_required": True,
                "director_approval_required": True,
                "scope_narrowing_required": True,
                "response_template": None,
            }

        return {
            "response_deadline_days": config.le_response_deadline_days,
            "extension_allowed": config.le_extension_allowed,
            "extension_max_days": config.le_extension_max_days,
            "legal_review_required": config.le_legal_review_required,
            "director_approval_required": config.le_director_approval_required,
            "scope_narrowing_required": config.le_scope_narrowing_required,
            "response_template": config.le_response_template_name,
            "state_code": state_code,
            "confidentiality_statute": config.confidentiality_statute,
        }

    async def calculate_le_response_deadline(
        self,
        state_code: str,
        received_date: datetime,
        extension_requested: bool = False,
    ) -> datetime:
        config = await self.get_state_config(state_code)

        base_days = config.le_response_deadline_days if config else 30
        extension_days = 0

        if extension_requested and config and config.le_extension_allowed:
            extension_days = config.le_extension_max_days or 30

        return received_date + timedelta(days=base_days + extension_days)

    # =========================================================================
    # State Library Reporting
    # =========================================================================

    async def get_reporting_requirements(self, state_code: str) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        if not config:
            return {
                "state_library_name": None,
                "state_library_id": None,
                "annual_report_due": None,
                "required_statistics": [],
                "report_template": None,
            }

        # Calculate next due date
        due_date = None
        if config.annual_report_due_month and config.annual_report_due_day:
            today = date.today()
            due_date = date(today.year, config.annual_report_due_month, config.annual_report_due_day)
            if due_date < today:
                due_date = due_date.replace(year=today.year + 1)

        return {
            "state_library_name": config.state_library_name,
            "state_library_id": config.state_library_id,
            "annual_report_due": due_date.isoformat() if due_date else None,
            "required_statistics": config.required_statistics or [],
            "report_template": config.state_report_template,
            "state_code": state_code,
        }

    async def get_report_template(self, template_name: str) -> Optional[StateReportTemplate]:
        result = await self.db.execute(
            select(StateReportTemplate).where(
                and_(
                    StateReportTemplate.template_name == template_name,
                    StateReportTemplate.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_upcoming_report_deadlines(self, days_ahead: int = 90) -> list[dict]:
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)

        configs = await self.get_all_state_configs()
        deadlines = []

        for config in configs:
            if config.annual_report_due_month and config.annual_report_due_day:
                due_date = date(today.year, config.annual_report_due_month, config.annual_report_due_day)
                if due_date < today:
                    due_date = due_date.replace(year=today.year + 1)

                if due_date <= cutoff:
                    deadlines.append({
                        "state_code": config.state_code,
                        "state_name": config.state_name,
                        "state_library_name": config.state_library_name,
                        "due_date": due_date.isoformat(),
                        "days_until_due": (due_date - today).days,
                        "report_template": config.state_report_template,
                    })

        # Sort by due date
        deadlines.sort(key=lambda x: x["due_date"])
        return deadlines

    # =========================================================================
    # ID Verification
    # =========================================================================

    async def get_id_verification_requirements(self, state_code: str) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        if not config:
            return {
                "require_photo_id_adult": False,
                "require_photo_id_minor": False,
                "require_residency_proof": True,
                "accepted_id_types": ["drivers_license", "state_id", "passport"],
                "residency_proof_types": ["utility_bill", "lease", "bank_statement"],
                "adult_age_threshold": 18,
                "teen_age_threshold": 13,
                "default_card_validity_years": 3,
            }

        return {
            "require_photo_id_adult": config.require_photo_id_for_adult_registration,
            "require_photo_id_minor": config.require_photo_id_for_minor_registration,
            "require_residency_proof": config.require_residency_proof,
            "accepted_id_types": config.accepted_id_types or ["drivers_license", "state_id", "passport"],
            "residency_proof_types": config.residency_proof_types or ["utility_bill", "lease", "bank_statement"],
            "adult_age_threshold": config.adult_age_threshold,
            "teen_age_threshold": config.teen_age_threshold,
            "default_card_validity_years": config.default_card_validity_years,
            "state_code": state_code,
        }

    async def validate_registration_documents(
        self,
        state_code: str,
        age: int,
        has_photo_id: bool = False,
        photo_id_type: Optional[str] = None,
        has_residency_proof: bool = False,
        residency_proof_type: Optional[str] = None,
    ) -> dict[str, Any]:
        requirements = await self.get_id_verification_requirements(state_code)
        missing = []
        valid = True

        # Determine if adult or minor
        is_adult = age >= requirements["adult_age_threshold"]

        # Check photo ID requirement
        if is_adult and requirements["require_photo_id_adult"]:
            if not has_photo_id:
                missing.append("Photo ID required for adult registration")
                valid = False
            elif photo_id_type and photo_id_type not in requirements["accepted_id_types"]:
                missing.append(f"Photo ID type '{photo_id_type}' not accepted. Accepted types: {requirements['accepted_id_types']}")
                valid = False

        if not is_adult and requirements["require_photo_id_minor"]:
            if not has_photo_id:
                missing.append("Photo ID required for minor registration")
                valid = False

        # Check residency proof
        if requirements["require_residency_proof"]:
            if not has_residency_proof:
                missing.append("Proof of residency required")
                valid = False
            elif residency_proof_type and residency_proof_type not in requirements["residency_proof_types"]:
                missing.append(f"Residency proof type '{residency_proof_type}' not accepted. Accepted types: {requirements['residency_proof_types']}")
                valid = False

        return {
            "valid": valid,
            "missing_requirements": missing,
            "is_adult": is_adult,
            "state_code": state_code,
            "card_validity_years": requirements["default_card_validity_years"],
        }

    # =========================================================================
    # Accessibility
    # =========================================================================

    async def get_accessibility_requirements(self, state_code: str) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        result = {
            "federal_requirements": "ADA, Section 508, WCAG 2.1 AA",
            "state_statute": None,
            "notes": None,
            "state_code": state_code,
        }

        if config:
            result["state_statute"] = config.additional_accessibility_statute
            result["notes"] = config.accessibility_notes

        return result

    # =========================================================================
    # Compliance Summary
    # =========================================================================

    async def get_full_compliance_summary(self, state_code: str) -> dict[str, Any]:
        config = await self.get_state_config(state_code)

        if not config:
            return {
                "state_code": state_code,
                "configured": False,
                "message": f"No compliance configuration found for state {state_code}. Using system defaults.",
            }

        return {
            "state_code": state_code,
            "state_name": config.state_name,
            "configured": True,
            "last_reviewed": config.last_reviewed_at.isoformat() if config.last_reviewed_at else None,
            "confidentiality": {
                "statute": config.confidentiality_statute,
                "strength": str(config.confidentiality_strength),
                "requires_court_order": config.requires_court_order,
                "patron_notification_required": config.patron_notification_required,
            },
            "retention": await self.get_retention_periods(state_code),
            "law_enforcement": await self.get_le_response_requirements(state_code),
            "reporting": await self.get_reporting_requirements(state_code),
            "id_verification": await self.get_id_verification_requirements(state_code),
            "accessibility": await self.get_accessibility_requirements(state_code),
        }

    # =========================================================================
    # Local (County/Municipal) Compliance
    # =========================================================================

    async def get_local_config(
        self, state_code: str, jurisdiction_name: str
    ) -> Optional[LocalComplianceConfig]:
        result = await self.db.execute(
            select(LocalComplianceConfig).where(
                and_(
                    LocalComplianceConfig.state_code == state_code.upper(),
                    LocalComplianceConfig.jurisdiction_name == jurisdiction_name,
                    LocalComplianceConfig.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_local_configs_for_state(
        self, state_code: str
    ) -> list[LocalComplianceConfig]:
        result = await self.db.execute(
            select(LocalComplianceConfig)
            .where(
                and_(
                    LocalComplianceConfig.state_code == state_code.upper(),
                    LocalComplianceConfig.is_active == True,
                )
            )
            .order_by(LocalComplianceConfig.jurisdiction_name)
        )
        return list(result.scalars().all())

    async def create_local_config(
        self,
        state_code: str,
        jurisdiction_type: str,
        jurisdiction_name: str,
        **kwargs,
    ) -> LocalComplianceConfig:
        config = LocalComplianceConfig(
            state_code=state_code.upper(),
            jurisdiction_type=jurisdiction_type,
            jurisdiction_name=jurisdiction_name,
            **kwargs,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_effective_compliance(
        self, state_code: str, jurisdiction_name: Optional[str] = None
    ) -> dict[str, Any]:
        await self.get_state_config(state_code)
        local_config = None

        if jurisdiction_name:
            local_config = await self.get_local_config(state_code, jurisdiction_name)

        # Start with state-level requirements
        effective = await self.get_full_compliance_summary(state_code)

        # Apply local overrides if they exist and are stricter
        if local_config:
            effective["local_jurisdiction"] = {
                "name": local_config.jurisdiction_name,
                "type": local_config.jurisdiction_type,
            }

            # Privacy - use stricter
            if local_config.privacy_stricter_than_state:
                effective["local_privacy_ordinance"] = local_config.local_privacy_ordinance

            # Retention - use shorter (stricter)
            if local_config.local_retention_override:
                if local_config.checkout_record_retention_years:
                    current = effective.get("retention", {}).get("checkout_record_retention_years", 7)
                    effective["retention"]["checkout_record_retention_years"] = min(
                        current, local_config.checkout_record_retention_years
                    )
                if local_config.financial_record_retention_years:
                    current = effective.get("retention", {}).get("financial_record_retention_years", 7)
                    effective["retention"]["financial_record_retention_years"] = min(
                        current, local_config.financial_record_retention_years
                    )

            # Local ID requirements
            if local_config.require_local_residency:
                effective["local_residency_required"] = True
                effective["local_residency_proof_types"] = local_config.local_residency_proof_types

            # Sanctuary city policies affect LE handling
            if local_config.sanctuary_city_policies:
                effective["sanctuary_city"] = True
                effective["le_notes"] = "Sanctuary city policies may limit cooperation with certain federal requests"

            # Local accessibility
            if local_config.local_accessibility_ordinance:
                effective["local_accessibility"] = {
                    "ordinance": local_config.local_accessibility_ordinance,
                    "contact_email": local_config.accessibility_contact_email,
                    "contact_phone": local_config.accessibility_contact_phone,
                }

            # Local reporting
            if local_config.local_reports_required:
                effective["local_reports"] = {
                    "types": local_config.local_report_types,
                    "due_dates": local_config.local_report_due_dates,
                }

        return effective

    # =========================================================================
    # Regulation Monitoring
    # =========================================================================

    async def create_regulation_monitor(
        self,
        regulation_name: str,
        jurisdiction_type: str,
        source: RegulationMonitoringSource,
        **kwargs,
    ) -> RegulationMonitor:
        monitor = RegulationMonitor(
            regulation_name=regulation_name,
            jurisdiction_type=jurisdiction_type,
            source=source,
            **kwargs,
        )
        self.db.add(monitor)
        await self.db.commit()
        await self.db.refresh(monitor)
        return monitor

    async def get_active_regulations(
        self,
        jurisdiction_type: Optional[str] = None,
        jurisdiction_code: Optional[str] = None,
        status: Optional[RegulationChangeStatus] = None,
    ) -> list[RegulationMonitor]:
        conditions = [RegulationMonitor.is_active == True]

        if jurisdiction_type:
            conditions.append(RegulationMonitor.jurisdiction_type == jurisdiction_type)
        if jurisdiction_code:
            conditions.append(RegulationMonitor.jurisdiction_code == jurisdiction_code.upper())
        if status:
            conditions.append(RegulationMonitor.status == status)

        result = await self.db.execute(
            select(RegulationMonitor)
            .where(and_(*conditions))
            .order_by(RegulationMonitor.effective_date.desc().nullsfirst())
        )
        return list(result.scalars().all())

    async def get_regulations_requiring_action(self) -> list[RegulationMonitor]:
        result = await self.db.execute(
            select(RegulationMonitor).where(
                and_(
                    RegulationMonitor.is_active == True,
                    RegulationMonitor.requires_action == True,
                    RegulationMonitor.reviewed == False,
                )
            ).order_by(RegulationMonitor.action_deadline.asc().nullslast())
        )
        return list(result.scalars().all())

    async def create_regulation_alert(
        self,
        regulation_monitor_id: int,
        alert_type: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
    ) -> RegulationAlert:
        alert = RegulationAlert(
            regulation_monitor_id=regulation_monitor_id,
            alert_type=alert_type,
            title=title,
            description=description,
            priority=priority,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def get_unresolved_alerts(
        self, priority: Optional[str] = None, assigned_to_id: Optional[int] = None
    ) -> list[RegulationAlert]:
        conditions = [RegulationAlert.is_resolved == False]

        if priority:
            conditions.append(RegulationAlert.priority == priority)
        if assigned_to_id:
            conditions.append(RegulationAlert.assigned_to_id == assigned_to_id)

        result = await self.db.execute(
            select(RegulationAlert)
            .where(and_(*conditions))
            .order_by(
                # Order by priority (critical first) then by creation date
                RegulationAlert.id.desc()
            )
        )
        return list(result.scalars().all())

    async def resolve_alert(
        self,
        alert_id: int,
        resolved_by_id: int,
        resolution_notes: Optional[str] = None,
    ) -> RegulationAlert:
        result = await self.db.execute(
            select(RegulationAlert).where(RegulationAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.is_resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by_id = resolved_by_id
        alert.resolution_notes = resolution_notes

        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def check_regulation_deadlines(self, days_ahead: int = 30) -> list[dict]:
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)

        result = await self.db.execute(
            select(RegulationMonitor).where(
                and_(
                    RegulationMonitor.is_active == True,
                    RegulationMonitor.requires_action == True,
                    RegulationMonitor.action_deadline != None,
                    RegulationMonitor.action_deadline <= cutoff,
                )
            ).order_by(RegulationMonitor.action_deadline.asc())
        )
        regulations = result.scalars().all()

        deadlines = []
        for reg in regulations:
            days_until = (reg.action_deadline - today).days
            deadlines.append({
                "id": reg.id,
                "regulation_name": reg.regulation_name,
                "regulation_number": reg.regulation_number,
                "jurisdiction_type": reg.jurisdiction_type,
                "jurisdiction_code": reg.jurisdiction_code,
                "action_deadline": reg.action_deadline.isoformat(),
                "days_until_deadline": days_until,
                "action_notes": reg.action_notes,
                "priority": reg.priority,
                "is_overdue": days_until < 0,
            })

        return deadlines

    # =========================================================================
    # Compliance Dashboard
    # =========================================================================

    async def get_dashboard_config(self, user_id: int) -> Optional[ComplianceDashboardConfig]:
        result = await self.db.execute(
            select(ComplianceDashboardConfig).where(
                ComplianceDashboardConfig.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update_dashboard_config(
        self, user_id: int, **kwargs
    ) -> ComplianceDashboardConfig:
        config = await self.get_dashboard_config(user_id)

        if config:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        else:
            # Set defaults if not provided
            if "enabled_widgets" not in kwargs:
                kwargs["enabled_widgets"] = [
                    "upcoming_deadlines",
                    "regulation_alerts",
                    "compliance_score",
                    "le_requests_pending",
                ]
            config = ComplianceDashboardConfig(user_id=user_id, **kwargs)
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_compliance_dashboard_data(
        self,
        user_id: int,
        state_code: Optional[str] = None,
    ) -> dict[str, Any]:
        config = await self.get_dashboard_config(user_id)
        enabled_widgets = config.enabled_widgets if config else [
            "upcoming_deadlines",
            "regulation_alerts",
            "compliance_score",
        ]
        date_range = config.default_date_range_days if config else 90

        dashboard_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "widgets": {},
        }

        # Upcoming Deadlines widget
        if "upcoming_deadlines" in enabled_widgets:
            dashboard_data["widgets"]["upcoming_deadlines"] = {
                "state_report_deadlines": await self.get_upcoming_report_deadlines(date_range),
                "regulation_deadlines": await self.check_regulation_deadlines(date_range),
            }

        # Regulation Alerts widget
        if "regulation_alerts" in enabled_widgets:
            alerts = await self.get_unresolved_alerts()
            dashboard_data["widgets"]["regulation_alerts"] = {
                "total_unresolved": len(alerts),
                "by_priority": {
                    "critical": len([a for a in alerts if a.priority == "critical"]),
                    "high": len([a for a in alerts if a.priority == "high"]),
                    "medium": len([a for a in alerts if a.priority == "medium"]),
                    "low": len([a for a in alerts if a.priority == "low"]),
                },
                "recent_alerts": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "priority": a.priority,
                        "alert_type": a.alert_type,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in alerts[:5]
                ],
            }

        # Compliance Score widget
        if "compliance_score" in enabled_widgets:
            dashboard_data["widgets"]["compliance_score"] = await self._calculate_compliance_score(state_code)

        # State Config Status widget
        if "state_config_status" in enabled_widgets:
            configs = await self.get_all_state_configs()
            dashboard_data["widgets"]["state_config_status"] = {
                "total_configured": len(configs),
                "states": [
                    {
                        "state_code": c.state_code,
                        "state_name": c.state_name,
                        "last_reviewed": c.last_reviewed_at.isoformat() if c.last_reviewed_at else None,
                        "needs_review": c.last_reviewed_at is None or (
                            datetime.now(timezone.utc) - c.last_reviewed_at
                        ).days > 365,
                    }
                    for c in configs
                ],
            }

        # Accessibility Status widget
        if "accessibility_status" in enabled_widgets:
            vpat = await self.get_current_vpat()
            dashboard_data["widgets"]["accessibility_status"] = {
                "has_vpat": vpat is not None,
                "vpat_version": vpat.report_version if vpat else None,
                "overall_conformance": str(vpat.overall_conformance) if vpat else None,
                "evaluation_date": vpat.evaluation_date.isoformat() if vpat else None,
                "wcag_level": vpat.wcag_level if vpat else "AA",
            }

        return dashboard_data

    async def _calculate_compliance_score(
        self, state_code: Optional[str] = None
    ) -> dict[str, Any]:
        scores = {
            "overall": 0,
            "categories": {},
        }

        total_points = 0
        earned_points = 0

        # State configurations (20 points)
        configs = await self.get_all_state_configs()
        if configs:
            earned_points += 20
        total_points += 20
        scores["categories"]["state_configs"] = {
            "score": 20 if configs else 0,
            "max": 20,
            "status": "configured" if configs else "needs_attention",
        }

        # VPAT report (20 points)
        vpat = await self.get_current_vpat()
        vpat_score = 0
        if vpat:
            if vpat.overall_conformance == VPATConformanceLevel.SUPPORTS:
                vpat_score = 20
            elif vpat.overall_conformance == VPATConformanceLevel.PARTIALLY_SUPPORTS:
                vpat_score = 15
            else:
                vpat_score = 5
        earned_points += vpat_score
        total_points += 20
        scores["categories"]["accessibility"] = {
            "score": vpat_score,
            "max": 20,
            "status": "excellent" if vpat_score >= 15 else "needs_attention" if vpat_score > 0 else "missing",
        }

        # Regulation monitoring (20 points)
        alerts = await self.get_unresolved_alerts()
        critical_alerts = len([a for a in alerts if a.priority == "critical"])
        reg_score = 20 - min(critical_alerts * 5, 20)
        earned_points += reg_score
        total_points += 20
        scores["categories"]["regulation_monitoring"] = {
            "score": reg_score,
            "max": 20,
            "status": "good" if reg_score >= 15 else "needs_attention",
            "critical_alerts": critical_alerts,
        }

        # Config review status (20 points)
        reviewed_recently = 0
        for config in configs:
            if config.last_reviewed_at and (
                datetime.now(timezone.utc) - config.last_reviewed_at
            ).days <= 365:
                reviewed_recently += 1
        review_score = int((reviewed_recently / max(len(configs), 1)) * 20)
        earned_points += review_score
        total_points += 20
        scores["categories"]["config_reviews"] = {
            "score": review_score,
            "max": 20,
            "status": "good" if review_score >= 15 else "needs_attention",
        }

        # Deadlines (20 points)
        deadlines = await self.check_regulation_deadlines(30)
        overdue = len([d for d in deadlines if d.get("is_overdue")])
        deadline_score = 20 - min(overdue * 5, 20)
        earned_points += deadline_score
        total_points += 20
        scores["categories"]["deadlines"] = {
            "score": deadline_score,
            "max": 20,
            "status": "good" if deadline_score >= 15 else "needs_attention",
            "overdue_count": overdue,
        }

        scores["overall"] = int((earned_points / total_points) * 100)
        scores["earned_points"] = earned_points
        scores["total_points"] = total_points

        return scores

    # =========================================================================
    # VPAT Generation
    # =========================================================================

    async def get_current_vpat(self) -> Optional[VPATReport]:
        result = await self.db.execute(
            select(VPATReport)
            .where(VPATReport.is_current == True)
            .order_by(VPATReport.evaluation_date.desc())
        )
        return result.scalar_one_or_none()

    async def get_vpat_by_id(self, vpat_id: int) -> Optional[VPATReport]:
        result = await self.db.execute(
            select(VPATReport).where(VPATReport.id == vpat_id)
        )
        return result.scalar_one_or_none()

    async def create_vpat_report(
        self,
        report_name: str,
        report_version: str,
        evaluation_date: date,
        created_by_id: int,
        **kwargs,
    ) -> VPATReport:
        # Mark previous VPAT as not current
        current_vpat = await self.get_current_vpat()
        if current_vpat:
            current_vpat.is_current = False

        vpat = VPATReport(
            report_name=report_name,
            report_version=report_version,
            evaluation_date=evaluation_date,
            created_by_id=created_by_id,
            is_current=True,
            **kwargs,
        )

        if current_vpat:
            vpat.superseded_by_id = None  # This is the new one
            current_vpat.superseded_by_id = None  # Will be updated after commit

        self.db.add(vpat)
        await self.db.commit()
        await self.db.refresh(vpat)

        # Update superseded reference
        if current_vpat:
            current_vpat.superseded_by_id = vpat.id
            await self.db.commit()

        return vpat

    async def add_vpat_criterion(
        self,
        vpat_report_id: int,
        standard: str,
        criterion_id: str,
        criterion_name: str,
        conformance_level: VPATConformanceLevel,
        level: Optional[str] = None,
        remarks: Optional[str] = None,
        test_results: Optional[dict] = None,
    ) -> VPATCriterion:
        criterion = VPATCriterion(
            vpat_report_id=vpat_report_id,
            standard=standard,
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            conformance_level=conformance_level,
            level=level,
            remarks=remarks,
            test_results=test_results,
        )
        self.db.add(criterion)
        await self.db.commit()
        await self.db.refresh(criterion)
        return criterion

    async def get_vpat_criteria(self, vpat_report_id: int) -> list[VPATCriterion]:
        result = await self.db.execute(
            select(VPATCriterion)
            .where(VPATCriterion.vpat_report_id == vpat_report_id)
            .order_by(VPATCriterion.criterion_id)
        )
        return list(result.scalars().all())

    async def initialize_vpat_with_default_criteria(
        self,
        vpat_report_id: int,
        default_conformance: VPATConformanceLevel = VPATConformanceLevel.NOT_EVALUATED,
    ) -> int:
        count = 0
        for criterion_data in DEFAULT_WCAG_21_AA_CRITERIA:
            await self.add_vpat_criterion(
                vpat_report_id=vpat_report_id,
                standard="WCAG",
                criterion_id=criterion_data["criterion_id"],
                criterion_name=criterion_data["criterion_name"],
                level=criterion_data["level"],
                conformance_level=default_conformance,
            )
            count += 1

        return count

    async def generate_vpat_document(self, vpat_report_id: int) -> dict[str, Any]:
        vpat = await self.get_vpat_by_id(vpat_report_id)
        if not vpat:
            raise ValueError(f"VPAT report {vpat_report_id} not found")

        criteria = await self.get_vpat_criteria(vpat_report_id)

        # Group criteria by WCAG principle
        principles = {
            "1": {"name": "Perceivable", "criteria": []},
            "2": {"name": "Operable", "criteria": []},
            "3": {"name": "Understandable", "criteria": []},
            "4": {"name": "Robust", "criteria": []},
        }

        for criterion in criteria:
            principle_num = criterion.criterion_id.split(".")[0]
            if principle_num in principles:
                principles[principle_num]["criteria"].append({
                    "id": criterion.criterion_id,
                    "name": criterion.criterion_name,
                    "level": criterion.level,
                    "conformance": str(criterion.conformance_level),
                    "remarks": criterion.remarks,
                })

        # Calculate summary statistics
        total = len(criteria)
        supports = len([c for c in criteria if c.conformance_level == VPATConformanceLevel.SUPPORTS])
        partial = len([c for c in criteria if c.conformance_level == VPATConformanceLevel.PARTIALLY_SUPPORTS])
        does_not = len([c for c in criteria if c.conformance_level == VPATConformanceLevel.DOES_NOT_SUPPORT])
        na = len([c for c in criteria if c.conformance_level == VPATConformanceLevel.NOT_APPLICABLE])
        not_eval = len([c for c in criteria if c.conformance_level == VPATConformanceLevel.NOT_EVALUATED])

        return {
            "metadata": {
                "report_name": vpat.report_name,
                "report_version": vpat.report_version,
                "vpat_version": vpat.vpat_version,
                "evaluation_date": vpat.evaluation_date.isoformat(),
                "product_name": vpat.product_name,
                "product_version": vpat.product_version,
                "product_description": vpat.product_description,
            },
            "contact": {
                "name": vpat.vendor_contact_name,
                "email": vpat.vendor_contact_email,
                "phone": vpat.vendor_contact_phone,
            },
            "evaluator": {
                "name": vpat.evaluator_name,
                "organization": vpat.evaluator_organization,
                "methods": vpat.evaluation_methods,
            },
            "standards": {
                "wcag_version": vpat.wcag_version,
                "wcag_level": vpat.wcag_level,
                "section_508": vpat.section_508_applicable,
                "en_301_549": vpat.en_301_549_applicable,
            },
            "summary": {
                "overall_conformance": str(vpat.overall_conformance),
                "total_criteria": total,
                "supports": supports,
                "partially_supports": partial,
                "does_not_support": does_not,
                "not_applicable": na,
                "not_evaluated": not_eval,
                "conformance_percentage": round((supports + partial * 0.5) / max(total - na - not_eval, 1) * 100, 1),
            },
            "principles": principles,
            "notes": vpat.general_notes,
            "legal_disclaimer": vpat.legal_disclaimer or (
                "This VPAT is provided for informational purposes only and does not "
                "constitute a warranty or guarantee of accessibility conformance. "
                "The evaluation was conducted based on the product version and date "
                "specified above. Accessibility features may vary in different "
                "environments or with subsequent product updates."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
