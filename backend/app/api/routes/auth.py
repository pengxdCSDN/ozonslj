import inspect
from collections.abc import Awaitable, Callable
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from backend.app.api.dependencies import (
    LoginRateLimiter,
    get_default_organization_id,
    get_identity_service,
    get_login_rate_limiter,
    get_request_session_token,
    get_session_cookie_secure,
)
from backend.app.application.identity import IdentityService
from backend.app.domain.identity import AuthenticatedUser, LoginResult, OrganizationRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)

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
    role: OrganizationRole

    @classmethod
    def from_domain(cls, user: AuthenticatedUser) -> "CurrentUserResponse":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.organization_role,
        )


class LoginResponse(CurrentUserResponse):
    session_token: str | None = None


@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    limiter: Annotated[LoginRateLimiter, Depends(get_login_rate_limiter)],
    secure_cookie: Annotated[bool, Depends(get_session_cookie_secure)],
    organization_id: Annotated[str, Depends(get_default_organization_id)],
) -> LoginResponse:
    client_key = request.client.host if request.client else "unknown"
    retry_after = await limiter.retry_after(payload.email, client_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "login_rate_limited", "message": "登录尝试过多，请稍后重试"},
            headers={"Retry-After": str(retry_after)},
        )
    # 兼容尚未迁移到组织参数的测试替身/旧插件；正式 IdentityService 始终走组织隔离分支。
    login = cast(Callable[..., Awaitable[LoginResult | None]], service.login)
    if len(inspect.signature(login).parameters) == 2:
        result = await login(payload.email, payload.password)
    else:
        result = await login(payload.email, payload.password, organization_id)
    if result is None:
        await limiter.record_failure(payload.email, client_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "邮箱或密码无效"},
        )
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
    response.headers["Cache-Control"] = "no-store"
    user = CurrentUserResponse.from_domain(result.user)
    return LoginResponse(
        **user.model_dump(),
        session_token=None if secure_cookie else result.token,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    token: Annotated[str | None, Depends(get_request_session_token)],
) -> CurrentUserResponse:
    user = await service.authenticate(token) if token else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "登录已失效"},
        )
    response.headers["Cache-Control"] = "no-store"
    return CurrentUserResponse.from_domain(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    token: Annotated[str | None, Depends(get_request_session_token)],
) -> None:
    if token:
        await service.logout(token)
    response.delete_cookie("ozonslj_session", path="/", httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
