# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Mutation testing configuration for LSC.

mutmut generates small changes (mutations) to source code and checks if
the test suite catches them. Surviving mutations indicate weak tests.

Usage:
    # Run mutation testing on critical financial module
    mutmut run --paths-to-mutate=app/domain/finance/

    # Run on circulation domain
    mutmut run --paths-to-mutate=app/domain/circulation/

    # Run on specific high-risk file
    mutmut run --paths-to-mutate=app/services/fine_service.py

    # View results
    mutmut results

    # Show a specific surviving mutant
    mutmut show <mutant-id>

    # Generate HTML report
    mutmut html

Configuration below controls which files are mutated and which tests run.
"""


def pre_mutation(context):
    """
    Called before each mutation is applied.

    Skip mutations in non-critical code to focus mutation testing budget
    on the highest-risk modules.
    """
    # Skip mutations in test files, migrations, and generated code
    skip_patterns = [
        "tests/",
        "migrations/",
        "__pycache__/",
        "__init__.py",
        "seed_",
        "conftest.py",
    ]
    for pattern in skip_patterns:
        if pattern in context.filename:
            context.skip = True
            return

    # Skip mutations in low-risk utility modules
    low_risk_modules = [
        "app/api/v1/health.py",
        "app/api/v1/releases.py",
        "app/api/v1/staff_picks.py",
        "app/core/logging.py",
    ]
    if context.filename in low_risk_modules:
        context.skip = True
        return


def pre_mutation_ast(context):
    """
    Called before each AST-level mutation.

    Skip mutations that generate noise without testing value,
    such as string literal changes in log messages.
    """
    # Skip mutations of string literals in logging calls
    # These mutations (changing log messages) rarely indicate real bugs
    if context.current_source_line:
        line = context.current_source_line.strip()
        if line.startswith("logger.") or line.startswith("logging."):
            context.skip = True
            return

        # Skip mutations of docstrings
        if line.startswith('"""') or line.startswith("'''"):
            context.skip = True
            return
