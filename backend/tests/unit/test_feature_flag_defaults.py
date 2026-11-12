# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.models.organization_features import OrganizationFeatures
from app.services.organization_features_service import OrganizationFeaturesService


@pytest.mark.unit
class TestFeatureFlagDefaults:
    def test_reading_goals_model_default_is_true(self):
        col = OrganizationFeatures.__table__.c["reading_goals_enabled"]
        assert col.default.arg is True

    def test_saved_searches_model_default_is_true(self):
        col = OrganizationFeatures.__table__.c["saved_searches_enabled"]
        assert col.default.arg is True

    def test_reading_goals_service_default_is_true(self):
        instance = OrganizationFeaturesService._create_default_features_instance()
        assert instance.reading_goals_enabled is True

    def test_saved_searches_service_default_is_true(self):
        instance = OrganizationFeaturesService._create_default_features_instance()
        assert instance.saved_searches_enabled is True
