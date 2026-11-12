# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.ai_guardrails import AIGuardrail, AIModelAllowlist, AIUsageLimit, AIUsageLog

logger = get_logger(__name__)


class GuardrailResult:
    def __init__(self):
        self.blocked = False
        self.block_reason: Optional[str] = None
        self.triggered_ids: List[int] = []
        self.system_prompt_additions: List[str] = []
        self.response_disclaimers: List[Tuple[str, str]] = []  # (text, position)
        self.max_response_length: Optional[int] = None
        self.block_urls = False
        self.block_code = False


async def check_prompt_guardrails(
    db: AsyncSession,
    prompt: str,
    tool_id: Optional[str] = None,
    is_minor: bool = False,
    patron_type: Optional[str] = None,
) -> GuardrailResult:
    result = GuardrailResult()

    # Load all enabled guardrails, ordered by priority
    query = select(AIGuardrail).where(AIGuardrail.enabled == True).order_by(AIGuardrail.priority)
    guardrails = (await db.execute(query)).scalars().all()

    prompt_lower = prompt.lower()

    for guardrail in guardrails:
        # Check if this guardrail applies to this tool
        applies_to = guardrail.applies_to_tools or []
        if applies_to and tool_id and tool_id not in applies_to:
            continue

        # Minor audience scoping
        audience = (guardrail.audience_minor or "all").lower()
        if audience == "minors_only" and not is_minor:
            continue
        if audience == "adults_only" and is_minor:
            continue

        # Patron-type scoping. Empty list = applies to all types.
        scoped_types = guardrail.audience_patron_types or []
        if scoped_types and (patron_type is None or patron_type not in scoped_types):
            continue

        config = guardrail.rule_config or {}

        if guardrail.rule_type == "blocked_topic":
            keywords = config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in prompt_lower:
                    result.blocked = True
                    result.block_reason = config.get("message", "That topic is not available.")
                    result.triggered_ids.append(guardrail.id)
                    return result

        elif guardrail.rule_type == "response_prefix":
            prefix = config.get("text", "")
            if prefix:
                result.system_prompt_additions.append(prefix)
                result.triggered_ids.append(guardrail.id)

        elif guardrail.rule_type == "required_disclaimer":
            text = config.get("text", "")
            position = config.get("position", "append")
            if text:
                result.response_disclaimers.append((text, position))
                result.triggered_ids.append(guardrail.id)

        elif guardrail.rule_type == "content_filter":
            max_len = config.get("max_length")
            if max_len:
                result.max_response_length = max_len
            if config.get("block_urls"):
                result.block_urls = True
            if config.get("block_code"):
                result.block_code = True
            result.triggered_ids.append(guardrail.id)

    return result


def apply_youth_guardrails(
    guardrail_result: GuardrailResult,
    user,
) -> GuardrailResult:
    if user is None:
        return guardrail_result

    is_teen = getattr(user, "is_teen", False)
    is_minor = getattr(user, "is_minor", False)

    if not is_teen and not is_minor:
        return guardrail_result

    guardrail_result.system_prompt_additions.append(
        "The current user is a minor. Keep all responses age-appropriate. "
        "Do not generate reading recommendations that reference or reveal "
        "this user's borrowing history, reading patterns, or hold list."
    )

    return guardrail_result


def apply_response_guardrails(
    response_text: str,
    guardrail_result: GuardrailResult,
) -> str:
    text = response_text

    # Trim length
    if guardrail_result.max_response_length and len(text) > guardrail_result.max_response_length:
        text = text[: guardrail_result.max_response_length] + "..."

    # Strip URLs
    if guardrail_result.block_urls:
        text = re.sub(r"https?://\S+", "[link removed]", text)

    # Strip code blocks
    if guardrail_result.block_code:
        text = re.sub(r"```[\s\S]*?```", "[code removed]", text)
        text = re.sub(r"`[^`]+`", "[code removed]", text)

    # Add disclaimers
    for disclaimer_text, position in guardrail_result.response_disclaimers:
        if position == "prepend":
            text = f"{disclaimer_text}\n\n{text}"
        else:
            text = f"{text}\n\n{disclaimer_text}"

    return text


def build_guarded_system_prompt(
    original_prompt: str,
    guardrail_result: GuardrailResult,
) -> str:
    additions = guardrail_result.system_prompt_additions
    if not additions:
        return original_prompt

    prefix = " ".join(additions)
    return f"{prefix}\n\n{original_prompt}"


async def check_usage_limits(
    db: AsyncSession,
    user_id: int,
    user_role: str,
) -> Tuple[bool, Optional[str]]:
    # Get the limit for this role
    result = await db.execute(
        select(AIUsageLimit).where(
            and_(AIUsageLimit.role == user_role, AIUsageLimit.enabled == True)
        )
    )
    limit = result.scalar_one_or_none()

    if not limit:
        return True, None  # No limit configured = unlimited

    now = datetime.now(timezone.utc)

    # Check hourly limit
    hour_ago = now - timedelta(hours=1)
    hourly_count_result = await db.execute(
        select(func.count(AIUsageLog.id)).where(
            and_(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= hour_ago,
                AIUsageLog.was_blocked == False,
            )
        )
    )
    hourly_count = hourly_count_result.scalar() or 0

    if hourly_count >= limit.hourly_limit:
        return (
            False,
            f"Hourly AI usage limit reached ({limit.hourly_limit} requests/hour). Please try again later.",
        )

    # Check daily limit
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count_result = await db.execute(
        select(func.count(AIUsageLog.id)).where(
            and_(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= day_start,
                AIUsageLog.was_blocked == False,
            )
        )
    )
    daily_count = daily_count_result.scalar() or 0

    if daily_count >= limit.daily_limit:
        return (
            False,
            f"Daily AI usage limit reached ({limit.daily_limit} requests/day). Please try again tomorrow.",
        )

    return True, None


def check_minor_access(tool, user) -> Tuple[bool, Optional[str]]:
    block_for_minors = bool(getattr(tool, "block_for_minors", False))
    requires_consent = bool(getattr(tool, "requires_parental_consent", False))
    blocked_types = list(getattr(tool, "block_for_patron_types", None) or [])

    if user is None:
        if block_for_minors or requires_consent:
            return False, "Sign in is required to use this AI tool."
        return True, None

    is_minor = bool(getattr(user, "is_minor", False))
    patron_type = getattr(user, "patron_type", None)

    if block_for_minors and is_minor:
        return False, "This AI tool isn't available for younger users."

    if patron_type and patron_type in blocked_types:
        return False, "This AI tool isn't available for your account type."

    if requires_consent and is_minor and not bool(getattr(user, "parental_consent_given", False)):
        return False, "A parent or guardian must give consent before you can use this AI tool."

    return True, None


async def check_model_allowed(
    db: AsyncSession,
    model_name: str,
) -> Tuple[bool, Optional[str]]:
    # Check if any entries exist at all
    count_result = await db.execute(
        select(func.count(AIModelAllowlist.id)).where(AIModelAllowlist.enabled == True)
    )
    total = count_result.scalar() or 0

    if total == 0:
        return True, None  # No allowlist = all allowed

    # Check if this specific model is allowed
    result = await db.execute(
        select(AIModelAllowlist).where(
            and_(
                AIModelAllowlist.model_name == model_name,
                AIModelAllowlist.enabled == True,
            )
        )
    )
    allowed_model = result.scalar_one_or_none()

    if not allowed_model:
        return False, f"Model '{model_name}' is not on the approved model list."

    return True, None


async def log_ai_usage(
    db: AsyncSession,
    user_id: Optional[int],
    tool_id: Optional[str],
    model_used: Optional[str],
    prompt: str,
    response: Optional[str],
    generation_time_ms: Optional[int],
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    guardrail_result: Optional[GuardrailResult] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    system_prompt: Optional[str] = None,
    was_minor: bool = False,
    patron_type_at_request: Optional[str] = None,
    log_content: bool = True,
) -> AIUsageLog:
    # log_content=False is the patron-chat privacy gate: patron questions are a
    # reading-history record, so nothing that names or quotes the patron may be
    # written. Enforced here (not just at the call site) so a caller can't
    # accidentally leak these by passing real values with log_content=False --
    # the function is the actual privacy boundary. Only ai_tools.py's staff
    # path relies on the log_content=True default; do not change that default.
    log = AIUsageLog(
        user_id=user_id if log_content else None,
        tool_id=tool_id,
        model_used=model_used,
        prompt_preview=(prompt[:500] if prompt else None) if log_content else None,
        system_prompt_used=system_prompt if log_content else None,
        response_preview=(response[:500] if response else None) if log_content else None,
        generation_time_ms=generation_time_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        guardrails_triggered=guardrail_result.triggered_ids if guardrail_result else [],
        was_blocked=guardrail_result.blocked if guardrail_result else False,
        block_reason=guardrail_result.block_reason if guardrail_result else None,
        was_minor=was_minor if log_content else False,
        patron_type_at_request=patron_type_at_request if log_content else None,
        success=success,
        error_message=error_message,
    )
    db.add(log)
    await db.flush()
    return log
