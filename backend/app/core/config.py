# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # App
    app_name: str = "L30 Library"
    debug: bool = Field(default=False, alias="DEBUG")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")

    # Uptime monitor (Uptime Kuma) feeding the public /status page
    kuma_base_url: str = Field(default="http://uptime-kuma:3001", alias="KUMA_BASE_URL")
    kuma_status_slug: str = Field(default="l30", alias="KUMA_STATUS_SLUG")
    # Push token for the scheduler heartbeat (Kuma "Push" monitor). When set, the
    # heartbeat check pings Kuma on every run so Kuma alerts if the pings stop
    # (a true dead man's switch that survives the backend dying). Empty = disabled.
    kuma_heartbeat_push_token: str = Field(default="", alias="KUMA_HEARTBEAT_PUSH_TOKEN")

    # Security
    trusted_hosts: str = Field(default="localhost", alias="TRUSTED_HOSTS")
    api_docs_enabled: bool = Field(default=False, alias="API_DOCS_ENABLED")

    # Database (REQUIRED - no default for security)
    database_url: str = Field(alias="DATABASE_URL")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_fallback_enabled: bool = Field(default=True, alias="RATE_LIMIT_FALLBACK_ENABLED")
    rate_limit_fallback_multiplier: float = Field(
        default=0.5, alias="RATE_LIMIT_FALLBACK_MULTIPLIER"
    )
    rate_limit_observe_only: bool = Field(default=True, alias="RATE_LIMIT_OBSERVE_ONLY")

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    redis_ssl: bool = Field(default=False, alias="REDIS_SSL")
    redis_ssl_cert_reqs: str = Field(default="required", alias="REDIS_SSL_CERT_REQS")
    redis_ssl_ca_certs: str = Field(default="", alias="REDIS_SSL_CA_CERTS")

    # Auth (REQUIRED - no default for security)
    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # JWT Key Rotation (OPTIONAL - for zero-downtime key rotation)
    jwt_secret_key: str = Field(
        default="", alias="JWT_SECRET_KEY"
    )  # Primary signing key (overrides secret_key if set)
    jwt_secret_key_previous: str = Field(
        default="", alias="JWT_SECRET_KEY_PREVIOUS"
    )  # Previous key for grace-period verification

    # Account security
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15, alias="LOCKOUT_DURATION_MINUTES")
    password_min_length: int = Field(default=8, alias="PASSWORD_MIN_LENGTH")

    # Cloudflare Turnstile (bot verification on public forms)
    # If unset, verification is fail-open in dev. Production deployments MUST set this.
    turnstile_secret_key: str | None = Field(default=None, alias="CF_TURNSTILE_SECRET")
    # Explicit self-host escape hatch: bypasses Turnstile verification entirely,
    # even in production, when no Cloudflare account exists to issue a secret.
    # Default False -- a hosted/production deployment that does not set this
    # keeps the existing fail-closed behavior. Opt-in only.
    turnstile_disabled: bool = Field(default=False, alias="TURNSTILE_DISABLED")

    # Whether admin-role accounts (admin/super_admin/director) are FORCED to set
    # up TOTP 2FA on login. Default True keeps the hardened behavior for hosted
    # deployments. Self-host/fork builds set this False so an operator can log in
    # and evaluate the system without standing up an authenticator app first
    # (2FA remains available to opt into via account settings, just not forced).
    require_admin_2fa: bool = Field(default=True, alias="REQUIRE_ADMIN_2FA")

    # Public records clerk notification (public-form submissions)
    public_records_clerk_email: str | None = Field(default=None, alias="PUBLIC_RECORDS_CLERK_EMAIL")

    # Email (Resend)
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    from_email: str = Field(default="noreply@example.com", alias="FROM_EMAIL")
    email_daily_send_cap: int = Field(default=500, alias="EMAIL_DAILY_SEND_CAP")
    # Minimum seconds between consecutive Resend API calls from this worker.
    # Resend's docs publish 5 req/s; 0.25s keeps us at 4 req/s with headroom.
    # Set to 0 to disable in-process pacing.
    resend_min_interval_s: float = Field(default=0.25, alias="RESEND_MIN_INTERVAL_S")
    email_alert_threshold: int = Field(
        default=100, alias="EMAIL_ALERT_THRESHOLD"
    )  # warn at this many sends/hour
    email_dedup_window_hours: int = Field(
        default=24, alias="EMAIL_DEDUP_WINDOW_HOURS"
    )  # suppress duplicate notifications within this window
    sms_enabled: bool = Field(
        default=False, alias="SMS_ENABLED"
    )  # gate SMS delivery in NotificationConfig (no provider wired; keep False until one is)

    # Temporary card trial
    temporary_card_trial_days: int = Field(default=7, alias="TEMPORARY_CARD_TRIAL_DAYS")

    # Monitoring & Logging
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=1.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # "json" or "text"

    # CORS
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", alias="CORS_ORIGINS"
    )

    # Scheduler settings (From time_config and financial_config)
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")
    library_timezone: str = Field(default="America/New_York", alias="LIBRARY_TIMEZONE")
    overdue_notice_interval_days: int = Field(default=7, alias="OVERDUE_NOTICE_INTERVAL_DAYS")
    hold_expiry_days: int = Field(default=7, alias="HOLD_EXPIRY_DAYS")
    overdue_fine_per_day: str = Field(default="0.25", alias="OVERDUE_FINE_PER_DAY")

    # Cache Warming
    cache_warming_enabled: bool = Field(default=True, alias="CACHE_WARMING_ENABLED")
    cache_refresh_interval_minutes: int = Field(default=30, alias="CACHE_REFRESH_INTERVAL_MINUTES")

    # Scheduler Job Store
    scheduler_job_store: str = Field(default="memory", alias="SCHEDULER_JOB_STORE")
    scheduler_retry_enabled: bool = Field(default=True, alias="SCHEDULER_RETRY_ENABLED")

    # EDI
    edi_polling_enabled: bool = Field(default=False, alias="EDI_POLLING_ENABLED")

    # Job Alerting
    job_alert_email: str = Field(default="", alias="JOB_ALERT_EMAIL")
    job_log_retention_days: int = Field(default=90, alias="JOB_LOG_RETENTION_DAYS")

    # Public Computers — automation
    # Both jobs default OFF; turn on per-branch after verifying behavior.
    computers_auto_no_show_enabled: bool = Field(
        default=False, alias="COMPUTERS_AUTO_NO_SHOW_ENABLED"
    )
    computers_auto_no_show_grace_minutes: int = Field(
        default=10, alias="COMPUTERS_AUTO_NO_SHOW_GRACE_MINUTES"
    )
    computers_auto_logout_enabled: bool = Field(
        default=False, alias="COMPUTERS_AUTO_LOGOUT_ENABLED"
    )

    # Endpoint Tracking & Monitoring
    enable_endpoint_tracking: bool = Field(default=True, alias="ENABLE_ENDPOINT_TRACKING")

    # Lost Item Detection
    lost_item_threshold_days: int = Field(default=30, alias="LOST_ITEM_THRESHOLD_DAYS")
    lost_item_default_replacement_cost: float = Field(
        default=25.00, alias="LOST_ITEM_DEFAULT_REPLACEMENT_COST"
    )
    lost_item_processing_fee: float = Field(default=5.00, alias="LOST_ITEM_PROCESSING_FEE")
    auto_convert_overdue_to_lost: bool = Field(default=True, alias="AUTO_CONVERT_OVERDUE_TO_LOST")
    found_item_credit_percentage: float = Field(default=100.0, alias="FOUND_ITEM_CREDIT_PERCENTAGE")
    found_item_grace_period_days: int = Field(default=365, alias="FOUND_ITEM_GRACE_PERIOD_DAYS")
    claims_returned_review_days: int = Field(default=30, alias="CLAIMS_RETURNED_REVIEW_DAYS")
    max_claims_per_patron_year: int = Field(default=3, alias="MAX_CLAIMS_PER_PATRON_YEAR")

    # Damage charge percentages (of replacement cost)
    minor_damage_charge_pct: float = Field(default=0.0, alias="MINOR_DAMAGE_CHARGE_PCT")
    moderate_damage_charge_pct: float = Field(default=25.0, alias="MODERATE_DAMAGE_CHARGE_PCT")
    severe_damage_charge_pct: float = Field(default=50.0, alias="SEVERE_DAMAGE_CHARGE_PCT")
    total_loss_damage_charge_pct: float = Field(default=100.0, alias="TOTAL_LOSS_DAMAGE_CHARGE_PCT")

    # Virus Scanning
    virus_scan_enabled: bool = Field(default=True, alias="VIRUS_SCAN_ENABLED")
    virus_scan_fail_on_error: bool = Field(default=True, alias="VIRUS_SCAN_FAIL_ON_ERROR")
    clamav_socket: str = Field(default="/var/run/clamav/clamd.sock", alias="CLAMAV_SOCKET")
    clamav_host: str = Field(default="", alias="CLAMAV_HOST")
    clamav_port: int = Field(default=3310, alias="CLAMAV_PORT")

    # SIP2 (read by the certificate-expiry monitor; the SIP2 self-checkout
    # kiosk server was never wired in and its dedicated-config fields were
    # removed with it)
    sip2_enabled: bool = Field(default=False, alias="SIP2_ENABLED")
    sip2_use_tls: bool = Field(default=True, alias="SIP2_USE_TLS")
    sip2_tls_cert: str = Field(default="", alias="SIP2_TLS_CERT")

    # Search Engine Configuration
    search_engine: str = Field(default="postgres", alias="SEARCH_ENGINE")
    elasticsearch_enabled: bool = Field(default=False, alias="ELASTICSEARCH_ENABLED")

    # PostgreSQL FTS tunables. Changing search_text_config requires rebuilding
    # the search_tsv generated column (see migration search_tsv_generated_001).
    search_text_config: str = Field(default="english", alias="SEARCH_TEXT_CONFIG")
    # pg_trgm similarity threshold (0.0-1.0). Lower = more recall, more noise.
    search_trigram_threshold: float = Field(default=0.15, alias="SEARCH_TRIGRAM_THRESHOLD")
    # ts_rank_cd normalization flag. Bit-OR of: 1=log(doc-length), 2=doc-length,
    # 4=mean harmonic distance, 8=unique-words, 16=log(unique+1), 32=rank/(rank+1).
    # 32 alone keeps scores in [0,1); 1|32 also penalises very long docs.
    search_ts_rank_normalization: int = Field(default=32, alias="SEARCH_TS_RANK_NORMALIZATION")
    # Reciprocal-rank-fusion constant. 60 is the published default; raise to
    # flatten contributions from top ranks, lower to amplify them.
    search_rrf_k: int = Field(default=60, alias="SEARCH_RRF_K")
    # Below this length, queries skip FTS and go straight to trigram.
    search_fts_min_query_length: int = Field(default=3, alias="SEARCH_FTS_MIN_QUERY_LENGTH")

    # Catalog cross-encoder reranker. Disabled by default until the model is
    # baked into the image and a per-library latency budget is verified.
    # When disabled, the ?rerank=true query param silently no-ops so we can
    # ship the UI affordance ahead of the model rollout.
    catalog_rerank_enabled: bool = Field(default=False, alias="CATALOG_RERANK_ENABLED")
    # How many FTS hits to feed the cross-encoder. ~50 is the sweet spot on
    # CPU: enough to catch a mis-ranked title 3 pages deep, few enough to
    # finish under the 1.5s latency budget per query.
    catalog_rerank_top_n_candidates: int = Field(
        default=50, alias="CATALOG_RERANK_TOP_N_CANDIDATES"
    )
    # Baked-image path. Overridable for dev so a host-side checkout can be
    # mounted in without rebuilding the image.
    catalog_rerank_model_path: str = Field(
        default="/app/models/bge-reranker-v2-m3",
        alias="CATALOG_RERANK_MODEL_PATH",
    )

    # AI / Embedding Services
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    google_books_api_key: str | None = Field(default=None, alias="GOOGLE_BOOKS_API_KEY")

    # MetisLib recruitment digest recipient; unset -> weekly digest job no-ops
    recruitment_digest_email: str | None = Field(default=None, alias="RECRUITMENT_DIGEST_EMAIL")

    # OCLC Submission Queue
    oclc_enabled: bool = Field(default=False, alias="OCLC_ENABLED")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_api_url: str = Field(
        default="https://api.openai.com/v1/embeddings", alias="EMBEDDING_API_URL"
    )
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")

    # Mapping API
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")
    mapbox_api_key: str = Field(default="", alias="MAPBOX_API_KEY")
    osrm_server_url: str = Field(default="https://router.project-osrm.org", alias="OSRM_SERVER_URL")

    # Ban Tracker — PEN America Index of School Book Bans (published CSV export).
    # Env-overridable so a sheet-ID change does not require a code deploy.
    pen_america_sheet_csv_url: str = Field(
        default="https://docs.google.com/spreadsheets/d/1slCpqLprPXHM-Wyt-WYJR30-NvbGLialVNR8qTsZFG8/export?format=csv",
        alias="PEN_AMERICA_SHEET_CSV_URL",
    )

    # HomeDelivery Settings
    home_delivery_reminder_days: int = Field(default=1, alias="HOME_DELIVERY_REMINDER_DAYS")
    home_delivery_feedback_delay_hours: int = Field(
        default=24, alias="HOME_DELIVERY_FEEDBACK_DELAY_HOURS"
    )

    # OpenTelemetry Distributed Tracing
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="l30-library", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_exporter_otlp_protocol: str = Field(default="grpc", alias="OTEL_EXPORTER_OTLP_PROTOCOL")
    otel_traces_sample_rate: float = Field(default=1.0, alias="OTEL_TRACES_SAMPLE_RATE")
    otel_log_spans: bool = Field(default=False, alias="OTEL_LOG_SPANS")

    # Feature Flags - External Services
    # These flags allow disabling expensive or unnecessary services while preserving all data
    # Palace Project (open-source library ebook/audiobook platform)
    palace_enabled: bool = Field(default=True, alias="PALACE_ENABLED")

    # Storage
    storage_local_path: str = Field(default="/app/uploads", alias="STORAGE_LOCAL_PATH")
    indie_ebook_storage_subdir: str = Field(
        default="indie_ebooks", alias="INDIE_EBOOK_STORAGE_SUBDIR"
    )

    @property
    def indie_ebook_storage_path(self) -> str:
        from pathlib import Path

        return str(Path(self.storage_local_path) / self.indie_ebook_storage_subdir)

    # Database Pool
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=15, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")
    database_require_ssl: bool = Field(default=False, alias="DATABASE_REQUIRE_SSL")

    # Indie OPDS import freeze — default frozen so MetisLib demo/seed titles
    # cannot flow into the owned catalog on an accidental re-import.
    indie_opds_import_enabled: bool = Field(default=False, alias="INDIE_OPDS_IMPORT_ENABLED")

    # MetisLib Platform Integration
    metislib_enabled: bool = Field(default=False, alias="METISLIB_ENABLED")
    metislib_mock: bool = Field(default=True, alias="METISLIB_MOCK")
    metislib_base_url: str = Field(default="http://localhost:8803", alias="METISLIB_BASE_URL")
    metislib_api_key: str = Field(default="", alias="METISLIB_API_KEY")
    metislib_library_id: str = Field(default="", alias="METISLIB_LIBRARY_ID")
    metislib_timeout_seconds: int = Field(default=10, alias="METISLIB_TIMEOUT_SECONDS")
    metislib_public_url: str = Field(default="https://metislib.org", alias="METISLIB_PUBLIC_URL")

    # Watermark / Social DRM
    watermark_enabled: bool = Field(default=False, alias="WATERMARK_ENABLED")
    watermark_secret_salt: str = Field(
        default="change-me-watermark-salt", alias="WATERMARK_SECRET_SALT"
    )
    library_id: str = Field(default="", alias="LIBRARY_ID")
    library_name: str = Field(default="My Library", alias="LIBRARY_NAME")

    # Library identity & contact (used by services that emit URLs/emails/RDF)
    library_website: str = Field(default="", alias="LIBRARY_WEBSITE")
    library_email: str = Field(default="library@example.com", alias="LIBRARY_EMAIL")
    support_email: str = Field(default="support@example.com", alias="SUPPORT_EMAIL")
    genealogy_email: str = Field(default="genealogy@example.com", alias="GENEALOGY_EMAIL")
    bibframe_base_uri: str = Field(default="https://example.com", alias="BIBFRAME_BASE_URI")
    schema_org_base_url: str = Field(default="https://example.com", alias="SCHEMA_ORG_BASE_URL")
    library_user_agent: str = Field(
        default="L30Library/1.0 (library@example.com)", alias="LIBRARY_USER_AGENT"
    )
    twitter_handle: str = Field(default="", alias="TWITTER_HANDLE")
    facebook_handle: str = Field(default="", alias="FACEBOOK_HANDLE")
    library_address: str = Field(default="", alias="LIBRARY_ADDRESS")
    library_city_state_zip: str = Field(default="", alias="LIBRARY_CITY_STATE_ZIP")
    library_phone: str = Field(default="", alias="LIBRARY_PHONE")
    library_service_area: str = Field(default="", alias="LIBRARY_SERVICE_AREA")
    library_latitude: float = Field(default=0.0, alias="LIBRARY_LATITUDE")
    library_longitude: float = Field(default=0.0, alias="LIBRARY_LONGITUDE")

    # Print-on-Demand (Lulu Direct)
    lulu_sandbox: bool = Field(default=True, alias="LULU_SANDBOX")
    lulu_client_key: str = Field(default="", alias="LULU_CLIENT_KEY")
    lulu_client_secret: str = Field(default="", alias="LULU_CLIENT_SECRET")
    lulu_webhook_secret: str = Field(default="", alias="LULU_WEBHOOK_SECRET")
    stripe_pod_webhook_secret: str = Field(default="", alias="STRIPE_POD_WEBHOOK_SECRET")

    # Stripe - Overflow Purchases
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_overflow_webhook_secret: str = Field(default="", alias="STRIPE_OVERFLOW_WEBHOOK_SECRET")

    # PII Encryption
    # Default is True in production (ENVIRONMENT=production) for data protection at rest
    # Can be explicitly disabled by setting PII_ENCRYPTION_ENABLED=false
    pii_encryption_enabled: bool = Field(default=True, alias="PII_ENCRYPTION_ENABLED")
    pii_encryption_key: str = Field(default="", alias="PII_ENCRYPTION_KEY")
    pii_encryption_key_previous: str = Field(default="", alias="PII_ENCRYPTION_KEY_PREVIOUS")
    # HMAC key for blind-index hashes (email_hash, name hashes, phone_hash).
    # Falls back to secret_key when unset so existing phone_hash values stay
    # valid. Set PII_HASH_KEY in .env.prod before deploy; rotating it
    # invalidates every blind index and requires a rehash backfill.
    pii_hash_key: str = Field(default="", alias="PII_HASH_KEY")
    # Dedicated key for encrypting stored vendor API tokens (SUSHI credentials).
    # Kept separate from SECRET_KEY so a session-signing key compromise does not
    # also expose stored vendor credentials. Falls back to secret_key in dev/test.
    token_encryption_key: str = Field(default="", alias="TOKEN_ENCRYPTION_KEY")
    # Dedicated key for encrypting TOTP (2FA) secrets. Kept separate from
    # SECRET_KEY so a session-signing key compromise does not also let an
    # attacker mint valid 2FA codes. Falls back to the legacy SECRET_KEY-derived
    # key when unset (no regression for existing installs). _PREVIOUS supports
    # rotation the same way PII_ENCRYPTION_KEY_PREVIOUS does.
    totp_encryption_key: str = Field(default="", alias="TOTP_ENCRYPTION_KEY")
    totp_encryption_key_previous: str = Field(default="", alias="TOTP_ENCRYPTION_KEY_PREVIOUS")

    # Audit Logging
    # Immutable audit log for security-critical events (logins, payments, permission changes)
    audit_log_enabled: bool = Field(default=True, alias="AUDIT_LOG_ENABLED")
    audit_log_path: str = Field(default="/var/log/l30/audit.log", alias="AUDIT_LOG_PATH")
    audit_log_signing_key: str = Field(default="", alias="AUDIT_LOG_SIGNING_KEY")

    # Download Tracking
    download_ip_hash_salt: str = Field(
        default="change-me-download-salt", alias="DOWNLOAD_IP_HASH_SALT"
    )
    download_retention_days: int = Field(default=90, alias="DOWNLOAD_RETENTION_DAYS")

    # Event Registration / Attendance Retention
    # Conservative defaults; staff can override via env. By default we
    # anonymize (rather than delete) so per-event aggregate counts stay stable.
    event_registration_retention_days: int = Field(
        default=365, alias="EVENT_REGISTRATION_RETENTION_DAYS"
    )
    attendance_record_retention_days: int = Field(
        default=730, alias="ATTENDANCE_RECORD_RETENTION_DAYS"
    )
    retention_anonymize_instead_of_delete: bool = Field(default=True, alias="RETENTION_ANONYMIZE")

    # Accessibility (Ace by DAISY)
    ace_binary_path: str = Field(default="npx", alias="ACE_BINARY_PATH")
    ace_timeout_seconds: int = Field(default=120, alias="ACE_TIMEOUT_SECONDS")

    # CourtListener API (bankruptcy filing data)
    courtlistener_api_token: str = Field(default="", alias="COURTLISTENER_API_TOKEN")

    # Umami analytics (website analytics proxy)
    umami_url: str = Field(default="", alias="UMAMI_URL")
    umami_username: str = Field(default="", alias="UMAMI_USERNAME")
    umami_password: str = Field(default="", alias="UMAMI_PASS")
    umami_website_id: str = Field(default="", alias="UMAMI_WEBSITE_ID")

    # Distributable packaging
    l30_version: str = Field(default="0.0.0-dev", alias="L30_VERSION")
    demo_public: bool = Field(default=False, alias="DEMO_PUBLIC")
    update_check: bool = Field(default=True, alias="UPDATE_CHECK")

    # ============ librarian-agent KB service ============
    # When base_url is empty, all emit/search calls are silently skipped
    # (dev/test default). API key header is omitted when api_key is empty.
    librarian_agent_base_url: str = Field(default="", alias="LIBRARIAN_AGENT_BASE_URL")
    librarian_agent_library_slug: str = Field(default="l30", alias="LIBRARIAN_AGENT_LIBRARY_SLUG")
    librarian_agent_api_key: str = Field(default="", alias="LIBRARIAN_AGENT_API_KEY")

    # Parent resource guide -- verification trail
    # Threshold above which an item is rendered as "stale" in the UI and
    # auto-styled with the rose-tinted card border. v1 is a single global
    # setting; spec Open Question 1 contemplates per-section thresholds
    # in v2.
    parent_resource_stale_after_months: int = Field(
        default=6, alias="PARENT_RESOURCE_STALE_AFTER_MONTHS"
    )

    class Config:
        env_file = (".env", "/secrets/.env.generated")
        extra = "ignore"

    @model_validator(mode="after")
    def validate_pii_encryption_config(self) -> "Settings":
        if self.pii_encryption_enabled and not self.pii_encryption_key:
            raise ValueError(
                "PII_ENCRYPTION_KEY must be set when PII_ENCRYPTION_ENABLED=true. "
                "This prevents silent data loss and ensures patron data protection. "
                "\n\nTo fix this:\n"
                '1. Generate a key: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"\n'
                "2. Set PII_ENCRYPTION_KEY in your environment or .env file\n"
                "3. Or disable encryption explicitly by setting PII_ENCRYPTION_ENABLED=false "
                "(not recommended for production)"
            )

        # Validate that previous key (if set) is a valid Fernet key
        if self.pii_encryption_key_previous:
            try:
                from cryptography.fernet import Fernet

                Fernet(self.pii_encryption_key_previous.encode())
            except Exception as e:
                raise ValueError(
                    f"PII_ENCRYPTION_KEY_PREVIOUS is not a valid Fernet key: {e}"
                ) from e

        # Validate that current key (if set) is a valid Fernet key
        if self.pii_encryption_enabled and self.pii_encryption_key:
            try:
                from cryptography.fernet import Fernet

                Fernet(self.pii_encryption_key.encode())
            except Exception as e:
                raise ValueError(f"PII_ENCRYPTION_KEY is not a valid Fernet key: {e}") from e

        # Validate security salts are not defaults in production
        if self.environment == "production":
            if not self.pii_encryption_enabled:
                # Hard fail, not a warning: encrypt_pii returns its input
                # unchanged when the feature is off, so a production boot with
                # this flag false silently stores plaintext in every
                # EncryptedString/EncryptedText column while model source,
                # column widths, and health checks all still look correct.
                raise ValueError(
                    "PII_ENCRYPTION_ENABLED must be true in production. "
                    "Patron PII columns store plaintext when it is off. "
                    "Set PII_ENCRYPTION_ENABLED=true and provide "
                    "PII_ENCRYPTION_KEY (generate with: python -c "
                    '"from cryptography.fernet import Fernet; '
                    'print(Fernet.generate_key().decode())")'
                )
            if self.pii_encryption_enabled and not self.pii_hash_key:
                raise ValueError(
                    "PII_HASH_KEY must be set in production when PII encryption "
                    "is enabled, so blind indexes (phone_hash, email_hash, name "
                    "hashes) key on a dedicated secret instead of silently "
                    "falling back to SECRET_KEY. Generate one with: "
                    'python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            if self.watermark_secret_salt == "change-me-watermark-salt":
                raise ValueError(
                    "WATERMARK_SECRET_SALT must be changed from default in production. "
                    'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            if not self.token_encryption_key:
                # Warn-only, not a hard fail: existing fork-and-gift installs
                # never set this var, and hard-failing here would break their
                # next rebuild. Falling back to SECRET_KEY is the documented
                # dev/test behavior (encryption.py:_get_token_fernet); this
                # just makes the fallback loud in production instead of silent.
                logger.warning(
                    "TOKEN_ENCRYPTION_KEY is not set in production. Stored vendor "
                    "API credentials (SUSHI) are being encrypted under a key "
                    "derived from SECRET_KEY instead of a dedicated secret. "
                    "Generate one with: "
                    'python -c "import secrets; print(secrets.token_urlsafe(32))" '
                    "and set TOKEN_ENCRYPTION_KEY."
                )
            if not self.totp_encryption_key:
                # Warn-only, not a hard fail: existing fork-and-gift installs
                # never set this var, and hard-failing here would break their
                # next rebuild. Falling back to SECRET_KEY is the documented
                # dev/test behavior (totp.py:_get_totp_fernet); this just
                # makes the fallback loud in production instead of silent.
                logger.warning(
                    "TOTP_ENCRYPTION_KEY is not set in production. Stored 2FA "
                    "TOTP secrets are being encrypted under a key derived "
                    "from SECRET_KEY instead of a dedicated secret. "
                    "Generate one with: "
                    'python -c "import secrets; print(secrets.token_urlsafe(32))" '
                    "and set TOTP_ENCRYPTION_KEY."
                )
            if self.download_ip_hash_salt == "change-me-download-salt":
                raise ValueError(
                    "DOWNLOAD_IP_HASH_SALT must be changed from default in production. "
                    'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            # SECRET_KEY signs session/JWT tokens. The shipped .env.dist placeholder
            # is public, so booting production with it lets anyone forge admin tokens
            # (create_access_token falls back to SECRET_KEY when JWT_SECRET_KEY is
            # unset). Fail closed, same as the salts above.
            if self.secret_key == "CHANGE_ME":
                raise ValueError(
                    "SECRET_KEY must be changed from the placeholder in production. "
                    "The .env.dist value 'CHANGE_ME' is public and would let an attacker "
                    "forge admin session tokens. Run ./setup.sh (it generates one), or set "
                    'it with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
                )
            # The dedicated JWT signing key is optional (empty falls back to SECRET_KEY),
            # but if set it must not be the placeholder either.
            if self.jwt_secret_key == "CHANGE_ME":
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from the placeholder in production, "
                    "or left empty to sign with SECRET_KEY. The placeholder 'CHANGE_ME' "
                    'is public. Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list.

        SECURITY (restores #175 / commit 941f8be96, dropped in a later refactor):
        - wildcard (*) never allowed (incompatible with allow_credentials=True)
        - every origin must be a valid http(s) URL
        - production additionally rejects localhost and non-HTTPS origins
        """
        import re

        # Filter blank entries: a trailing/doubled comma in CORS_ORIGINS
        # (e.g. "https://a.com,https://b.com,") used to produce a bare ""
        # in the list, which CORSMiddleware would treat as an allowed
        # origin literal.
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

        if "*" in origins:
            raise ValueError(
                "CORS wildcard origin '*' is not allowed. "
                "Wildcard origins are incompatible with allow_credentials=True "
                "and pose significant security risks. Use explicit origins instead."
            )

        url_pattern = re.compile(
            r"^https?://"  # protocol
            r"[a-zA-Z0-9]"  # start with alphanumeric
            r"[a-zA-Z0-9\-\.]*"  # domain chars
            r"[a-zA-Z0-9]"  # end with alphanumeric
            r"(:\d{1,5})?$"  # optional port
        )
        for origin in origins:
            if not url_pattern.match(origin):
                raise ValueError(
                    f"CORS origin '{origin}' is not a valid URL format. "
                    "Expected format: https://example.com or http://localhost:3000"
                )

        if self.environment == "production":
            for origin in origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(
                        f"CORS origin '{origin}' contains localhost - not allowed in production"
                    )
                if not origin.startswith("https://"):
                    raise ValueError(
                        f"CORS origin '{origin}' must use HTTPS in production. "
                        "HTTP origins are not secure for production deployments."
                    )

        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
