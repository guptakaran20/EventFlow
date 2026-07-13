from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import AuthenticatedPrincipal, require_api_key

router = APIRouter(prefix="/auth", tags=["auth"])


class VerifyResponse(BaseModel):
    authenticated: bool = True


@router.get("/verify", response_model=VerifyResponse)
async def verify(
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_api_key)],
) -> VerifyResponse:
    """Protected test endpoint proving API-key auth is enforced."""
    return VerifyResponse()
