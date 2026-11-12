# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import contextlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password
from app.models.ai_config import AIConfiguration
from app.models.library_branding import LibraryBranding
from app.models.multi_branch import Branch, BranchStatus, BranchType, LibrarySystem, SystemSettings
from app.models.user import User, UserRole
from app.services.setup_service import is_demo_mode, is_setup_complete, is_setup_required

from app.api.v1.dependencies import get_current_user_optional, require_admin
from app.api.v1.organization_features import PRESETS, _serialize_features
from app.services.organization_features_service import OrganizationFeaturesService
from app.services.setup_progress_service import compute_setup_progress
from .schemas import (
    AdminAccountCreate,
    AiPrefsCreate,
    BrandingCreate,
    DomainUpdate,
    FeaturesCreate,
    LibraryInfoCreate,
    PoliciesCreate,
    SetupProgressResponse,
    SetupResponse,
    SetupStatusResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])

_BRANDING_CANDIDATES = [
    Path("/opt/l30/branding.json"),
    Path("/app/branding.json"),
    Path(__file__).resolve().parents[5] / "branding.json",
]


def _branding_path() -> Path:
    for p in _BRANDING_CANDIDATES:
        if p.exists():
            return p
    return _BRANDING_CANDIDATES[1]  # default to /app/branding.json


async def require_setup_access(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> None:
    """Gate for setup-wizard endpoints.

    - 404 once setup is complete (bootstrap-only surface, same as the old
      require_setup_not_complete).
    - Open during the pre-admin bootstrap window: there is no account to
      authenticate against yet, and whoever reaches a fresh install first
      owns it (standard first-run model).
    - Admin-only once a founding admin exists. Without this, every wizard
      endpoint (branding, policies, domain, demo load, feature presets,
      /setup/complete itself) stays writable by ANY anonymous caller until
      the wizard is marked complete -- and demo instances intentionally
      never mark it complete.
    """
    if await is_setup_complete(db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if await is_setup_required(db):
        return
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def _write_branding_json(updates: dict) -> None:
    """Best-effort merge-write into branding.json (boot-time defaults only).

    The live branding path is the LibraryBranding DB row; a read-only
    filesystem must not fail the wizard step, so OSError degrades to a
    warning instead of a 500.
    """
    path = _branding_path()
    existing: dict = {}
    if path.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            existing = json.loads(path.read_text())
    existing.update(updates)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing, indent=2))
    except OSError as e:
        logger.warning("Could not write %s (%s); branding persisted to DB only", path, e)


async def _upsert_library_branding(db: AsyncSession, **values) -> None:
    """Persist wizard branding into the LibraryBranding row (id=1).

    GET /branding serves file/env defaults overridden by this DB row; the
    branding.json writes below only feed boot-time defaults. Without the DB
    upsert, wizard choices never take effect on the live site. Caller commits.
    """
    result = await db.execute(select(LibraryBranding).where(LibraryBranding.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = LibraryBranding(id=1)
        db.add(row)
    for key, value in values.items():
        setattr(row, key, value)


@router.get("/progress", response_model=SetupProgressResponse)
async def get_setup_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SetupProgressResponse:
    library_system_id = current_user.home_library_system_id
    if library_system_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Current user is not attached to a library system",
        )
    steps = await compute_setup_progress(db, library_system_id)
    completed = sum(1 for s in steps if s["completed"])
    return SetupProgressResponse(
        library_system_id=library_system_id,
        completed_count=completed,
        total=len(steps),
        all_complete=completed == len(steps),
        steps=steps,
    )


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(db: AsyncSession = Depends(get_db)) -> SetupStatusResponse:
    settings = get_settings()
    setup_required = await is_setup_required(db)
    demo_mode = await is_demo_mode(db)
    return SetupStatusResponse(
        setup_required=setup_required,
        demo_mode=demo_mode,
        demo_public=settings.demo_public,
    )


@router.post("/admin", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_account(
    payload: AdminAccountCreate,
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    # Serialize concurrent bootstrap attempts. Two requests hitting the setup
    # window could both pass is_setup_required() (admin count == 0) and each
    # insert a SUPER_ADMIN. A transaction-scoped advisory lock (released on
    # commit) makes the check-and-insert atomic with no schema change. Postgres
    # only; the SQLite test DB is single-connection and has no such race.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(4030201)"))
    if not await is_setup_required(db) or await is_setup_complete(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin account already exists",
        )

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        # Fresh installs have no mail server configured yet, so there is no way
        # for the founding admin to click a verification link. Auto-verify the
        # wizard-created admin; login's email_verified check stays intact for
        # every other account.
        email_verified=True,
    )
    db.add(user)
    await db.commit()

    # Auto-login the founding admin: the remaining wizard steps are
    # admin-gated (require_setup_access), and a login round-trip here would
    # hit the Turnstile check with no widget in the wizard. Safe to mint:
    # this endpoint 409s whenever any admin already exists.
    access_token = create_access_token(
        subject=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )
    return SetupResponse(
        success=True,
        message="Admin account created",
        access_token=access_token,
    )


@router.post("/library-info", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def save_library_info(
    payload: LibraryInfoCreate,
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    result = await db.execute(select(LibrarySystem).limit(1))
    lib_sys = result.scalar_one_or_none()

    if lib_sys is None:
        lib_sys = LibrarySystem(
            code=payload.code.upper(),
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            address_line1=payload.address,
            city=payload.city,
            state=payload.state,
            zip_code=payload.zip_code,
            is_active=True,
        )
        db.add(lib_sys)
        await db.flush()

        branch = Branch(
            library_system_id=lib_sys.id,
            code="MAIN",
            name=payload.name,
            short_name=payload.code.upper(),
            branch_type=BranchType.MAIN,
            status=BranchStatus.ACTIVE,
            phone=payload.phone,
            email=payload.email,
            address_line1=payload.address,
            city=payload.city,
            state=payload.state,
            zip_code=payload.zip_code,
        )
        db.add(branch)

        # Backfill: founding admin(s) created before the library system existed
        # have home_library_system_id=NULL. Assign them to the new system now.
        await db.execute(
            update(User)
            .where(User.home_library_system_id.is_(None))
            .values(home_library_system_id=lib_sys.id)
        )

        settings_row = SystemSettings(
            library_system_id=lib_sys.id,
            setup_complete=False,
        )
        db.add(settings_row)
    else:
        lib_sys.name = payload.name
        lib_sys.code = payload.code.upper()
        lib_sys.email = payload.email
        lib_sys.phone = payload.phone
        lib_sys.address_line1 = payload.address
        lib_sys.city = payload.city
        lib_sys.state = payload.state
        lib_sys.zip_code = payload.zip_code

    # GET /branding only merges city/state/zip/phone from LibrarySystem;
    # name/email/address come from the LibraryBranding row, so mirror them
    # there or the live site keeps showing the stock defaults.
    identity: dict = {"library_name": payload.name}
    if payload.email:
        identity["contact_email"] = payload.email
    if payload.address:
        identity["address_line1"] = payload.address
    await _upsert_library_branding(db, **identity)

    await db.commit()
    return SetupResponse(success=True, message="Library info saved")


@router.post("/branding", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def save_branding(
    payload: BrandingCreate,
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    values: dict = {
        "primary_color": payload.primary_color,
        "accent_color": payload.accent_color,
    }
    if payload.hero_title is not None:
        values["hero_title"] = payload.hero_title
    if payload.tagline is not None:
        values["tagline"] = payload.tagline

    _write_branding_json(values)
    await _upsert_library_branding(db, **values)
    await db.commit()

    return SetupResponse(success=True, message="Branding saved")


@router.post("/branding/logo", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def upload_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    _LOGO_MIME_EXT = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    ctype = (file.content_type or "").lower().split(";")[0].strip()
    if ctype not in _LOGO_MIME_EXT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be a PNG, JPEG, GIF, or WebP image",
        )

    # Store under the uploads mount (see app.main /uploads StaticFiles) so the
    # logo has a servable URL. The old /app/static/branding location had no
    # route and the uploaded file was unreachable.
    import os
    logo_dir = Path(os.getenv("STORAGE_LOCAL_PATH", "/app/uploads")) / "branding"
    logo_dir.mkdir(parents=True, exist_ok=True)

    suffix = _LOGO_MIME_EXT[ctype]
    logo_path = logo_dir / f"logo{suffix}"
    # Drop a previous logo with a different extension so the row's logo_url
    # never points at a stale file.
    for old in logo_dir.glob("logo.*"):
        if old != logo_path:
            with contextlib.suppress(OSError):
                old.unlink()
    logo_path.write_bytes(await file.read())

    _write_branding_json({"logo_path": str(logo_path)})
    await _upsert_library_branding(db, logo_url=f"/uploads/branding/logo{suffix}")
    await db.commit()

    return SetupResponse(success=True, message="Logo uploaded")


@router.post("/policies", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def save_policies(
    payload: PoliciesCreate,
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    result = await db.execute(select(SystemSettings).limit(1))
    settings_row = result.scalar_one_or_none()

    if settings_row is None:
        lib_result = await db.execute(select(LibrarySystem).limit(1))
        lib_sys = lib_result.scalar_one_or_none()
        if lib_sys is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Library info must be saved before setting policies",
            )
        settings_row = SystemSettings(library_system_id=lib_sys.id, setup_complete=False)
        db.add(settings_row)

    settings_row.default_loan_period_days = payload.default_loan_period_days
    settings_row.default_renewal_limit = payload.default_renewal_limit
    settings_row.default_hold_limit = payload.default_hold_limit
    settings_row.default_overdue_fine_per_day = payload.default_overdue_fine_per_day
    settings_row.default_max_fine = payload.default_max_fine
    settings_row.grace_period_days = payload.grace_period_days
    settings_row.fine_free_juvenile = payload.fine_free_juvenile
    settings_row.lost_item_threshold_days = payload.lost_item_threshold_days

    await db.commit()
    return SetupResponse(success=True, message="Policies saved")


@router.post("/domain", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def save_domain(
    payload: DomainUpdate,
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    _write_branding_json({"domain": payload.domain})
    await _upsert_library_branding(db, domain=payload.domain)
    await db.commit()
    return SetupResponse(success=True, message="Domain saved")


@router.post("/demo/load", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def load_demo_data(db: AsyncSession = Depends(get_db)) -> SetupResponse:
    # Demo data and a real founding admin account must be able to coexist
    # during the wizard (e.g. create the admin first, then load sample data
    # to explore the system) -- require_setup_access allows that: open
    # pre-admin, admin-token-gated after, 404 once the wizard is complete.
    #
    # ORM-driven (app.seeds.demo_seeder) rather than a raw-SQL seed file --
    # see docs/dist-install-characterization.md §6 for why the old
    # demo/seed.sql approach was retired (never packaged into the backend
    # image, and stale against the PII-encrypted schema even when copied in
    # by hand).
    from app.seeds.demo_seeder import seed_demo

    result = await seed_demo(db)
    message = "Demo data already loaded" if result.get("skipped") else "Demo data loaded"
    return SetupResponse(success=True, message=message)


@router.post("/features", dependencies=[Depends(require_setup_access)])
async def save_features(
    payload: FeaturesCreate,
    db: AsyncSession = Depends(get_db),
):
    """Apply a feature preset + overrides during unauthenticated bootstrap.
    Reuses the same PRESETS + apply logic as the admin-gated /organization-features
    endpoint, attributed to the founding super_admin from POST /setup/admin."""
    if payload.preset not in PRESETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown preset '{payload.preset}'. Valid presets: {', '.join(PRESETS)}",
        )
    result = await db.execute(
        select(User).where(User.role == UserRole.SUPER_ADMIN).order_by(User.id).limit(1)
    )
    founder = result.scalar_one_or_none()
    if founder is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account must be created before setting features",
        )
    merged = {**PRESETS[payload.preset], **payload.overrides}
    features = await OrganizationFeaturesService.update_features(
        db=db, update_data=merged, updated_by=founder
    )
    return _serialize_features(features)


@router.post("/complete", response_model=SetupResponse, dependencies=[Depends(require_setup_access)])
async def complete_setup(db: AsyncSession = Depends(get_db)) -> SetupResponse:
    result = await db.execute(select(SystemSettings).limit(1))
    settings_row = result.scalar_one_or_none()

    if settings_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Library info must be saved before completing setup",
        )

    settings_row.setup_complete = True
    await db.commit()
    return SetupResponse(success=True, message="Setup complete")


@router.post("/policies/extract", dependencies=[Depends(require_setup_access)])
async def extract_policies(file: UploadFile = File(...)):
    """Upload a policy document and extract circulation values via AI."""
    from app.services.policy_extraction import extract_policies_from_document

    allowed_types = (
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=422, detail="File must be PDF, Word, or plain text")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")

    try:
        result = await extract_policies_from_document(content, file.filename or "doc.txt")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI extraction failed: {str(e)}") from e


@router.get('/update-status', dependencies=[Depends(require_setup_access)])
async def get_update_status():
    from app.services.update_checker import get_cached_update_info
    info = get_cached_update_info()
    return {'update_available': info is not None, 'update_info': info}


@router.post("/ai", dependencies=[Depends(require_setup_access)])
async def save_ai_prefs(
    payload: AiPrefsCreate,
    db: AsyncSession = Depends(get_db),
):
    """Persist AI preferences during unauthenticated bootstrap.
    Writes the full prefs into the `agent_chat` config (the key the generator
    reads `model` from) and merges `model` into the `ollama` config without
    disturbing its `base_url`. Guardrails are stored alongside but not applied
    to the separate ollama_admin guardrail tables."""
    agent_value = {
        "model": payload.model,
        "temperature": payload.temperature,
        "system_prompt": payload.system_prompt,
        "guardrails": payload.guardrails,
    }
    await _upsert_ai_config(db, "agent_chat", lambda cur: {**cur, **agent_value})
    await _upsert_ai_config(db, "ollama", lambda cur: {**cur, "model": payload.model})
    await db.commit()
    return {"status": "ok"}


async def _upsert_ai_config(db, key, mutate):
    result = await db.execute(select(AIConfiguration).where(AIConfiguration.config_key == key))
    row = result.scalar_one_or_none()
    if row is None:
        row = AIConfiguration(config_key=key, config_value={})
        db.add(row)
    row.config_value = mutate(dict(row.config_value or {}))
