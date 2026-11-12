# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for drift_checks.alembic_chain helper functions."""

import sys
from pathlib import Path

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from drift_checks.alembic_chain import find_heads, parse_revision_file


class TestParseRevisionFile:
    """parse_revision_file returns (revision, down_revisions) where
    down_revisions is always a List[str] -- empty for a base migration,
    possibly multi-element for a merge migration whose down_revision is a
    tuple/list of parent revisions. (Not Optional[str]/None -- that was the
    pre-merge-support contract.)"""

    def test_baseline_migration(self, tmp_path):
        f = tmp_path / "migration.py"
        f.write_text('revision: str = "abc123"\ndown_revision: Union[str, None] = None\n')
        rev, down_rev = parse_revision_file(str(f))
        assert rev == "abc123"
        assert down_rev == []

    def test_normal_migration(self, tmp_path):
        f = tmp_path / "migration.py"
        f.write_text('revision: str = "def456"\ndown_revision: str = "abc123"\n')
        rev, down_rev = parse_revision_file(str(f))
        assert rev == "def456"
        assert down_rev == ["abc123"]

    def test_union_type_annotation(self, tmp_path):
        f = tmp_path / "migration.py"
        f.write_text('revision: str = "aaa111"\ndown_revision: Union[str, None] = "bbb222"\n')
        rev, down_rev = parse_revision_file(str(f))
        assert rev == "aaa111"
        assert down_rev == ["bbb222"]

    def test_no_revision_found(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("# no revision here\n")
        rev, down_rev = parse_revision_file(str(f))
        assert rev is None
        assert down_rev == []

    def test_real_migration_format(self, tmp_path):
        """Test with format matching actual L30 migrations."""
        f = tmp_path / "migration.py"
        f.write_text(
            '"""Some migration description."""\n'
            "from typing import Sequence, Union\n"
            "from alembic import op\n"
            "import sqlalchemy as sa\n"
            "\n"
            'revision: str = "b1f8ec5dae56"\n'
            "down_revision: Union[str, None] = None\n"
            "branch_labels: Union[str, Sequence[str], None] = None\n"
            "depends_on: Union[str, Sequence[str], None] = None\n"
        )
        rev, down_rev = parse_revision_file(str(f))
        assert rev == "b1f8ec5dae56"
        assert down_rev == []

    def test_merge_migration_tuple_down_revision(self, tmp_path):
        """Merge migrations have a tuple down_revision listing every parent."""
        f = tmp_path / "migration.py"
        f.write_text(
            'revision: str = "merge123"\n'
            'down_revision: Union[str, Sequence[str], None] = ("aaa111", "bbb222")\n'
        )
        rev, down_rev = parse_revision_file(str(f))
        assert rev == "merge123"
        assert down_rev == ["aaa111", "bbb222"]


class TestFindHeads:
    """find_heads takes Dict[str, List[str]] -- each revision maps to its
    list of parent (down_revision) ids, empty list for a base migration.
    This supports merge migrations (multiple parents), which a bare
    Optional[str] value couldn't represent."""

    def test_single_chain(self):
        revisions = {
            "aaa": [],  # base
            "bbb": ["aaa"],
            "ccc": ["bbb"],  # head
        }
        heads = find_heads(revisions)
        assert heads == ["ccc"]

    def test_forked_chain(self):
        revisions = {
            "aaa": [],
            "bbb": ["aaa"],
            "ccc": ["aaa"],  # fork!
        }
        heads = find_heads(revisions)
        assert heads == ["bbb", "ccc"]

    def test_single_revision(self):
        revisions = {"aaa": []}
        heads = find_heads(revisions)
        assert heads == ["aaa"]

    def test_empty_revisions(self):
        heads = find_heads({})
        assert heads == []

    def test_longer_chain(self):
        revisions = {
            "a": [],
            "b": ["a"],
            "c": ["b"],
            "d": ["c"],
            "e": ["d"],
        }
        heads = find_heads(revisions)
        assert heads == ["e"]

    def test_two_independent_chains(self):
        revisions = {
            "a": [],
            "b": ["a"],
            "x": [],  # separate base
            "y": ["x"],
        }
        heads = find_heads(revisions)
        assert sorted(heads) == ["b", "y"]

    def test_merge_migration_not_a_fork(self):
        """A merge migration's down_revision lists BOTH parents, so neither
        parent is a head -- only the merge revision itself is."""
        revisions = {
            "aaa": [],
            "bbb": ["aaa"],
            "ccc": ["aaa"],
            "merge": ["bbb", "ccc"],  # merges both forks back together
        }
        heads = find_heads(revisions)
        assert heads == ["merge"]
