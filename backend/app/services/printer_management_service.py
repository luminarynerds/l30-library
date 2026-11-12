# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.print import (
    Printer, PrinterStatus, PrinterAlert, PrintReleaseStation,
    PrintJob, PrintJobStatus
)
from ..models.user import User


class PrinterManagementService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_printer(
        self,
        name: str,
        printer_type: str,
        location: str,
        device_id: Optional[str] = None,
        model: Optional[str] = None,
        cups_printer_name: Optional[str] = None,
        ipp_endpoint: Optional[str] = None,
        ip_address: Optional[str] = None,
        supports_color: bool = True,
        supports_double_sided: bool = True,
        notes: Optional[str] = None,
    ) -> Printer:

        printer = Printer(
            name=name,
            printer_type=printer_type,
            location=location,
            device_id=device_id,
            model=model,
            cups_printer_name=cups_printer_name,
            ipp_endpoint=ipp_endpoint,
            ip_address=ip_address,
            supports_color=supports_color,
            supports_double_sided=supports_double_sided,
            notes=notes,
            status=PrinterStatus.online,
        )

        self.db.add(printer)
        await self.db.commit()

        return printer

    async def get_printer(self, printer_id: int) -> Optional[Printer]:
        result = await self.db.execute(select(Printer).filter(Printer.id == printer_id))
        return result.scalar_one_or_none()

    async def get_all_printers(self, only_enabled: bool = True) -> List[Printer]:
        query = select(Printer)

        if only_enabled:
            query = query.filter(Printer.is_enabled == True)

        query = query.order_by(Printer.location)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_printers_by_location(self, location: str) -> List[Printer]:
        safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        result = await self.db.execute(
            select(Printer).filter(
                and_(
                    Printer.location.ilike(f"%{safe_location}%"),
                    Printer.is_enabled == True
                )
            ).order_by(Printer.name)
        )
        return result.scalars().all()

    async def update_printer_status(
        self,
        printer_id: int,
        status: PrinterStatus,
    ) -> Printer:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")

        printer.status = status
        printer.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        return printer

    async def update_supply_levels(
        self,
        printer_id: int,
        black_toner_level: Optional[float] = None,
        color_toner_level: Optional[float] = None,
        paper_level: Optional[float] = None,
    ) -> Printer:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")


        if black_toner_level is not None:
            printer.black_toner_level = black_toner_level
        if color_toner_level is not None:
            printer.color_toner_level = color_toner_level
        if paper_level is not None:
            printer.paper_level = paper_level

        # Check for alerts
        await self._check_and_create_alerts(printer_id, printer)

        printer.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return printer

    async def disable_printer(self, printer_id: int) -> Printer:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")

        printer.is_enabled = False
        printer.status = PrinterStatus.disabled

        await self.db.commit()
        return printer

    async def enable_printer(self, printer_id: int) -> Printer:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")

        printer.is_enabled = True
        printer.status = PrinterStatus.online

        await self.db.commit()
        return printer

    # ========================================================================
    # Release Stations
    # ========================================================================

    async def register_release_station(
        self,
        name: str,
        location: str,
        card_reader_type: str,
        has_display: bool = True,
        has_touchscreen: bool = False,
        has_cash_payment: bool = False,
        has_card_payment: bool = False,
        use_pin_code: bool = True,
        notes: Optional[str] = None,
    ) -> PrintReleaseStation:

        station = PrintReleaseStation(
            name=name,
            location=location,
            card_reader_type=card_reader_type,
            has_display=has_display,
            has_touchscreen=has_touchscreen,
            has_cash_payment=has_cash_payment,
            has_card_payment=has_card_payment,
            use_pin_code=use_pin_code,
            notes=notes,
        )

        self.db.add(station)
        await self.db.commit()

        return station

    async def get_release_station(self, station_id: int) -> Optional[PrintReleaseStation]:
        result = await self.db.execute(
            select(PrintReleaseStation).filter(PrintReleaseStation.id == station_id)
        )
        return result.scalar_one_or_none()

    async def get_all_release_stations(self) -> List[PrintReleaseStation]:
        result = await self.db.execute(
            select(PrintReleaseStation)
            .filter(PrintReleaseStation.is_active == True)
            .order_by(PrintReleaseStation.location)
        )
        return result.scalars().all()

    async def heartbeat_release_station(self, station_id: int) -> PrintReleaseStation:
        station = await self.get_release_station(station_id)
        if not station:
            raise ValueError(f"Release station {station_id} not found")

        station.last_heartbeat = datetime.now(timezone.utc)
        station.is_online = True

        await self.db.commit()
        return station

    # ========================================================================
    # Alerts
    # ========================================================================

    async def create_alert(
        self,
        printer_id: int,
        alert_type: str,
        severity: str,
        message: str,
    ) -> PrinterAlert:

        # Check if unresolved alert already exists
        result = await self.db.execute(
            select(PrinterAlert).filter(
                and_(
                    PrinterAlert.printer_id == printer_id,
                    PrinterAlert.alert_type == alert_type,
                    PrinterAlert.resolved == False
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing  # Return existing alert

        alert = PrinterAlert(
            printer_id=printer_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
        )

        self.db.add(alert)

        # Update printer alert flags
        printer = await self.get_printer(printer_id)
        if printer:
            if alert_type == "low_toner":
                printer.has_low_toner_alert = True
            elif alert_type == "low_paper":
                printer.has_low_paper_alert = True

            printer.last_alert_sent_at = datetime.now(timezone.utc)

        await self.db.commit()
        return alert

    async def get_unresolved_alerts(self, printer_id: Optional[int] = None) -> List[PrinterAlert]:
        query = select(PrinterAlert).filter(PrinterAlert.resolved == False)

        if printer_id:
            query = query.filter(PrinterAlert.printer_id == printer_id)

        query = query.order_by(PrinterAlert.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def resolve_alert(
        self,
        alert_id: int,
        resolved_by_id: Optional[int] = None,
    ) -> PrinterAlert:

        result = await self.db.execute(
            select(PrinterAlert).filter(PrinterAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by_id = resolved_by_id

        # Clear printer flags if all alerts resolved
        printer = await self.get_printer(alert.printer_id)
        if printer:
            # Check if there are any other unresolved alerts of this type
            result = await self.db.execute(
                select(PrinterAlert).filter(
                    and_(
                        PrinterAlert.printer_id == alert.printer_id,
                        PrinterAlert.alert_type == alert.alert_type,
                        PrinterAlert.resolved == False
                    )
                )
            )
            remaining = result.scalar_one_or_none()

            if not remaining:
                if alert.alert_type == "low_toner":
                    printer.has_low_toner_alert = False
                elif alert.alert_type == "low_paper":
                    printer.has_low_paper_alert = False

        await self.db.commit()
        return alert

    async def get_alerts_for_staff(self) -> List[dict]:
        alerts = await self.get_unresolved_alerts()

        formatted_alerts = []
        for alert in alerts:
            printer = await self.get_printer(alert.printer_id)
            formatted_alerts.append({
                "id": alert.id,
                "printer_id": alert.printer_id,
                "printer_name": printer.name if printer else "Unknown",
                "printer_location": printer.location if printer else "Unknown",
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            })

        return formatted_alerts

    # ========================================================================
    # Maintenance
    # ========================================================================

    async def schedule_maintenance(
        self,
        printer_id: int,
        next_due_date: datetime,
    ) -> Printer:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")

        printer.next_maintenance_due = next_due_date
        await self.db.commit()

        return printer

    async def record_maintenance(
        self,
        printer_id: int,
        next_due_days: int = 90,
    ) -> Printer:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")

        printer.last_maintenance_date = datetime.now(timezone.utc)
        printer.next_maintenance_due = datetime.now(timezone.utc) + timedelta(days=next_due_days)

        await self.db.commit()
        return printer

    async def get_maintenance_due_printers(self) -> List[Printer]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Printer).filter(
                and_(
                    Printer.next_maintenance_due <= now,
                    Printer.is_enabled == True
                )
            )
        )
        return result.scalars().all()

    # ========================================================================
    # Private Helpers
    # ========================================================================

    async def _check_and_create_alerts(
        self,
        printer_id: int,
        printer: Printer,
    ) -> None:

        if printer.black_toner_level is not None:
            if printer.black_toner_level <= printer.low_toner_threshold:
                await self.create_alert(
                    printer_id=printer_id,
                    alert_type="low_toner",
                    severity="warning",
                    message=f"Black toner level at {printer.black_toner_level}% (threshold: {printer.low_toner_threshold}%)",
                )

        if printer.color_toner_level is not None:
            if printer.color_toner_level <= printer.low_toner_threshold:
                await self.create_alert(
                    printer_id=printer_id,
                    alert_type="low_color_toner",
                    severity="warning",
                    message=f"Color toner level at {printer.color_toner_level}% (threshold: {printer.low_toner_threshold}%)",
                )

        if printer.paper_level is not None:
            if printer.paper_level <= printer.low_paper_threshold:
                await self.create_alert(
                    printer_id=printer_id,
                    alert_type="low_paper",
                    severity="warning",
                    message=f"Paper level at {printer.paper_level}% (threshold: {printer.low_paper_threshold}%)",
                )

    async def get_printer_statistics(self, printer_id: int) -> dict:
        printer = await self.get_printer(printer_id)
        if not printer:
            raise ValueError(f"Printer {printer_id} not found")

        # Get jobs from last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        result = await self.db.execute(
            select(func.count(), func.sum(PrintJob.pages)).filter(
                and_(
                    PrintJob.printer_id == printer_id,
                    PrintJob.submitted_at >= thirty_days_ago,
                    PrintJob.status.in_([PrintJobStatus.completed, PrintJobStatus.released])
                )
            )
        )
        count, pages = result.first()

        return {
            "printer_id": printer_id,
            "printer_name": printer.name,
            "total_jobs_all_time": printer.total_jobs,
            "total_pages_all_time": printer.total_pages_printed,
            "total_revenue": float(printer.total_revenue),
            "jobs_last_30_days": count or 0,
            "pages_last_30_days": pages or 0,
            "average_pages_per_job": (pages / count) if count and pages else 0,
        }
