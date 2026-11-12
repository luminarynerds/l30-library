# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum, StrEnum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Float,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class WeatherCondition(StrEnum):

    sunny = "sunny"
    cloudy = "cloudy"
    rainy = "rainy"
    snowy = "snowy"
    stormy = "stormy"
    hot = "hot"  # >85°F
    cold = "cold"  # <32°F
    moderate = "moderate"  # 65-80°F


class OccupancyLevel(StrEnum):

    empty = "empty"  # <10% occupancy
    low = "low"  # 10-30%
    moderate = "moderate"  # 30-70%
    high = "high"  # 70-90%
    full = "full"  # >90%


class SignageWeatherTrigger(Base):

    __tablename__ = "signage_weather_trigger"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="CASCADE"), nullable=False)

    # Weather conditions that trigger this content
    trigger_conditions = Column(String(500), nullable=False)  # Comma-separated conditions
    min_temperature = Column(Float, nullable=True)  # Celsius
    max_temperature = Column(Float, nullable=True)
    min_humidity = Column(Integer, nullable=True)  # 0-100
    max_humidity = Column(Integer, nullable=True)
    min_wind_speed = Column(Float, nullable=True)  # km/h

    # Display configuration
    display_priority = Column(Integer, default=50)  # Higher than normal content
    min_display_minutes = Column(Integer, default=30)  # Minimum display duration
    location_coordinates = Column(String(50), nullable=True)  # "lat,lon"

    # Control flags
    is_enabled = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SignageWeatherData(Base):

    __tablename__ = "signage_weather_data"

    id = Column(Integer, primary_key=True, index=True)
    location_coordinates = Column(String(50), nullable=False)  # "lat,lon"

    # Weather data
    temperature = Column(Float, nullable=True)  # Celsius
    feels_like = Column(Float, nullable=True)
    humidity = Column(Integer, nullable=True)  # 0-100%
    wind_speed = Column(Float, nullable=True)  # km/h
    wind_direction = Column(String(10), nullable=True)  # N, NE, E, etc.
    condition = Column(String(50), nullable=True)  # sunny, rainy, etc.
    description = Column(String(255), nullable=True)

    # Forecast
    forecast_high = Column(Float, nullable=True)
    forecast_low = Column(Float, nullable=True)
    forecast_condition = Column(String(50), nullable=True)

    # Tracking
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    data_source = Column(String(100), nullable=True)  # "openweathermap", etc., server_default=func.now())


class SignageOccupancySensor(Base):

    __tablename__ = "signage_occupancy_sensor"

    id = Column(Integer, primary_key=True, index=True)

    # Sensor configuration
    sensor_name = Column(String(255), nullable=False)
    sensor_location = Column(String(255), nullable=False)
    sensor_type = Column(
        String(50), nullable=False
    )  # "motion", "counting", "co2", etc.

    # Occupancy data
    current_occupancy_percent = Column(Integer, nullable=True)  # 0-100%
    current_occupancy_count = Column(Integer, nullable=True)  # Actual count
    occupancy_level = Column(SQLEnum(OccupancyLevel, values_callable=lambda x: [e.value for e in x]), nullable=True)
    capacity = Column(Integer, nullable=True)

    # Thresholds
    low_threshold = Column(Integer, default=10)
    high_threshold = Column(Integer, default=90)

    # API configuration for real-time data
    api_endpoint = Column(String(500), nullable=True)
    api_auth_token = Column(String(255), nullable=True)
    last_api_check = Column(DateTime(timezone=True), nullable=True)

    # Control flags
    is_active = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SignageOccupancyTrigger(Base):

    __tablename__ = "signage_occupancy_trigger"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="CASCADE"), nullable=False)
    occupancy_sensor_id = Column(
        Integer, ForeignKey("signage_occupancy_sensor.id", ondelete="CASCADE"), nullable=False
    )

    # Occupancy conditions
    trigger_level = Column(SQLEnum(OccupancyLevel, values_callable=lambda x: [e.value for e in x]), nullable=False)  # What level triggers this
    comparison = Column(String(20), default="equals")  # equals, above, below

    # Display configuration
    display_priority = Column(Integer, default=75)
    min_display_minutes = Column(Integer, default=15)

    # Control flags
    is_enabled = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SignageContentOptimization(Base):

    __tablename__ = "signage_content_optimization"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("signage_content.id", ondelete="CASCADE"), nullable=False)

    # Performance metrics
    engagement_score = Column(Float, nullable=True)  # 0-100
    visibility_score = Column(Float, nullable=True)  # Based on viewer counts
    interaction_rate = Column(Float, nullable=True)  # Interactions / views

    # Recommendations
    recommended_duration = Column(Integer, nullable=True)  # Seconds
    recommended_priority = Column(Integer, nullable=True)
    recommended_times = Column(String(500), nullable=True)  # "9-12,14-17"
    recommended_locations = Column(String(500), nullable=True)  # Display IDs

    # A/B Testing
    test_variant_id = Column(Integer, nullable=True)
    test_status = Column(String(50), nullable=True)  # "active", "completed", "winner"
    test_winner = Column(Boolean, default=False)

    # Optimization AI insights
    insights = Column(JSON, nullable=True)  # {"best_display": 5, "peak_hours": "9-12"}
    confidence_score = Column(Float, nullable=True)  # 0-1, server_default=func.now())
