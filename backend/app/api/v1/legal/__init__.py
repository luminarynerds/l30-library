# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal resources API router package.

This module provides a modular API for legal resources including forms,
guides, clinics, courts, and other legal information resources.

Sub-routers:
- forms: Form library and downloads
- packets: Form packet management
- guides: Guide content, topics, Know Your Rights, staff guidelines, feedback
- providers: Legal service provider directory
- clinics: Clinic scheduling and registration
- courts: Court location directory
- wizard: Form finder wizard (state machine)
- glossary: Legal terminology
- calculators: Deadline calculator, fee waiver eligibility, expungement checks
- emergency: Emergency resources
- collections: Content collections
"""

# Each sub-router is registered directly in registry.py
# (app.api.v1.legal.<name>) rather than through this package's __init__ --
# no aggregate router is built here; nothing mounts a bare `legal.router`.
