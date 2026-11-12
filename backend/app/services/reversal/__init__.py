# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reversal Strategy Package

Provides domain-specific reversal strategies extracted from the unified
reversal service. Each strategy handles a specific domain of reversal
operations (audit, circulation, fine, patron, enhanced).

All public types, constants, and strategy classes are exported from this
package for convenient imports.
"""

from .base import (
    ReversalResult,
    CanRevertResult,
    ReversalType,
    # Time window constants
    UNDO_CHECKOUT_WINDOW_MINUTES,
    UNDO_HOLD_WINDOW_MINUTES,
    UNDO_RENEWAL_WINDOW_DAYS,
    UNDO_FINE_PAYMENT_WINDOW_DAYS,
    # Audit reversal constants
    NON_REVERSIBLE_ACTIONS,
    REVERSIBLE_ACTIONS,
    ACTION_TO_REVERT_ACTION,
    # Shared helpers
    get_user,
    get_audit_log,
)

from .audit_strategy import AuditReversalStrategy
from .circulation_strategy import CirculationReversalStrategy
from .enhanced_strategy import EnhancedReversalStrategy
from .fine_strategy import FineReversalStrategy
from .patron_strategy import PatronRecoveryStrategy

__all__ = [
    # Data classes
    "ReversalResult",
    "CanRevertResult",
    "ReversalType",
    # Strategy classes
    "AuditReversalStrategy",
    "CirculationReversalStrategy",
    "EnhancedReversalStrategy",
    "FineReversalStrategy",
    "PatronRecoveryStrategy",
    # Time window constants
    "UNDO_CHECKOUT_WINDOW_MINUTES",
    "UNDO_HOLD_WINDOW_MINUTES",
    "UNDO_RENEWAL_WINDOW_DAYS",
    "UNDO_FINE_PAYMENT_WINDOW_DAYS",
    # Audit reversal constants
    "NON_REVERSIBLE_ACTIONS",
    "REVERSIBLE_ACTIONS",
    "ACTION_TO_REVERT_ACTION",
    # Shared helpers
    "get_user",
    "get_audit_log",
]
