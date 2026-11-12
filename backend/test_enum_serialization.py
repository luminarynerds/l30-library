"""
Verify that (str, Enum) members serialise to their bare value, not
"ClassName.MEMBER".

Enum definitions are copied inline from the model files to avoid the
app/__init__ branding/settings chain. This tests the Python-level
serialisation behavior — the same behavior that the API code relies on.
"""
from enum import Enum


# ── Copied from app/models/patron_communication.py ───────────────────────────
class NoteCategory(str, Enum):
    GENERAL = "general"
    ACCOMMODATION_NEEDS = "accommodation_needs"
    INCIDENT = "incident"
    FOLLOW_UP = "follow_up"
    PATRON_PREFERENCE = "patron_preference"
    OTHER = "other"

class NotePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class MessageType(str, Enum):
    OVERDUE_NOTICE = "overdue_notice"
    HOLD_READY = "hold_ready"
    FINE_REMINDER = "fine_reminder"
    ACCOUNT_BLOCKED = "account_blocked"
    WELCOME_NEW_PATRON = "welcome_new_patron"
    CUSTOM = "custom"

class MessageChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PRINT = "print"


# ── Copied from app/models/support_ticket.py ─────────────────────────────────
class SupportTicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# ── Copied from app/models/household.py ──────────────────────────────────────
class HouseholdLinkStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


# ── Copied from app/models/cipa_compliance.py ────────────────────────────────
class BypassReason(str, Enum):
    BONA_FIDE_RESEARCH = "bona_fide_research"
    MEDICAL_INFORMATION = "medical_information"
    LEGAL_RESEARCH = "legal_research"
    EDUCATIONAL_PURPOSE = "educational_purpose"
    OTHER_LAWFUL = "other_lawful"

class BypassStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    COMPLETED = "completed"

class ComputerSessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    TIMED_OUT = "timed_out"
    TERMINATED = "terminated"


# ── Copied from app/models/fine.py ───────────────────────────────────────────
class FineStatus(str, Enum):
    unpaid = "unpaid"
    paid = "paid"
    waived = "waived"
    partial = "partial"

class FineType(str, Enum):
    overdue = "overdue"
    lost_item = "lost_item"
    damaged_item = "damaged_item"
    other = "other"


# ── Copied from app/models/makerspace.py ─────────────────────────────────────
class JobStatus(str, Enum):
    submitted = "submitted"
    pending_review = "pending_review"
    rejected = "rejected"
    approved = "approved"
    in_progress = "in_progress"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# ── Copied from app/models/lost_damaged.py ───────────────────────────────────
import enum as _enum
class DamageSeverity(str, _enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    TOTAL_LOSS = "total_loss"


# ── Tests ─────────────────────────────────────────────────────────────────────
import pytest


def test_str_leaks_classname():
    """Python 3.11+ str(StrEnum member) returns 'ClassName.MEMBER' not value."""
    bad = str(NoteCategory.ACCOMMODATION_NEEDS)
    # On Python 3.12 this gives "NoteCategory.ACCOMMODATION_NEEDS"
    assert bad != "accommodation_needs", (
        "str() returns bare value — Python semantics changed; "
        ".value fix may be unnecessary at language level."
    )


@pytest.mark.parametrize("member,expected", [
    # patron_communication (NoteCategory, NotePriority, MessageType, MessageChannel)
    (NoteCategory.ACCOMMODATION_NEEDS, "accommodation_needs"),
    (NoteCategory.GENERAL,             "general"),
    (NoteCategory.INCIDENT,            "incident"),
    (NotePriority.HIGH,                "high"),
    (NotePriority.URGENT,              "urgent"),
    (NotePriority.NORMAL,              "normal"),
    (MessageType.OVERDUE_NOTICE,       "overdue_notice"),
    (MessageType.HOLD_READY,           "hold_ready"),
    (MessageType.CUSTOM,               "custom"),
    (MessageChannel.EMAIL,             "email"),
    (MessageChannel.SMS,               "sms"),
    (MessageChannel.PRINT,             "print"),
    # support
    (SupportTicketStatus.OPEN,         "open"),
    (SupportTicketStatus.IN_PROGRESS,  "in_progress"),
    (SupportTicketStatus.RESOLVED,     "resolved"),
    # households
    (HouseholdLinkStatus.PENDING,      "pending"),
    (HouseholdLinkStatus.APPROVED,     "approved"),
    (HouseholdLinkStatus.DECLINED,     "declined"),
    # cipa
    (BypassStatus.ACTIVE,              "active"),
    (BypassStatus.REVOKED,             "revoked"),
    (BypassReason.BONA_FIDE_RESEARCH,  "bona_fide_research"),
    (BypassReason.LEGAL_RESEARCH,      "legal_research"),
    (ComputerSessionStatus.ACTIVE,     "active"),
    (ComputerSessionStatus.TIMED_OUT,  "timed_out"),
    (ComputerSessionStatus.TERMINATED, "terminated"),
    # fines / patron_profile
    (FineStatus.unpaid,                "unpaid"),
    (FineStatus.waived,                "waived"),
    (FineType.overdue,                 "overdue"),
    (FineType.lost_item,               "lost_item"),
    # makerspace
    (JobStatus.submitted,              "submitted"),
    (JobStatus.pending_review,         "pending_review"),
    # damaged_items
    (DamageSeverity.MINOR,             "minor"),
    (DamageSeverity.SEVERE,            "severe"),
    (DamageSeverity.TOTAL_LOSS,        "total_loss"),
])
def test_value_is_bare_string(member, expected):
    """.value produces the client-facing bare string; str() does not."""
    assert member.value == expected, f"{member!r}.value should be {expected!r}"
    # For members with UPPER_CASE names, str() leaks "ClassName.MEMBER"
    if member.name != member.value:
        assert str(member) != expected, (
            f"str({member!r}) returns {expected!r} — Python semantics may have changed"
        )
