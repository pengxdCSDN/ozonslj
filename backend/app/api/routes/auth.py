from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from backend.app.api.dependencies import (
    LoginRateLimiter,
    get_identity_service,
    get_login_rate_limiter,
    get_request_session_token,
    get_session_cookie_secure,
)
from backend.app.application.identity import IdentityService
from backend.app.domain.identity import AuthenticatedUser, OperatorRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])
IdentityServiceDependency = Annotated[IdentityService, Depends(get_identity_service)]
SecureCookieDependency = Annotated[bool, Depends(get_session_cookie_secure)]
SessionTokenDependency = Annotated[str | None, Depends(get_request_session_token)]
LoginRateLimiterDependency = Annotated[LoginRateLimiter, Depends(get_login_rate_limiter)]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("邮箱格式不正确")
        return normalized


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: OperatorRole
    workspace_ids: list[str]

    @classmethod
    def from_domain(cls, user: AuthenticatedUser) -> "CurrentUserResponse":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            workspace_ids=list(user.workspace_ids),
        )


class LoginResponse(CurrentUserResponse):
    session_token: str | None = None


@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
    secure_cookie: SecureCookieDependency,
    limiter: LoginRateLimiterDependency,
) -> LoginResponse:
    client_key = request.client.host if request.client else "unknown"
    retry_after = await limiter.retry_after(payload.email, client_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过多，请稍后重试",
            headers={"Retry-After": str(retry_after)},
        )
    result = await service.login(payload.email, payload.password)
    if result is None:
        await limiter.record_failure(payload.email, client_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    await limiter.clear(payload.email, client_key)
    response.set_cookie(
        "ozonslj_session",
        result.token,
        expires=result.expires_at,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )
    user = CurrentUserResponse.from_domain(result.user)
    return LoginResponse(
        **user.model_dump(),
        session_token=None if secure_cookie else result.token,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    service: IdentityServiceDependency,
    session: SessionTokenDependency,
) -> CurrentUserResponse:
    user = await service.authenticate(session) if session else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    return CurrentUserResponse.from_domain(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    service: IdentityServiceDependency,
    session: SessionTokenDependency,
) -> None:
    if session:
        await service.logout(session)
    response.delete_cookie("ozonslj_session", path="/", httponly=True, samesite="lax")
