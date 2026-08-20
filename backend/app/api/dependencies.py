"""说明本模块的职责、边界和主要协作对象。"""

from functools import lru_cache
from typing import Annotated, Protocol, cast

from fastapi import Cookie, Depends, Header, HTTPException, status
from redis.asyncio import Redis

from backend.app.application.identity import IdentityService
from backend.app.application.seller_accounts import SellerAccountService
from backend.app.config import get_settings
from backend.app.domain.advertising_analysis import AdvertisingAnalysisGateway
from backend.app.domain.advertising_calendar import AdvertisingCalendarGateway
from backend.app.domain.advertising_campaign import AdvertisingCampaignGateway
from backend.app.domain.advertising_keyword_diagnosis import AdvertisingKeywordDiagnosisGateway
from backend.app.domain.advertising_metrics import AdvertisingMetricsGateway
from backend.app.domain.advertising_readonly import AdvertisingBoundaryGateway
from backend.app.domain.advertising_report import AdvertisingReportGateway
from backend.app.domain.advertising_thresholds import AdvertisingThresholdGateway
from backend.app.domain.agent_permissions import AgentPermissionGateway
from backend.app.domain.agent_trigger import AgentTriggerGateway
from backend.app.domain.audit_event_store import AuditEventGateway
from backend.app.domain.competition_analysis import CompetitionAnalysisGateway
from backend.app.domain.competitor_seed import CompetitorSeedGateway
from backend.app.domain.competitor_selection_analysis import CompetitorSelectionAnalysisGateway
from backend.app.domain.cost_sensitivity import CostSensitivityGateway
from backend.app.domain.customer_order import CustomerOrderGateway
from backend.app.domain.data_freshness import DataFreshnessGateway
from backend.app.domain.data_provenance import DataProvenanceGateway
from backend.app.domain.data_quality import QualityFindingGateway
from backend.app.domain.diff_preview import DiffPreviewGateway
from backend.app.domain.execution_result_store import ExecutionResultGateway
from backend.app.domain.external_notification import ExternalNotificationGateway
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.inventory_analysis import InventoryAnalysisGateway
from backend.app.domain.keyword_import import KeywordImportGateway
from backend.app.domain.listing_fabe import ListingFabeGateway
from backend.app.domain.listing_keyword import ListingKeywordGateway
from backend.app.domain.listing_layering import ListingLayerGateway
from backend.app.domain.listing_publish import ListingPublishGateway
from backend.app.domain.listing_risk import ListingRiskGateway
from backend.app.domain.listing_title_draft import ListingTitleDraftGateway
from backend.app.domain.listing_version import ListingVersionGateway
from backend.app.domain.manual_approval import ManualApprovalGateway
from backend.app.domain.model_adapter import ModelAdapterGateway
from backend.app.domain.parser_alert import ParserAlertGateway
from backend.app.domain.performance_credentials import PerformanceCredentialGateway
from backend.app.domain.posting import PostingGateway
from backend.app.domain.profit_model import ProfitModelGateway
from backend.app.domain.public_snapshot import PublicSnapshotGateway
from backend.app.domain.readback_store import ReadbackVerificationGateway
from backend.app.domain.readonly_tool import ReadonlyToolGateway
from backend.app.domain.sales_analysis import SalesAnalysisGateway
from backend.app.domain.search_attributes import SearchAttributesGateway
from backend.app.domain.selection_decision_book import SelectionDecisionBookGateway
from backend.app.domain.selection_expand import ExpandResultGateway
from backend.app.domain.selection_explore import ExploreOpportunityGateway
from backend.app.domain.selection_validate import ValidateResultGateway
from backend.app.domain.seller_account import CreatedSellerAccount
from backend.app.domain.seller_fulfillment_snapshot import SellerFulfillmentSnapshotGateway
from backend.app.domain.seller_operation import SellerOperationGateway
from backend.app.domain.seller_order_snapshot import SellerOrderSnapshotGateway
from backend.app.domain.seller_product_snapshot import SellerProductSnapshotGateway
from backend.app.domain.seller_stock_snapshot import SellerStockSnapshotGateway
from backend.app.domain.smart_search import SmartSearchGateway
from backend.app.domain.stock_position import StockPositionGateway
from backend.app.domain.store_workspace import (
    CredentialProtector,
    OzonCredentials,
    SellerAccountVerifier,
    StoreWorkspaceGateway,
)
from backend.app.domain.summary_report import SummaryReportGateway
from backend.app.domain.sync_job import SyncJobGateway
from backend.app.infrastructure.credential_protection import (
    FernetCredentialProtector,
)
from backend.app.infrastructure.login_rate_limit import RedisLoginRateLimiter
from backend.app.infrastructure.model_credentials import ModelCredentialStore
from backend.app.infrastructure.ozon.account_verifier import (
    HttpOzonSellerAccountVerifier,
    StubSellerAccountVerifier,
)
from backend.app.infrastructure.ozon.gateway import (
    ProductOfferGateway,
)
from backend.app.infrastructure.postgres.model_budgets import PostgresModelBudgetGateway
from backend.app.infrastructure.postgresql.advertising_analysis import (
    PostgresAdvertisingAnalysisGateway,
)
from backend.app.infrastructure.postgresql.advertising_calendar import (
    PostgresAdvertisingCalendarGateway,
)
from backend.app.infrastructure.postgresql.advertising_campaigns import (
    PostgresAdvertisingCampaignGateway,
)
from backend.app.infrastructure.postgresql.advertising_keyword_diagnosis import (
    PostgresAdvertisingKeywordDiagnosisGateway,
)
from backend.app.infrastructure.postgresql.advertising_metrics import (
    PostgresAdvertisingMetricsGateway,
)
from backend.app.infrastructure.postgresql.advertising_readonly import (
    PostgresAdvertisingBoundaryGateway,
)
from backend.app.infrastructure.postgresql.advertising_reports import (
    PostgresAdvertisingReportGateway,
)
from backend.app.infrastructure.postgresql.advertising_thresholds import (
    PostgresAdvertisingThresholdGateway,
)
from backend.app.infrastructure.postgresql.agent_permissions import PostgresAgentPermissionGateway
from backend.app.infrastructure.postgresql.agent_triggers import PostgresAgentTriggerGateway
from backend.app.infrastructure.postgresql.audit_events import PostgresAuditEventGateway
from backend.app.infrastructure.postgresql.competition_analyses import (
    PostgresCompetitionAnalysisGateway,
)
from backend.app.infrastructure.postgresql.competitor_seeds import PostgresCompetitorSeedGateway
from backend.app.infrastructure.postgresql.competitor_selection_analysis import (
    PostgresCompetitorSelectionAnalysisGateway,
)
from backend.app.infrastructure.postgresql.cost_sensitivity import PostgresCostSensitivityGateway
from backend.app.infrastructure.postgresql.customer_orders import (
    PostgresCustomerOrderGateway,
)
from backend.app.infrastructure.postgresql.data_freshness import PostgresDataFreshnessGateway
from backend.app.infrastructure.postgresql.data_provenance import PostgresDataProvenanceGateway
from backend.app.infrastructure.postgresql.data_quality import PostgresQualityFindingGateway
from backend.app.infrastructure.postgresql.diff_previews import PostgresDiffPreviewGateway
from backend.app.infrastructure.postgresql.execution_results import PostgresExecutionResultGateway
from backend.app.infrastructure.postgresql.external_notifications import (
    PostgresExternalNotificationGateway,
)
from backend.app.infrastructure.postgresql.identity import PostgresIdentityGateway
from backend.app.infrastructure.postgresql.inventory_analysis import (
    PostgresInventoryAnalysisGateway,
)
from backend.app.infrastructure.postgresql.keyword_imports import PostgresKeywordImportGateway
from backend.app.infrastructure.postgresql.listing_fabe import PostgresListingFabeGateway
from backend.app.infrastructure.postgresql.listing_keyword_layers import PostgresListingLayerGateway
from backend.app.infrastructure.postgresql.listing_keywords import PostgresListingKeywordGateway
from backend.app.infrastructure.postgresql.listing_publish import PostgresListingPublishGateway
from backend.app.infrastructure.postgresql.listing_risks import PostgresListingRiskGateway
from backend.app.infrastructure.postgresql.listing_title_drafts import (
    PostgresListingTitleDraftGateway,
)
from backend.app.infrastructure.postgresql.listing_versions import PostgresListingVersionGateway
from backend.app.infrastructure.postgresql.manual_approvals import PostgresManualApprovalGateway
from backend.app.infrastructure.postgresql.model_adapters import PostgresModelAdapterGateway
from backend.app.infrastructure.postgresql.parser_alerts import PostgresParserAlertGateway
from backend.app.infrastructure.postgresql.performance_credentials import (
    PostgresPerformanceCredentialGateway,
)
from backend.app.infrastructure.postgresql.postings import PostgresPostingGateway
from backend.app.infrastructure.postgresql.product_offers import (
    PostgresProductOfferGateway,
)
from backend.app.infrastructure.postgresql.profit_models import PostgresProfitModelGateway
from backend.app.infrastructure.postgresql.public_snapshots import PostgresPublicSnapshotGateway
from backend.app.infrastructure.postgresql.rag_evaluation import (
    PostgresRagEvaluationGateway,
)
from backend.app.infrastructure.postgresql.rag_model_providers import (
    PostgresRagModelProviderGateway,
)
from backend.app.infrastructure.postgresql.rag_tasks import PostgresRagTaskGateway
from backend.app.infrastructure.postgresql.readback_verifications import (
    PostgresReadbackVerificationGateway,
)
from backend.app.infrastructure.postgresql.readonly_tools import PostgresReadonlyToolGateway
from backend.app.infrastructure.postgresql.sales_analysis import PostgresSalesAnalysisGateway
from backend.app.infrastructure.postgresql.search_attributes import PostgresSearchAttributesGateway
from backend.app.infrastructure.postgresql.selection_decision_books import (
    PostgresSelectionDecisionBookGateway,
)
from backend.app.infrastructure.postgresql.selection_expansions import PostgresExpandResultGateway
from backend.app.infrastructure.postgresql.selection_opportunities import (
    PostgresExploreOpportunityGateway,
)
from backend.app.infrastructure.postgresql.selection_validations import (
    PostgresValidateResultGateway,
)
from backend.app.infrastructure.postgresql.seller_fulfillment_snapshots import (
    PostgresSellerFulfillmentSnapshotGateway,
)
from backend.app.infrastructure.postgresql.seller_operations import (
    PostgresSellerOperationGateway,
)
from backend.app.infrastructure.postgresql.seller_order_snapshots import (
    PostgresSellerOrderSnapshotGateway,
)
from backend.app.infrastructure.postgresql.seller_product_snapshots import (
    PostgresSellerProductSnapshotGateway,
)
from backend.app.infrastructure.postgresql.seller_stock_snapshots import (
    PostgresSellerStockSnapshotGateway,
)
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)
from backend.app.infrastructure.postgresql.smart_search import PostgresSmartSearchGateway
from backend.app.infrastructure.postgresql.stock_positions import (
    PostgresStockPositionGateway,
)
from backend.app.infrastructure.postgresql.store_workspaces import (
    PostgresStoreWorkspaceGateway,
)
from backend.app.infrastructure.postgresql.summary_reports import PostgresSummaryReportGateway
from backend.app.infrastructure.postgresql.sync_jobs import PostgresSyncJobGateway
from backend.app.infrastructure.readiness import InfrastructureReadinessProbe
from backend.app.infrastructure.redis_rag_tasks import RedisRagTaskQueue


class LoginRateLimiter(Protocol):
    """说明 LoginRateLimiter 的职责、状态边界和对外协作关系。"""
    async def retry_after(self, email: str, client_key: str) -> int | None:
        """执行 retry_after 的业务流程并返回该流程的结果。"""

    async def record_failure(self, email: str, client_key: str) -> None:
        """执行 record_failure 的业务流程并返回该流程的结果。"""

    async def clear(self, email: str, client_key: str) -> None:
        """执行 clear 的业务流程并返回该流程的结果。"""


class _LegacySellerCredentialProtector:
    """兼容旧 SellerAccountService 测试端口，实际密文仍由统一保护器生成。"""

    def __init__(self, protector: CredentialProtector) -> None:
        """初始化对象依赖和运行时状态。"""
        self._protector = protector

    @property
    def key_version(self) -> int:
        """执行 key_version 的业务流程并返回该流程的结果。"""
        return self._protector.key_version

    def encrypt(self, api_key: str) -> bytes:
        """执行 encrypt 的业务流程并返回该流程的结果。"""
        return self._protector.protect(api_key)


class _LegacySellerCredentialVerifier:
    """将旧的分离参数校验端口转换为当前凭据对象端口。"""

    def __init__(self, verifier: SellerAccountVerifier) -> None:
        """初始化对象依赖和运行时状态。"""
        self._verifier = verifier

    async def verify(self, *, client_id: str, api_key: str) -> None:
        """执行 verify 的业务流程并返回该流程的结果。"""
        await self._verifier.verify(OzonCredentials(client_id=client_id, api_key=api_key))


class _LegacySellerAccountGateway:
    """将历史卖家账户服务适配到当前工作区聚合，避免重复维护凭据写入逻辑。"""

    def __init__(self, gateway: StoreWorkspaceGateway) -> None:
        """初始化对象依赖和运行时状态。"""
        self._gateway = gateway

    async def create(self, **values: object) -> CreatedSellerAccount:
        """执行 create 的业务流程并返回该流程的结果。"""
        workspace = await self._gateway.create_workspace(
            display_name=str(values["display_name"]),
            client_id=str(values["client_id"]),
            encrypted_api_key=cast(bytes, values["encrypted_api_key"]),
            credential_version=cast(int, values["credential_version"]),
        )
        return CreatedSellerAccount(
            seller_account_id=workspace.id,
            workspace_id=workspace.id,
            display_name=workspace.display_name,
            workspace_name=workspace.display_name,
        )


class ReadinessProbe(Protocol):
    """说明 ReadinessProbe 的职责、状态边界和对外协作关系。"""
    async def check(self) -> None:
        """执行 check 的业务流程并返回该流程的结果。"""


@lru_cache
def get_postgres_sessions() -> PostgresSessionFactory:
    """执行 get_postgres_sessions 的业务流程并返回该流程的结果。"""
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL 未配置")
    sessions = PostgresSessionFactory(str(settings.database_url))
    sessions.open()
    return sessions


def close_postgres_sessions() -> None:
    """仅关闭已经创建的全局连接池，避免关停阶段意外建立新连接。"""
    if get_postgres_sessions.cache_info().currsize > 0:
        get_postgres_sessions().close()
        get_postgres_sessions.cache_clear()


@lru_cache
def get_redis_client() -> Redis:
    """执行 get_redis_client 的业务流程并返回该流程的结果。"""
    settings = get_settings()
    if settings.redis_url is None:
        raise RuntimeError("REDIS_URL 未配置")
    return cast(Redis, Redis.from_url(str(settings.redis_url), decode_responses=True))


async def close_redis_client() -> None:
    """执行 close_redis_client 的业务流程并返回该流程的结果。"""
    if get_redis_client.cache_info().currsize > 0:
        await get_redis_client().aclose()
        get_redis_client.cache_clear()


def get_identity_service(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> IdentityService:
    """执行 get_identity_service 的业务流程并返回该流程的结果。"""
    return IdentityService(PostgresIdentityGateway(sessions))


def get_login_rate_limiter(
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> LoginRateLimiter:
    """执行 get_login_rate_limiter 的业务流程并返回该流程的结果。"""
    settings = get_settings()
    return RedisLoginRateLimiter(
        redis,
        max_attempts=settings.login_max_attempts,
        window_seconds=settings.login_window_seconds,
    )


def get_readiness_probe(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> ReadinessProbe:
    """执行 get_readiness_probe 的业务流程并返回该流程的结果。"""
    return InfrastructureReadinessProbe(sessions, redis)


def get_session_cookie_secure() -> bool:
    """执行 get_session_cookie_secure 的业务流程并返回该流程的结果。"""
    return get_settings().session_cookie_secure


def get_default_organization_id() -> str:
    """返回当前部署绑定的运营组织，避免客户端参与租户选择。"""
    return get_settings().default_organization_id


def get_request_session_token(
    session: str | None = Cookie(default=None, alias="ozonslj_session"),
    authorization: str | None = Header(default=None),
) -> str | None:
    """执行 get_request_session_token 的业务流程并返回该流程的结果。"""
    if session:
        return session
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer" and token:
        return token
    return None


async def get_current_user(
    service: Annotated[IdentityService, Depends(get_identity_service)],
    token: Annotated[str | None, Depends(get_request_session_token)],
) -> AuthenticatedUser:
    """执行 get_current_user 的业务流程并返回该流程的结果。"""
    user = await service.authenticate(token) if token else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "请先登录"},
        )
    return user


def get_tenant_context(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TenantContext:
    """只从已验证会话派生数据库租户上下文，禁止客户端自报组织或用户。"""
    return TenantContext(organization_id=user.organization_id, user_id=user.id)


def require_account_manager(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """卖家账户与凭据只允许组织所有者或管理员管理。"""
    if user.organization_role not in {"owner", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "insufficient_role", "message": "当前角色不能管理卖家账户"},
        )
    return user


def get_product_offer_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ProductOfferGateway:
    """执行 get_product_offer_gateway 的业务流程并返回该流程的结果。"""
    return PostgresProductOfferGateway(sessions, context)


def get_customer_order_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> CustomerOrderGateway:
    """使用认证会话的固定内部边界读取脱敏订单。"""
    return PostgresCustomerOrderGateway(sessions, context)


def get_posting_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> PostingGateway:
    """使用认证会话的固定内部边界读取履约摘要。"""
    return PostgresPostingGateway(sessions, context)


def get_seller_operation_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SellerOperationGateway:
    """使用认证会话的固定内部边界读取脱敏审计。"""
    return PostgresSellerOperationGateway(sessions, context)


def get_keyword_import_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> KeywordImportGateway:
    """执行 get_keyword_import_gateway 的业务流程并返回该流程的结果。"""
    return PostgresKeywordImportGateway(sessions, context)


def get_listing_keyword_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingKeywordGateway:
    """执行 get_listing_keyword_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingKeywordGateway(sessions, context)


def get_listing_layer_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingLayerGateway:
    """执行 get_listing_layer_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingLayerGateway(sessions, context)


def get_listing_title_draft_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingTitleDraftGateway:
    """执行 get_listing_title_draft_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingTitleDraftGateway(sessions, context)


def get_listing_fabe_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingFabeGateway:
    """执行 get_listing_fabe_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingFabeGateway(sessions, context)


def get_listing_risk_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingRiskGateway:
    """执行 get_listing_risk_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingRiskGateway(sessions, context)


def get_listing_version_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingVersionGateway:
    """执行 get_listing_version_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingVersionGateway(sessions, context)


def get_listing_publish_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ListingPublishGateway:
    """执行 get_listing_publish_gateway 的业务流程并返回该流程的结果。"""
    return PostgresListingPublishGateway(sessions, context)


def get_advertising_keyword_diagnosis_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingKeywordDiagnosisGateway:
    """执行 get_advertising_keyword_diagnosis_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingKeywordDiagnosisGateway(sessions, context)


def get_advertising_threshold_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingThresholdGateway:
    """执行 get_advertising_threshold_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingThresholdGateway(sessions, context)


def get_advertising_calendar_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingCalendarGateway:
    """执行 get_advertising_calendar_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingCalendarGateway(sessions, context)


def get_advertising_boundary_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingBoundaryGateway:
    """执行 get_advertising_boundary_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingBoundaryGateway(sessions, context)


def get_model_adapter_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ModelAdapterGateway:
    """执行 get_model_adapter_gateway 的业务流程并返回该流程的结果。"""
    return PostgresModelAdapterGateway(sessions, context)


def get_model_budget_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> PostgresModelBudgetGateway:
    """返回按租户隔离的模型额度 PostgreSQL 网关。"""
    return PostgresModelBudgetGateway(sessions, context)


def get_rag_model_provider_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> PostgresRagModelProviderGateway:
    """返回带组织 RLS 上下文的 RAG 模型供应商配置网关。"""
    return PostgresRagModelProviderGateway(sessions, context)


@lru_cache
def get_model_credential_store() -> ModelCredentialStore:
    """模型凭据只写入部署专用 Secret 卷，目录由环境配置决定。"""
    return ModelCredentialStore(get_settings().rag_provider_credentials_dir)


def get_rag_task_gateway(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> PostgresRagTaskGateway:
    """RAG 任务状态统一从 PostgreSQL 读取，避免 API/Worker 各自持有内存队列。"""
    return PostgresRagTaskGateway(sessions, context)


def get_rag_evaluation_gateway(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> PostgresRagEvaluationGateway:
    """返回按组织隔离的评测案例与运行记录 PostgreSQL 网关。"""
    return PostgresRagEvaluationGateway(sessions, context)


def get_rag_task_queue(
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> RedisRagTaskQueue:
    """返回 RAG Redis Stream 投递器；Redis 只保存可重放的任务触发信号。"""
    return RedisRagTaskQueue(redis)


def get_readonly_tool_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ReadonlyToolGateway:
    """执行 get_readonly_tool_gateway 的业务流程并返回该流程的结果。"""
    return PostgresReadonlyToolGateway(sessions, context)


def get_sales_analysis_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SalesAnalysisGateway:
    """执行 get_sales_analysis_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSalesAnalysisGateway(sessions, context)


def get_inventory_analysis_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> InventoryAnalysisGateway:
    """执行 get_inventory_analysis_gateway 的业务流程并返回该流程的结果。"""
    return PostgresInventoryAnalysisGateway(sessions, context)


def get_advertising_analysis_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingAnalysisGateway:
    """执行 get_advertising_analysis_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingAnalysisGateway(sessions, context)


def get_competitor_selection_analysis_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> CompetitorSelectionAnalysisGateway:
    """执行 get_competitor_selection_analysis_gateway 的业务流程并返回该流程的结果。"""
    return PostgresCompetitorSelectionAnalysisGateway(sessions, context)


def get_summary_report_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SummaryReportGateway:
    """执行 get_summary_report_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSummaryReportGateway(sessions, context)


def get_agent_trigger_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AgentTriggerGateway:
    """执行 get_agent_trigger_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAgentTriggerGateway(sessions, context)


def get_agent_permission_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AgentPermissionGateway:
    """执行 get_agent_permission_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAgentPermissionGateway(sessions, context)


def get_external_notification_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ExternalNotificationGateway:
    """执行 get_external_notification_gateway 的业务流程并返回该流程的结果。"""
    return PostgresExternalNotificationGateway(sessions, context)


def get_diff_preview_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> DiffPreviewGateway:
    """执行 get_diff_preview_gateway 的业务流程并返回该流程的结果。"""
    return PostgresDiffPreviewGateway(sessions, context)


def get_manual_approval_gateway(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> ManualApprovalGateway:
    """执行 get_manual_approval_gateway 的业务流程并返回该流程的结果。"""
    return PostgresManualApprovalGateway(sessions, context)


def get_execution_result_gateway(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> ExecutionResultGateway:
    """执行 get_execution_result_gateway 的业务流程并返回该流程的结果。"""
    return PostgresExecutionResultGateway(sessions, context)


def get_readback_verification_gateway(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> ReadbackVerificationGateway:
    """执行 get_readback_verification_gateway 的业务流程并返回该流程的结果。"""
    return PostgresReadbackVerificationGateway(sessions, context)


def get_audit_event_gateway(
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> AuditEventGateway:
    """执行 get_audit_event_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAuditEventGateway(sessions, context)


def get_data_freshness_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> DataFreshnessGateway:
    """执行 get_data_freshness_gateway 的业务流程并返回该流程的结果。"""
    return PostgresDataFreshnessGateway(sessions, context)


def get_data_provenance_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> DataProvenanceGateway:
    """执行 get_data_provenance_gateway 的业务流程并返回该流程的结果。"""
    return PostgresDataProvenanceGateway(sessions, context)


def get_search_attributes_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SearchAttributesGateway:
    """执行 get_search_attributes_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSearchAttributesGateway(sessions, context)


def get_smart_search_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SmartSearchGateway:
    """执行 get_smart_search_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSmartSearchGateway(sessions, context)


def get_competitor_seed_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> CompetitorSeedGateway:
    """执行 get_competitor_seed_gateway 的业务流程并返回该流程的结果。"""
    return PostgresCompetitorSeedGateway(sessions, context)


def get_competition_analysis_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> CompetitionAnalysisGateway:
    """执行 get_competition_analysis_gateway 的业务流程并返回该流程的结果。"""
    return PostgresCompetitionAnalysisGateway(sessions, context)


def get_cost_sensitivity_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> CostSensitivityGateway:
    """执行 get_cost_sensitivity_gateway 的业务流程并返回该流程的结果。"""
    return PostgresCostSensitivityGateway(sessions, context)


def get_profit_model_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ProfitModelGateway:
    """执行 get_profit_model_gateway 的业务流程并返回该流程的结果。"""
    return PostgresProfitModelGateway(sessions, context)


def get_public_snapshot_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> PublicSnapshotGateway:
    """执行 get_public_snapshot_gateway 的业务流程并返回该流程的结果。"""
    return PostgresPublicSnapshotGateway(sessions, context)


def get_parser_alert_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ParserAlertGateway:
    """执行 get_parser_alert_gateway 的业务流程并返回该流程的结果。"""
    return PostgresParserAlertGateway(sessions, context)


def get_explore_opportunity_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ExploreOpportunityGateway:
    """执行 get_explore_opportunity_gateway 的业务流程并返回该流程的结果。"""
    return PostgresExploreOpportunityGateway(sessions, context)


def get_validate_result_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ValidateResultGateway:
    """执行 get_validate_result_gateway 的业务流程并返回该流程的结果。"""
    return PostgresValidateResultGateway(sessions, context)


def get_selection_decision_book_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SelectionDecisionBookGateway:
    """执行 get_selection_decision_book_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSelectionDecisionBookGateway(sessions, context)


def get_expand_result_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> ExpandResultGateway:
    """执行 get_expand_result_gateway 的业务流程并返回该流程的结果。"""
    return PostgresExpandResultGateway(sessions, context)


def get_quality_finding_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> QualityFindingGateway:
    """返回带组织上下文的质量隔离适配器，禁止通过请求参数切换租户。"""
    return PostgresQualityFindingGateway(sessions, context)


def get_sync_job_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SyncJobGateway:
    """同步任务始终写入 PostgreSQL，Redis 仅承担后续可重建投递。"""
    return PostgresSyncJobGateway(sessions, context)


def get_stock_position_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> StockPositionGateway:
    """使用认证会话派生的内部边界读取库存，客户端不能指定组织。"""
    return PostgresStockPositionGateway(sessions, context)


def get_store_workspace_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> StoreWorkspaceGateway:
    """执行 get_store_workspace_gateway 的业务流程并返回该流程的结果。"""
    return PostgresStoreWorkspaceGateway(
        sessions,
        context,
    )


def get_seller_order_snapshot_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SellerOrderSnapshotGateway:
    """执行 get_seller_order_snapshot_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSellerOrderSnapshotGateway(sessions, context)


def get_seller_stock_snapshot_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SellerStockSnapshotGateway:
    """执行 get_seller_stock_snapshot_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSellerStockSnapshotGateway(sessions, context)


def get_seller_fulfillment_snapshot_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SellerFulfillmentSnapshotGateway:
    """执行 get_seller_fulfillment_snapshot_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSellerFulfillmentSnapshotGateway(sessions, context)


def get_seller_product_snapshot_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> SellerProductSnapshotGateway:
    """执行 get_seller_product_snapshot_gateway 的业务流程并返回该流程的结果。"""
    return PostgresSellerProductSnapshotGateway(sessions, context)


@lru_cache
def get_credential_protector() -> CredentialProtector:
    """执行 get_credential_protector 的业务流程并返回该流程的结果。"""
    settings = get_settings()
    return FernetCredentialProtector(
        settings.ozon_credential_key_file,
        key_version=settings.ozon_credential_key_version,
    )


def get_performance_credential_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
    protector: Annotated[CredentialProtector, Depends(get_credential_protector)],
) -> PerformanceCredentialGateway:
    """提供 Performance API 凭据网关，确保令牌加密边界只存在于后端。"""
    return PostgresPerformanceCredentialGateway(sessions, context, protector)


def get_advertising_campaign_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingCampaignGateway:
    """执行 get_advertising_campaign_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingCampaignGateway(sessions, context)


def get_advertising_report_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingReportGateway:
    """执行 get_advertising_report_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingReportGateway(sessions, context)


def get_advertising_metrics_gateway(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
    sessions: Annotated[PostgresSessionFactory, Depends(get_postgres_sessions)],
) -> AdvertisingMetricsGateway:
    """执行 get_advertising_metrics_gateway 的业务流程并返回该流程的结果。"""
    return PostgresAdvertisingMetricsGateway(sessions, context)


@lru_cache
def get_seller_account_verifier() -> SellerAccountVerifier:
    """执行 get_seller_account_verifier 的业务流程并返回该流程的结果。"""
    settings = get_settings()
    if settings.ozon_mode == "stub":
        return StubSellerAccountVerifier()
    return HttpOzonSellerAccountVerifier(str(settings.ozon_base_url))


def get_seller_account_service(
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    verifier: Annotated[SellerAccountVerifier, Depends(get_seller_account_verifier)],
    protector: Annotated[CredentialProtector, Depends(get_credential_protector)],
) -> SellerAccountService:
    """保留旧 Seller 账户 API 的依赖入口，写入统一工作区聚合。"""
    return SellerAccountService(
        _LegacySellerAccountGateway(gateway),
        _LegacySellerCredentialVerifier(verifier),
        _LegacySellerCredentialProtector(protector),
    )
