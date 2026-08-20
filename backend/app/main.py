"""说明本模块的职责、边界和主要协作对象。"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.app.api.dependencies import (
    close_postgres_sessions,
    close_redis_client,
    get_credential_protector,
    get_seller_account_verifier,
)
from backend.app.api.routes.advertising_analysis import router as advertising_analysis_router
from backend.app.api.routes.advertising_budget import router as advertising_budget_router
from backend.app.api.routes.advertising_calendar import router as advertising_calendar_router
from backend.app.api.routes.advertising_campaigns import router as advertising_campaigns_router
from backend.app.api.routes.advertising_keyword_diagnosis import (
    router as advertising_keyword_diagnosis_router,
)
from backend.app.api.routes.advertising_metrics import router as advertising_metrics_router
from backend.app.api.routes.advertising_readonly import router as advertising_readonly_router
from backend.app.api.routes.advertising_reports import router as advertising_reports_router
from backend.app.api.routes.advertising_thresholds import router as advertising_thresholds_router
from backend.app.api.routes.agent_permissions import router as agent_permissions_router
from backend.app.api.routes.agent_triggers import router as agent_triggers_router
from backend.app.api.routes.audit_events import router as audit_events_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.competition_analysis import router as competition_analysis_router
from backend.app.api.routes.competitor_seeds import router as competitor_seeds_router
from backend.app.api.routes.competitor_selection_analysis import (
    router as competitor_selection_analysis_router,
)
from backend.app.api.routes.cost_sensitivity import router as cost_sensitivity_router
from backend.app.api.routes.customer_orders import router as customer_orders_router
from backend.app.api.routes.data_freshness import router as data_freshness_router
from backend.app.api.routes.data_provenance import router as data_provenance_router
from backend.app.api.routes.data_quality import router as data_quality_router
from backend.app.api.routes.data_quality_findings import router as data_quality_findings_router
from backend.app.api.routes.data_quality_schema import router as data_quality_schema_router
from backend.app.api.routes.data_quality_summary import router as data_quality_summary_router
from backend.app.api.routes.data_sources import router as data_sources_router
from backend.app.api.routes.diff_previews import router as diff_previews_router
from backend.app.api.routes.erp_imports import router as erp_imports_router
from backend.app.api.routes.execution_results import router as execution_results_router
from backend.app.api.routes.external_notifications import router as external_notifications_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.inventory_analysis import router as inventory_analysis_router
from backend.app.api.routes.keyword_imports import router as keyword_imports_router
from backend.app.api.routes.knowledge_answers import router as knowledge_answers_router
from backend.app.api.routes.knowledge_chunk_previews import (
    router as knowledge_chunk_previews_router,
)
from backend.app.api.routes.knowledge_indexes import router as knowledge_indexes_router
from backend.app.api.routes.knowledge_ingestion import router as knowledge_ingestion_router
from backend.app.api.routes.knowledge_sources import router as knowledge_sources_router
from backend.app.api.routes.knowledge_strategies import router as knowledge_strategies_router
from backend.app.api.routes.knowledge_tasks import router as knowledge_tasks_router
from backend.app.api.routes.listing_fabe import router as listing_fabe_router
from backend.app.api.routes.listing_keywords import router as listing_keywords_router
from backend.app.api.routes.listing_layering import router as listing_layering_router
from backend.app.api.routes.listing_publish import router as listing_publish_router
from backend.app.api.routes.listing_risks import router as listing_risks_router
from backend.app.api.routes.listing_title_drafts import router as listing_title_drafts_router
from backend.app.api.routes.listing_versions import router as listing_versions_router
from backend.app.api.routes.managed_model_providers import router as managed_model_providers_router
from backend.app.api.routes.manual_approvals import router as manual_approvals_router
from backend.app.api.routes.metrics import router as metrics_router
from backend.app.api.routes.model_adapters import router as model_adapters_router
from backend.app.api.routes.model_budgets import router as model_budgets_router
from backend.app.api.routes.model_providers import router as model_providers_router
from backend.app.api.routes.money_inventory_quality import router as money_inventory_quality_router
from backend.app.api.routes.parser_alerts import router as parser_alerts_router
from backend.app.api.routes.pdf_uploads import router as pdf_uploads_router
from backend.app.api.routes.performance_credentials import router as performance_credentials_router
from backend.app.api.routes.performance_oauth import router as performance_oauth_router
from backend.app.api.routes.postings import router as postings_router
from backend.app.api.routes.price_batch import router as price_batch_router
from backend.app.api.routes.product_offers import router as product_offers_router
from backend.app.api.routes.profit_model import router as profit_model_router
from backend.app.api.routes.public_sampling import router as public_sampling_router
from backend.app.api.routes.public_snapshots import router as public_snapshots_router
from backend.app.api.routes.quality_isolation import router as quality_isolation_router
from backend.app.api.routes.rag_evaluation import router as rag_evaluation_router
from backend.app.api.routes.rag_rollout import router as rag_rollout_router
from backend.app.api.routes.readback_verification import router as readback_verification_router
from backend.app.api.routes.readonly_tools import router as readonly_tools_router
from backend.app.api.routes.relationship_quality import router as relationship_quality_router
from backend.app.api.routes.sales_analysis import router as sales_analysis_router
from backend.app.api.routes.sample_scope import router as sample_scope_router
from backend.app.api.routes.sampling_policy import router as sampling_policy_router
from backend.app.api.routes.search_attributes import router as search_attributes_router
from backend.app.api.routes.selection_decision_books import (
    router as selection_decision_books_router,
)
from backend.app.api.routes.selection_expand import router as selection_expand_router
from backend.app.api.routes.selection_explore import router as selection_explore_router
from backend.app.api.routes.selection_validate import router as selection_validate_router
from backend.app.api.routes.seller_accounts import router as seller_accounts_router
from backend.app.api.routes.seller_fulfillment_sync import router as seller_fulfillment_sync_router
from backend.app.api.routes.seller_operations import router as seller_operations_router
from backend.app.api.routes.seller_order_sync import router as seller_order_sync_router
from backend.app.api.routes.seller_product_sync import router as seller_product_sync_router
from backend.app.api.routes.seller_stock_sync import router as seller_stock_sync_router
from backend.app.api.routes.smart_search import router as smart_search_router
from backend.app.api.routes.source_conflicts import router as source_conflicts_router
from backend.app.api.routes.stock_positions import router as stock_positions_router
from backend.app.api.routes.store_workspaces import router as store_workspaces_router
from backend.app.api.routes.summary_reports import router as summary_reports_router
from backend.app.api.routes.sync_jobs import router as sync_jobs_router
from backend.app.api.routes.sync_processor import router as sync_processor_router
from backend.app.domain.knowledge_runtime import close_knowledge_runtime
from backend.app.domain.store_workspace import CredentialProtector, SellerAccountVerifier
from backend.app.infrastructure.observability import METRICS


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """记录方法、受控路径、状态和耗时，不记录查询参数、请求体、Cookie 或响应正文。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """执行 dispatch 的业务流程并返回该流程的结果。

Args:
    request: 参数语义、输入边界和安全约束。
    call_next: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            METRICS.inc(
                "ozonslj_http_requests_total",
                labels={
                    "method": request.method,
                    "route": _route_label(request.url.path),
                    "status": "500",
                },
            )
            raise
        route = _route_label(request.url.path)
        status_code = str(response.status_code)
        METRICS.inc(
            "ozonslj_http_requests_total",
            labels={"method": request.method, "route": route, "status": status_code},
        )
        METRICS.observe(
            "ozonslj_http_request_duration_seconds",
            time.perf_counter() - started,
            labels={"method": request.method, "route": route},
        )
        return response


def _route_label(path: str) -> str:
    """将动态路径归并为固定标签，防止标签基数和敏感信息进入指标。

Args:
    path: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    if path == "/metrics":
        return "/metrics"
    if path.startswith("/health/"):
        return "/health/*"
    if path.startswith("/v1/"):
        return "/v1/*"
    return "/other"


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用退出时释放已打开的 PostgreSQL 连接池。

Args:
    _: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    yield
    await close_knowledge_runtime()
    close_postgres_sessions()
    await close_redis_client()


def create_app(
    *,
    credential_protector: CredentialProtector | None = None,
    seller_account_verifier: SellerAccountVerifier | None = None,
) -> FastAPI:
    """执行 create_app 的业务流程并返回该流程的结果。

Args:
    credential_protector: 参数语义、输入边界和安全约束。
    seller_account_verifier: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    app = FastAPI(
        title="Ozon Seller Operations API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        # 登录会话在安全 Cookie 中传递；允许凭据时仍只开放本地开发源。
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=[
            "Content-Type",
            "X-Request-Id",
        ],
    )
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(external_notifications_router)
    app.include_router(erp_imports_router)
    app.include_router(auth_router)
    app.include_router(seller_accounts_router)
    app.include_router(customer_orders_router)
    app.include_router(competitor_seeds_router)
    app.include_router(competitor_selection_analysis_router)
    app.include_router(data_quality_router)
    app.include_router(data_quality_findings_router)
    app.include_router(data_sources_router)
    app.include_router(diff_previews_router)
    app.include_router(manual_approvals_router)
    app.include_router(price_batch_router)
    app.include_router(execution_results_router)
    app.include_router(readback_verification_router)
    app.include_router(audit_events_router)
    app.include_router(data_provenance_router)
    app.include_router(relationship_quality_router)
    app.include_router(money_inventory_quality_router)
    app.include_router(source_conflicts_router)
    app.include_router(quality_isolation_router)
    app.include_router(data_freshness_router)
    app.include_router(data_quality_schema_router)
    app.include_router(data_quality_summary_router)
    app.include_router(keyword_imports_router)
    app.include_router(knowledge_answers_router)
    app.include_router(knowledge_sources_router)
    app.include_router(knowledge_chunk_previews_router)
    app.include_router(knowledge_ingestion_router)
    app.include_router(knowledge_strategies_router)
    app.include_router(knowledge_indexes_router)
    app.include_router(knowledge_tasks_router)
    app.include_router(pdf_uploads_router)
    app.include_router(rag_evaluation_router)
    app.include_router(rag_rollout_router)
    app.include_router(model_providers_router)
    app.include_router(managed_model_providers_router)
    app.include_router(model_budgets_router)
    app.include_router(inventory_analysis_router)
    app.include_router(postings_router)
    app.include_router(seller_operations_router)
    app.include_router(seller_product_sync_router)
    app.include_router(seller_order_sync_router)
    app.include_router(seller_fulfillment_sync_router)
    app.include_router(seller_stock_sync_router)
    app.include_router(sync_jobs_router)
    app.include_router(sync_processor_router)
    app.include_router(store_workspaces_router)
    app.include_router(sampling_policy_router)
    app.include_router(public_sampling_router)
    app.include_router(public_snapshots_router)
    app.include_router(sample_scope_router)
    app.include_router(parser_alerts_router)
    app.include_router(selection_explore_router)
    app.include_router(selection_validate_router)
    app.include_router(selection_expand_router)
    app.include_router(selection_decision_books_router)
    app.include_router(competition_analysis_router)
    app.include_router(profit_model_router)
    app.include_router(cost_sensitivity_router)
    app.include_router(listing_keywords_router)
    app.include_router(listing_layering_router)
    app.include_router(listing_title_drafts_router)
    app.include_router(search_attributes_router)
    app.include_router(sales_analysis_router)
    app.include_router(listing_fabe_router)
    app.include_router(smart_search_router)
    app.include_router(listing_risks_router)
    app.include_router(listing_versions_router)
    app.include_router(model_adapters_router)
    app.include_router(listing_publish_router)
    app.include_router(performance_oauth_router)
    app.include_router(performance_credentials_router)
    app.include_router(advertising_campaigns_router)
    app.include_router(advertising_calendar_router)
    app.include_router(advertising_analysis_router)
    app.include_router(advertising_budget_router)
    app.include_router(advertising_reports_router)
    app.include_router(advertising_readonly_router)
    app.include_router(advertising_thresholds_router)
    app.include_router(agent_triggers_router)
    app.include_router(agent_permissions_router)
    app.include_router(advertising_metrics_router)
    app.include_router(advertising_keyword_diagnosis_router)
    app.include_router(product_offers_router)
    app.include_router(readonly_tools_router)
    app.include_router(stock_positions_router)
    app.include_router(summary_reports_router)
    if credential_protector is not None:
        app.dependency_overrides[get_credential_protector] = lambda: credential_protector
    if seller_account_verifier is not None:
        app.dependency_overrides[get_seller_account_verifier] = (
            lambda: seller_account_verifier
        )
    return app


app = create_app()
