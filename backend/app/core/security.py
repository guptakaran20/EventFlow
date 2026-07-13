import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db_session
from app.services.api_key_service import APIKeyService

_settings = get_settings()
_api_key_scheme = APIKeyHeader(name=_settings.api_key_header_name, auto_error=False)


@dataclass
class AuthenticatedPrincipal:
    raw_key: str
    key_type: str
    api_key_id: uuid.UUID | None = None


async def require_api_key(
    api_key: Annotated[str | None, Depends(_api_key_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthenticatedPrincipal:
    """Validate the X-EventFlow-API-Key header.

    Checks the bootstrap key list first (no DB access) so local/dev setups
    and existing tests keep working without a database. Falls back to
    hashed, DB-backed keys (`APIKeyService`). Returns an AuthenticatedPrincipal.
    """
    settings = get_settings()

    if not api_key:
        raise AppError(
            "Missing API key",
            code="missing_api_key",
            status_code=401,
        )

    if api_key in settings.bootstrap_api_keys_list:
        return AuthenticatedPrincipal(raw_key=api_key, key_type="bootstrap")

    db_key = await APIKeyService(db).get_by_raw_key(api_key)
    if db_key is not None:
        db_key.last_used_at = datetime.now(UTC)
        await db.commit()
        return AuthenticatedPrincipal(raw_key=api_key, key_type="db", api_key_id=db_key.id)

    raise AppError(
        "Invalid API key",
        code="invalid_api_key",
        status_code=401,
    )


async def require_api_key_id(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> uuid.UUID:
    """Resolve an AuthenticatedPrincipal into a database APIKey UUID.

    If the principal is a bootstrap key, this lazily creates a dummy
    database record so foreign key constraints are satisfied.
    """
    if principal.key_type == "bootstrap":
        api_key_service = APIKeyService(db)
        key = await api_key_service.get_or_create_bootstrap_api_key(principal.raw_key)
        return key.id

    if principal.api_key_id is None:
        raise AppError("Missing API key ID", code="unauthorized", status_code=401)

    return principal.api_key_id
