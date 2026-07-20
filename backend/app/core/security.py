import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db_session
from app.services.api_key_service import APIKeyService

_settings = get_settings()
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


@dataclass
class AuthenticatedPrincipal:
    raw_key: str
    key_type: str
    api_key_id: uuid.UUID | None = None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_access_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_refresh_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


async def authenticate_api_key(
    api_key: str | None,
    db: AsyncSession,
) -> AuthenticatedPrincipal:
    """Validate a raw API key value against bootstrap and DB-backed keys.

    Used by the login endpoint to exchange a raw API key for a JWT.
    """
    if not api_key:
        raise AppError(
            "Missing API key",
            code="missing_api_key",
            status_code=401,
        )

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


async def resolve_api_key_id(
    principal: AuthenticatedPrincipal,
    db: AsyncSession,
) -> uuid.UUID:
    """Resolve an AuthenticatedPrincipal into a database APIKey UUID.

    If the principal is a bootstrap key, this lazily creates a dummy
    database record so foreign key constraints are satisfied.
    """
    if principal.api_key_id is None:
        raise AppError("Missing API key ID", code="unauthorized", status_code=401)

    return principal.api_key_id


async def get_current_principal_from_token(token: str | None) -> AuthenticatedPrincipal:
    if not token:
        raise AppError("Missing or invalid token", code="unauthorized", status_code=401)

    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_access_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise AppError("Invalid token type", code="invalid_token", status_code=401)

        raw_key = payload.get("raw_key")
        key_type = payload.get("key_type")
        api_key_id_str = payload.get("api_key_id")

        if raw_key is None or key_type is None:
            raise AppError("Invalid token payload", code="invalid_token", status_code=401)

        api_key_id = uuid.UUID(api_key_id_str) if api_key_id_str else None
        return AuthenticatedPrincipal(raw_key=raw_key, key_type=key_type, api_key_id=api_key_id)

    except jwt.ExpiredSignatureError:
        raise AppError("Token expired", code="token_expired", status_code=401) from None
    except jwt.PyJWTError:
        raise AppError("Invalid token", code="invalid_token", status_code=401) from None


async def get_token(
    request: Request, bearer_token: Annotated[str | None, Depends(_oauth2_scheme)]
) -> str | None:
    return request.cookies.get("eventflow_jwt") or bearer_token


async def require_api_key(
    token: Annotated[str | None, Depends(get_token)],
) -> AuthenticatedPrincipal:
    """Validate the token. Returns an AuthenticatedPrincipal."""
    return await get_current_principal_from_token(token)


async def require_api_key_id(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> uuid.UUID:
    return await resolve_api_key_id(principal, db)
