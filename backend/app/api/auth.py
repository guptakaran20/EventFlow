from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    AuthenticatedPrincipal,
    authenticate_api_key,
    create_access_token,
    create_refresh_token,
    require_api_key,
)
from app.db.session import get_db_session

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
        "raw_key": principal.raw_key,
        "key_type": principal.key_type,
        "api_key_id": str(principal.api_key_id) if principal.api_key_id else None,
    }

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    settings = get_settings()

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
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
) -> TokenResponse:
    settings = get_settings()
    token = request.cookies.get("eventflow_refresh") or (body.refresh_token if body else None)
    if not token:
        raise AppError("Missing refresh token", code="missing_token", status_code=401)

    try:
        payload = jwt.decode(
            token, settings.jwt_refresh_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise AppError("Invalid token type", code="invalid_token", status_code=401)

        token_data = {
            "raw_key": payload.get("raw_key"),
            "key_type": payload.get("key_type"),
            "api_key_id": payload.get("api_key_id"),
        }

        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

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
            value=refresh_token,
            httponly=True,
            samesite="none",
            secure=True,
            max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        )

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    except jwt.ExpiredSignatureError:
        raise AppError("Refresh token expired", code="token_expired", status_code=401)
    except jwt.PyJWTError:
        raise AppError("Invalid refresh token", code="invalid_token", status_code=401)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("eventflow_jwt", httponly=True, samesite="none", secure=True)
    response.delete_cookie("eventflow_refresh", httponly=True, samesite="none", secure=True)
    return {"message": "Logged out successfully"}


class MeResponse(BaseModel):
    raw_key: str
    key_type: str


@router.get("/me", response_model=MeResponse)
async def get_current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
) -> MeResponse:
    """Returns information about the currently authenticated user/key."""
    return MeResponse(
        raw_key=principal.raw_key,
        key_type=principal.key_type,
    )


class VerifyResponse(BaseModel):
    authenticated: bool = True


@router.get("/verify", response_model=VerifyResponse)
async def verify(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
) -> VerifyResponse:
    """Protected test endpoint proving API-key auth is enforced."""
    return VerifyResponse()
