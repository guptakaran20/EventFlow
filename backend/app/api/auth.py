import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    AuthenticatedPrincipal,
    authenticate_api_key,
    create_access_token,
    require_api_key,
)
from app.db.session import get_db_session
from app.models.api_key import APIKey
from app.models.refresh_token import RefreshToken

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    api_key: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    request: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    principal = await authenticate_api_key(request.api_key, db)

    token_data = {
        "api_key_id": str(principal.api_key_id),
    }

    access_token = create_access_token(data=token_data)

    settings = get_settings()
    raw_refresh_token = secrets.token_urlsafe(32)
    refresh_token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
    family_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    db_rt = RefreshToken(
        token_hash=refresh_token_hash,
        family_id=family_id,
        api_key_id=principal.api_key_id,
        expires_at=expires_at,
        is_valid=True,
    )
    db.add(db_rt)
    await db.commit()

    response.set_cookie(
        key="eventflow_jwt",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.jwt_access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="eventflow_refresh",
        value=raw_refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    body: RefreshRequest | None = None,
) -> TokenResponse:
    settings = get_settings()
    token = request.cookies.get("eventflow_refresh") or (body.refresh_token if body else None)
    if not token:
        raise AppError("Missing refresh token", code="missing_token", status_code=401)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    db_rt = result.scalar_one_or_none()

    if db_rt is None:
        raise AppError("Invalid refresh token", code="invalid_token", status_code=401)

    if not db_rt.is_valid:
        # Token reuse detected! Invalidate entire family.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == db_rt.family_id)
            .values(is_valid=False)
        )
        await db.commit()
        raise AppError("Refresh token reused", code="token_reused", status_code=401)

    if db_rt.expires_at < datetime.now(UTC):
        raise AppError("Refresh token expired", code="token_expired", status_code=401)

    # Invalidate current token
    db_rt.is_valid = False

    # Issue new tokens
    raw_refresh_token = secrets.token_urlsafe(32)
    new_token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    new_db_rt = RefreshToken(
        token_hash=new_token_hash,
        family_id=db_rt.family_id,
        api_key_id=db_rt.api_key_id,
        expires_at=expires_at,
        is_valid=True,
    )
    db.add(new_db_rt)
    await db.commit()

    token_data = {
        "api_key_id": str(db_rt.api_key_id),
    }
    access_token = create_access_token(data=token_data)

    response.set_cookie(
        key="eventflow_jwt",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.jwt_access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="eventflow_refresh",
        value=raw_refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    token = request.cookies.get("eventflow_refresh")
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_rt = result.scalar_one_or_none()
        if db_rt:
            db_rt.is_valid = False
            await db.commit()

    response.delete_cookie("eventflow_jwt", httponly=True, samesite="none", secure=True)
    response.delete_cookie("eventflow_refresh", httponly=True, samesite="none", secure=True)
    return {"message": "Logged out successfully"}


class MeResponse(BaseModel):
    api_key_id: uuid.UUID
    name: str


@router.get("/me", response_model=MeResponse)
async def get_current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MeResponse:
    """Returns information about the currently authenticated API key."""
    api_key_obj = await db.get(APIKey, principal.api_key_id)
    if api_key_obj is None:
        raise AppError("API key not found", code="unauthorized", status_code=401)
    return MeResponse(
        api_key_id=api_key_obj.id,
        name=api_key_obj.name,
    )


class VerifyResponse(BaseModel):
    authenticated: bool = True


@router.get("/verify", response_model=VerifyResponse)
async def verify(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
) -> VerifyResponse:
    """Protected test endpoint proving API-key auth is enforced."""
    return VerifyResponse()
