# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

# Re-export everything from the notifications package for backward compatibility.
# Any code that imports from `unified_notification_service` will continue to work.
from .notifications import (
    # Types
    NotificationType,
    NotificationChannel,
    NotificationTemplate,
    NotificationContent,
    NotificationRecipient,
    NotificationResult,
    NotificationConfig,
    # Domain-specific type enums
    CirculationNotificationType,
    MakerspaceNotificationType,
    DeliveryNotificationType,
    AlertNotificationType,
    EmergencyNotificationType,
    PayoutNotificationType,
    ReviewNotificationType,
    # Base class
    BaseNotificationService,
    # Domain services
    CirculationNotificationService,
    EmergencyNotificationService,
    MakerspaceNotificationService,
    DeliveryNotificationService,
    AlertNotificationService,
    # Template provider
    DomainTemplateProvider,
    # Facade and factory
    UnifiedNotificationService,
    NotificationFactory,
    # Singleton instances
    notification_service,
    notification_factory,
)

# Backward compatibility alias: some callers import NotificationType
# from this module as UnifiedNotificationType
UnifiedNotificationType = NotificationType

__all__ = [
    # Types
    "NotificationType",
    "UnifiedNotificationType",
    "NotificationChannel",
    "NotificationTemplate",
    "NotificationContent",
    "NotificationRecipient",
    "NotificationResult",
    "NotificationConfig",
    # Domain-specific type enums
    "CirculationNotificationType",
    "MakerspaceNotificationType",
    "DeliveryNotificationType",
    "AlertNotificationType",
    "EmergencyNotificationType",
    "PayoutNotificationType",
    "ReviewNotificationType",
    # Base class
    "BaseNotificationService",
    # Domain services
    "CirculationNotificationService",
    "EmergencyNotificationService",
    "MakerspaceNotificationService",
    "DeliveryNotificationService",
    "AlertNotificationService",
    # Template provider
    "DomainTemplateProvider",
    # Facade and factory (backward compatibility)
    "UnifiedNotificationService",
    "NotificationFactory",
    "notification_service",
    "notification_factory",
]
