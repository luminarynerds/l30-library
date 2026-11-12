# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PLS submission-grade validation rules for the annual report.

Distinct from ``AnnualReportService.validate_report`` (which checks
state-configured ``AnnualReportValidationRule`` rows). These are the fixed
internal-consistency rules an Ohio PLS submission must satisfy before it can
be certified: finance entered by the director, circulation/attendance/FTE
component sums reconcile to their totals.

``validate(report)`` is pure (no DB) and returns a list of ``ValidationError``.
The arithmetic helper ``sums_match`` is shared with the finance PATCH endpoint
so the "lines must equal the total" check lives in exactly one place.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, List, Optional

# Money/FTE comparisons use a cent of slack; integer counts compare exactly.
MONEY_TOLERANCE = Decimal("0.01")


@dataclass
class ValidationError:
    field: str
    message: str

    def to_dict(self) -> dict:
        return {"field": self.field, "message": self.message}


def _dec(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _sum_values(mapping: Optional[dict]) -> Decimal:
    if not mapping:
        return Decimal(0)
    total = Decimal(0)
    for v in mapping.values():
        d = _dec(v)
        if d is not None:
            total += d
    return total


def sums_match(total: Any, parts: Iterable[Any]) -> bool:
    """True if the parts sum to ``total`` within the money tolerance.

    Returns False if the total is missing — a present breakdown with no total
    (or vice versa) is a mismatch, not a pass.
    """
    total_dec = _dec(total)
    if total_dec is None:
        return False
    running = Decimal(0)
    for p in parts:
        d = _dec(p)
        if d is not None:
            running += d
    return abs(running - total_dec) <= MONEY_TOLERANCE


def _finance_entered(report) -> bool:
    # First-class column is the source of truth; fall back to the legacy JSONB
    # tag for reports created before finance_source existed.
    if getattr(report, "finance_source", None) == "manual":
        return True
    sources = getattr(report, "data_sources", None) or {}
    return sources.get("financial") == "manual"


def validate(report) -> List[ValidationError]:
    """Return the list of PLS consistency errors for ``report`` (empty == valid)."""
    errors: List[ValidationError] = []

    # Completeness: finance must be director-entered. De-fabbed reports leave the
    # totals at their column default of 0, so None-checking is unreliable; the
    # manual data-source tag (set by the finance PATCH) is the source of truth.
    if not _finance_entered(report):
        errors.append(
            ValidationError(
                field="financial",
                message="Finance data has not been entered by the director.",
            )
        )

    # Children's circulation cannot exceed total circulation.
    total_circ = report.total_circulation
    childrens = report.childrens_circulation
    if total_circ is not None and childrens is not None and childrens > total_circ:
        errors.append(
            ValidationError(
                field="childrens_circulation",
                message=(
                    f"Children's circulation ({childrens}) exceeds total "
                    f"circulation ({total_circ})."
                ),
            )
        )

    # Electronic + physical circulation must equal total circulation.
    elec = report.electronic_circulation
    phys = report.physical_circulation
    if total_circ is not None and elec is not None and phys is not None:
        if elec + phys != total_circ:
            errors.append(
                ValidationError(
                    field="circulation_split",
                    message=(
                        f"Electronic ({elec}) + physical ({phys}) circulation "
                        f"= {elec + phys}, does not equal total ({total_circ})."
                    ),
                )
            )

    # Program attendance by audience must sum to the total.
    attendance_total = report.total_program_attendance
    by_audience = report.program_attendance_by_audience
    if attendance_total is not None and by_audience:
        audience_sum = int(_sum_values(by_audience))
        if audience_sum != attendance_total:
            errors.append(
                ValidationError(
                    field="program_attendance_by_audience",
                    message=(
                        f"Attendance by audience sums to {audience_sum}, does not "
                        f"equal total program attendance ({attendance_total})."
                    ),
                )
            )

    # Revenue lines must reconcile to total operating revenue.
    revenue = report.revenue_by_source
    if revenue and not sums_match(report.total_operating_revenue, revenue.values()):
        errors.append(
            ValidationError(
                field="revenue_by_source",
                message=(
                    "Revenue by source does not sum to total operating revenue."
                ),
            )
        )

    # Capital revenue lines must reconcile to capital outlay (when both present).
    capital_revenue = report.capital_revenue
    capital_outlay = getattr(report, "capital_outlay", None)
    if (
        capital_revenue
        and capital_outlay is not None
        and not sums_match(capital_outlay, capital_revenue.values())
    ):
        errors.append(
            ValidationError(
                field="capital_revenue",
                message="Capital revenue does not sum to capital outlay.",
            )
        )

    # Staff FTE components must reconcile to total staff FTE.
    total_fte = _dec(report.total_staff_fte)
    components = [
        report.librarian_fte,
        report.library_technician_fte,
        report.other_staff_fte,
    ]
    if total_fte is not None and any(c is not None for c in components):
        if not sums_match(report.total_staff_fte, components):
            errors.append(
                ValidationError(
                    field="total_staff_fte",
                    message=(
                        "Librarian + technician + other FTE does not sum to total "
                        "staff FTE."
                    ),
                )
            )

    return errors
