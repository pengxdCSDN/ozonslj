import { ArrowClockwise, ArrowRight, CaretDown, ChartLineUp, ChatCircleText, CheckCircle, ClipboardText, Cube, Key, MagnifyingGlass, Package, Plus, ShieldCheck, ShoppingCart, Storefront, Truck, WarningCircle, Warehouse, X } from "@phosphor-icons/react";
import { type FormEvent, useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { cancelSyncJob, createSellerAccount, createStoreWorkspace, createSyncJob, fetchCurrentUser, fetchOperationData, fetchProductOffers, fetchStoreWorkspaces, fetchSyncJob, fetchTaskData, latestOperationSyncAt, login, logout, replaceStoreCredentials, retrySyncJob, type AuthUser, type OperationData, type ProductOffer, type ProductOfferPage, type SellerOperationSummary, type StoreWorkspace, type SyncJob, type SyncResourceType, verifyStoreWorkspace } from "./api";
import { loadSelectedWorkspaceId, saveSelectedWorkspaceId } from "./workspace-storage";
import { checkQuality, commitKeywordImport, previewKeywordImport, previewMappedKeywordImport } from "./api";
import { fetchQualityFindings, fetchQualitySummary, updateQualityFinding } from "./api";
import { createQualityFindings } from "./api";
import { CompetitorSeedsView } from "./CompetitorSeedsView";
import { SamplingPolicyView } from "./SamplingPolicyView";
import { PublicSamplingView } from "./PublicSamplingView";
import { PublicSnapshotView } from "./PublicSnapshotView";
import { SampleScopeView } from "./SampleScopeView";
import { ParserAlertsView } from "./ParserAlertsView";
import { SelectionExploreView } from "./SelectionExploreView";
import { SelectionValidateView } from "./SelectionValidateView";
import { SelectionExpandView } from "./SelectionExpandView";
import { SelectionDecisionBookView } from "./SelectionDecisionBookView";
import { CompetitionAnalysisView } from "./CompetitionAnalysisView";
import { ProfitModelView } from "./ProfitModelView";
import { CostSensitivityView } from "./CostSensitivityView";
import { ListingKeywordsView } from "./ListingKeywordsView";
import { ListingLayeringView } from "./ListingLayeringView";
import { ListingTitleDraftView } from "./ListingTitleDraftView";
import { SearchAttributesView } from "./SearchAttributesView";
import { ListingFabeView } from "./ListingFabeView";
import { SmartSearchView } from "./SmartSearchView";
import { ListingRiskView } from "./ListingRiskView";
import { ListingVersionView } from "./ListingVersionView";
import { ListingPublishView } from "./ListingPublishView";
import { DiffPreviewView } from "./DiffPreviewView";
import { ManualApprovalView } from "./ManualApprovalView";
import { PriceBatchView } from "./PriceBatchView";
import { ExecutionResultsView } from "./ExecutionResultsView";
import { ReadbackVerificationView } from "./ReadbackVerificationView";
import { AuditEventsView } from "./AuditEventsView";
import { DataProvenanceView } from "./DataProvenanceView";
import { RelationshipQualityView } from "./RelationshipQualityView";
import { MoneyInventoryQualityView } from "./MoneyInventoryQualityView";
import { SourceConflictView } from "./SourceConflictView";
import { QualityIsolationView } from "./QualityIsolationView";
import { DataFreshnessView } from "./DataFreshnessView";
import { PerformanceOAuthView } from "./PerformanceOAuthView";
import { AdvertisingCampaignsView } from "./AdvertisingCampaignsView";
import { AdvertisingReportsView } from "./AdvertisingReportsView";
import { AdvertisingMetricsView } from "./AdvertisingMetricsView";
import { AdvertisingKeywordDiagnosisView } from "./AdvertisingKeywordDiagnosisView";
import { AdvertisingThresholdsView } from "./AdvertisingThresholdsView";
import { AdvertisingCalendarView } from "./AdvertisingCalendarView";
import { AdvertisingReadonlyView } from "./AdvertisingReadonlyView";
import { ModelAdapterView } from "./ModelAdapterView";
import { ReadonlyToolsView } from "./ReadonlyToolsView";
import { SalesAnalysisView } from "./SalesAnalysisView";
import { InventoryAnalysisView } from "./InventoryAnalysisView";
import { AdvertisingAnalysisView } from "./AdvertisingAnalysisView";
import { CompetitorSelectionAnalysisView } from "./CompetitorSelectionAnalysisView";
import { SummaryReportView } from "./SummaryReportView";
import { AgentTriggersView } from "./AgentTriggersView";
import { AgentPermissionsView } from "./AgentPermissionsView";
import { ExternalNotificationsView } from "./ExternalNotificationsView";
import { SellerProductSyncView } from "./SellerProductSyncView";
import { SellerStockSyncView } from "./SellerStockSyncView";
import { SellerOrderSyncView } from "./SellerOrderSyncView";
import { SellerFulfillmentSyncView } from "./SellerFulfillmentSyncView";
import { SyncProcessorView } from "./SyncProcessorView";
import { DataSourceLabelsView } from "./DataSourceLabelsView";
import { DataQualitySchemaView } from "./DataQualitySchemaView";
import { DataQualityDashboardView } from "./DataQualityDashboardView";
import { ErpImportView } from "./ErpImportView";
import { KeywordImportView } from "./KeywordImportView";
import { KnowledgeQueryView } from "./KnowledgeQueryView";
import { KnowledgeSourcesView } from "./KnowledgeSourcesView";
import { ModelBudgetView } from "./ModelBudgetView";
import { RagModelProvidersView } from "./RagModelProvidersView";
import { RagEvaluationView } from "./RagEvaluationView";

type LoadState = { status: "idle" | "loading" } | { status: "ready"; data: ProductOfferPage } | { status: "error"; message: string };
type View = "overview" | "products" | "operations" | "tasks" | "quality" | "imports" | "competitors" | "sampling-policy" | "sampling" | "snapshots" | "sample-scope" | "parser-alerts" | "explore" | "validate" | "expand" | "decision-book" | "competition" | "profit" | "sensitivity" | "listing-keywords" | "listing-layering" | "listing-title" | "search-attributes" | "fabe" | "smart-search" | "listing-risk" | "listing-versions" | "listing-publish" | "performance-oauth" | "advertising-campaigns" | "advertising-reports" | "advertising-metrics" | "advertising-keywords" | "advertising-thresholds" | "advertising-calendar" | "advertising-readonly" | "model-adapter" | "model-providers" | "model-budget" | "rag-evaluation" | "readonly-tools" | "sales-analysis" | "inventory-analysis" | "advertising-analysis" | "competitor-selection-analysis" | "summary-report" | "agent-triggers" | "agent-permissions" | "external-notifications" | "performance-credentials" | "seller-product-sync" | "seller-stock-sync" | "seller-order-sync" | "seller-fulfillment-sync" | "sync-processor" | "data-source-labels" | "data-quality-schema" | "erp-import" | "knowledge-query" | "knowledge-sources" | "accounts";
type OperationLoadState = { status: "idle" | "loading" } | { status: "ready"; data: OperationData } | { status: "error"; message: string };
type StockFilter = "all" | "available" | "risk" | "empty";
type CurrentUser = AuthUser;
const LOW_STOCK_THRESHOLD = 15;
/**
 * 这些页面只管理账号级配置、RAG 评测或独立 Performance 数据，不读取 Seller 商品/订单事实。
 * 因此店铺仍处于待验证、无 Seller Key 时也应允许进入；页面内部仍需展示各自的凭据/数据状态。
 */
const SELLER_GATE_EXEMPT_VIEWS = new Set<View>([
  "knowledge-query",
  "knowledge-sources",
  "performance-oauth",
  "advertising-campaigns",
  "advertising-reports",
  "advertising-metrics",
  "advertising-keywords",
  "advertising-thresholds",
  "advertising-calendar",
  "advertising-readonly",
  "advertising-analysis",
  "summary-report",
  "model-adapter",
  "model-providers",
  "model-budget",
  "rag-evaluation",
  "agent-permissions",
  "external-notifications",
]);

function isSellerGateExempt(view: View): boolean {
  return SELLER_GATE_EXEMPT_VIEWS.has(view);
}
function ImportView({ workspaceId }: { workspaceId: string }) { const [content, setContent] = useState("term,volume,rate\n"); const [mapping, setMapping] = useState({ term: "term", volume: "volume", rate: "rate" }); const [preview, setPreview] = useState<import("./api").KeywordImportPreview | null>(null); const [message, setMessage] = useState(""); const previewImport = async () => { try { setPreview(await previewMappedKeywordImport(workspaceId, content, { [mapping.term]: "keyword", [mapping.volume]: "search_count", [mapping.rate]: "conversion_rate" })); setMessage(""); } catch (error) { setMessage(error instanceof Error ? error.message : "导入预览失败"); } }; const commitImport = async () => { if (!preview) return; try { const batch = await commitKeywordImport(workspaceId, preview.fingerprint, preview.rows); setMessage(batch.reused ? "检测到相同文件，已复用既有导入批次" : "导入批次及搜索词事实已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "导入批次保存失败"); } }; return <div className="view-content"><PageHeading label="数据导入 / RES-003" title="搜索词报告字段映射" note="先映射列、预览校验，再提交导入批次；重复文件自动复用" compact /><section className="panel import-panel"><div className="form-grid"><label>关键词列<input value={mapping.term} onChange={(event) => setMapping({ ...mapping, term: event.target.value })} /></label><label>搜索量列<input value={mapping.volume} onChange={(event) => setMapping({ ...mapping, volume: event.target.value })} /></label><label>转化率列<input value={mapping.rate} onChange={(event) => setMapping({ ...mapping, rate: event.target.value })} /></label></div><textarea value={content} onChange={(event) => setContent(event.target.value)} aria-label="CSV 内容" rows={8} /><div className="sync-actions"><button className="secondary-button" onClick={() => void previewImport()}>映射并预览</button><button className="secondary-button" disabled={!preview} onClick={() => void commitImport()}>提交导入</button></div>{message ? <p className="form-message">{message}</p> : null}{preview ? <div className="quality-result"><strong>{preview.total} 行，指纹 {preview.fingerprint.slice(0, 12)}…</strong>{preview.rows.slice(0, 5).map((row) => <div className="operation-row" key={row.source_row}><span><strong>{row.keyword}</strong><small>第 {row.source_row} 行</small></span><em>{row.search_count ?? "无搜索量"}</em></div>)}</div> : null}</section></div>; }
function QualityQueue({ findings, onResolve }: { findings: import("./api").QualityFinding[]; onResolve: (id: string) => void }) { return <section className="panel quality-queue"><div className="list-summary"><span>待处理隔离记录</span><b>{findings.length}</b></div>{findings.length ? findings.map((finding) => <div className="operation-row" key={finding.id ?? `${finding.rule_code}-${finding.field_name}`}><span><strong>{finding.rule_code}</strong><small>{finding.field_name} · {finding.source} · {finding.status}</small></span><em>{finding.message}</em>{finding.id ? <button className="text-button" onClick={() => onResolve(finding.id!)}>标记已处理</button> : null}</div>) : <div className="empty-search"><strong>暂无待处理质量问题</strong><span>异常数据不会覆盖业务事实</span></div>}</section>; }
function QualityView({ state, summary, onCheck }: { state: { status: "idle" | "loading" | "ready" | "error"; result?: import("./api").QualityCheckResult; message?: string }; summary?: import("./api").QualitySummary; onCheck: () => void }) { return <div className="view-content"><PageHeading label="数据质量" title="数据质量中心" note="异常结果只作为质量提示，不静默进入运营分析" compact /><section className="panel"><div className="section-heading"><div><p className="eyebrow">DQ-003 / DQ-004 / DQ-005 / DQ-008</p><h2>问题摘要与样本检查</h2></div><button className="secondary-button" onClick={onCheck} disabled={state.status === "loading"}>{state.status === "loading" ? "检查中…" : "开始检查"}</button></div>{summary ? <div className="metric-grid"><div><small>待处理问题</small><strong>{summary.total}</strong></div><div><small>错误</small><strong>{summary.by_severity.error ?? 0}</strong></div><div><small>警告</small><strong>{summary.by_severity.warning ?? 0}</strong></div></div> : null}{state.status === "error" ? <p className="form-message">{state.message}</p> : null}{state.status === "ready" ? <div className="quality-result"><strong>{state.result?.valid ? "样本通过检查" : `发现 ${state.result?.findings.length ?? 0} 个问题`}</strong>{state.result?.findings.map((finding) => <div className="operation-row" key={`${finding.rule_code}-${finding.field_name}`}><span><strong>{finding.rule_code}</strong><small>{finding.field_name}</small></span><em>{finding.message}</em></div>)}</div> : null}{state.status === "idle" ? <div className="empty-search"><strong>尚未执行检查</strong><span>检查会调用后端质量规则，不修改业务事实</span></div> : null}</section></div>; }
const STATUS_LABELS = { pending: "待验证", active: "已连接", invalid: "凭据无效", disabled: "已停用" } as const;

const NAV_GROUPS: { label: string; icon: React.ReactNode; items: { view: View; label: string }[] }[] = [
  { label: "知识中心", icon: <ChatCircleText size={17} />, items: [{ view: "knowledge-query", label: "知识问答" }, { view: "knowledge-sources", label: "知识源管理" }] },
  { label: "数据准备", icon: <ShieldCheck size={17} />, items: [{ view: "quality", label: "数据质量" }, { view: "imports", label: "搜索词导入" }, { view: "competitors", label: "竞品种子" }, { view: "sampling", label: "公开采样" }] },
  { label: "选品研究", icon: <MagnifyingGlass size={17} />, items: [{ view: "explore", label: "探索选品" }, { view: "validate", label: "选品验证" }, { view: "competition", label: "竞争分析" }, { view: "profit", label: "利润模型" }] },
  { label: "内容增长", icon: <ClipboardText size={17} />, items: [{ view: "listing-keywords", label: "关键词策略" }, { view: "listing-title", label: "标题草稿" }, { view: "listing-risk", label: "内容风险" }, { view: "listing-publish", label: "受控发布" }] },
  { label: "广告分析", icon: <ChartLineUp size={17} />, items: [{ view: "advertising-campaigns", label: "广告活动" }, { view: "advertising-metrics", label: "广告指标" }, { view: "advertising-keywords", label: "关键词诊断" }, { view: "summary-report", label: "汇总报告" }] },
  { label: "系统工具", icon: <Key size={17} />, items: [{ view: "performance-credentials", label: "Performance 凭据" }, { view: "model-providers", label: "模型供应商" }, { view: "model-budget", label: "模型额度" }, { view: "rag-evaluation", label: "RAG 评测确认" }, { view: "seller-product-sync", label: "Seller 数据同步" }, { view: "agent-permissions", label: "Agent 权限" }, { view: "external-notifications", label: "外部通知" }] },
];

const VIEW_LABELS: Partial<Record<View, string>> = {
  overview: "运营总览",
  products: "商品与库存",
  operations: "运营事实",
  tasks: "任务中心",
  ...Object.fromEntries(NAV_GROUPS.flatMap((group) => group.items.map((item) => [item.view, item.label])))
};

function AdvancedNavigation({ view, onNavigate }: { view: View; onNavigate: (next: View) => void }) {
  return <div className="advanced-navigation">{NAV_GROUPS.map((group) => <details key={group.label} open={group.items.some((item) => item.view === view)}><summary>{group.icon}<span>{group.label}</span><CaretDown size={12} /></summary><div>{group.items.map((item) => <button type="button" className={view === item.view ? "active" : ""} onClick={() => onNavigate(item.view)} key={item.view}>{item.label}</button>)}</div></details>)}</div>;
}

function WorkspaceSwitcher({ workspaces, selectedId, onChange, title }: { workspaces: StoreWorkspace[]; selectedId: string; onChange: (id: string) => void; title: string }) {
  const [open, setOpen] = useState(false);
  const selected = workspaces.find((workspace) => workspace.id === selectedId);
  return <div className="workspace-switcher" title={title} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <span className={`online-dot ${selected?.status ?? "pending"}`} />
    <span className="workspace-label">当前店铺</span>
    <button type="button" className="workspace-trigger" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((current) => !current)}><strong>{selected?.display_name ?? "请选择店铺"}</strong><CaretDown size={13} /></button>
    {open ? <div className="workspace-menu" role="listbox" aria-label="切换当前店铺">{workspaces.map((workspace) => <button type="button" role="option" aria-selected={workspace.id === selectedId} onClick={() => { onChange(workspace.id); setOpen(false); }} key={workspace.id}><span className={`online-dot ${workspace.status}`} /><span><strong>{workspace.display_name}</strong><small>{STATUS_LABELS[workspace.status]}</small></span>{workspace.id === selectedId ? <CheckCircle size={15} weight="fill" /> : null}</button>)}</div> : null}
  </div>;
}

function formatPrice(value: string, currency: string) { return new Intl.NumberFormat("zh-CN", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value)); }
function stockState(stock: number) { if (!stock) return { label: "缺货", className: "danger" }; if (stock <= LOW_STOCK_THRESHOLD) return { label: "低库存", className: "warning" }; return { label: "在售", className: "success" }; }
function ProductRow({ offer }: { offer: ProductOffer }) { const status = stockState(offer.available_stock); return <article className="product-row"><div className={`product-visual ${status.className}`}><Package size={20} weight="duotone" /></div><div className="product-identity"><h3>{offer.name}</h3><p>{offer.offer_id}</p></div><div className="product-meta"><strong>{formatPrice(offer.price, offer.currency)}</strong><span className={`status-pill ${status.className}`}>{status.label} · {offer.available_stock}</span></div><button className="row-action" type="button" aria-label={`查看 ${offer.name}`}><ArrowRight size={16} weight="bold" /></button></article>; }

function LoginPanel({ onAuthenticated }: { onAuthenticated: (user: CurrentUser) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand-mark login-mark" aria-hidden>O</div>
        <p className="eyebrow">Ozon 跨境运营</p>
        <h1>登录运营控制台</h1>
        <p className="login-note">使用管理员分配的账号登录。卖家 API 凭据不会保存在浏览器中。</p>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            setSubmitting(true);
            setError(null);
            try {
              onAuthenticated(await login(email, password));
            } catch (loginError) {
              setError(loginError instanceof Error ? loginError.message : "登录失败，请重试");
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <label className="login-field">
            <span>邮箱</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="login-field">
            <span>密码</span>
            <input
              type="password"
              autoComplete="current-password"
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error ? <p className="login-error" role="alert">{error}</p> : null}
          <button className="primary-button login-button" type="submit" disabled={submitting}>
            {submitting ? "正在登录…" : "登录"}
          </button>
        </form>
      </section>
    </main>
  );
}

function AddSellerAccountDialog({
  onClose,
  onCreated
}: {
  onClose: () => void;
  onCreated: (workspaceId: string) => Promise<void>;
}) {
  const [displayName, setDisplayName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [clientId, setClientId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, submitting]);

  return (
    <div className="account-dialog-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !submitting) onClose();
    }}>
      <section className="account-dialog" role="dialog" aria-modal="true" aria-labelledby="account-dialog-title">
        <div className="account-dialog-heading">
          <div>
            <p className="eyebrow">店铺连接</p>
            <h2 id="account-dialog-title">添加 Ozon 卖家账号</h2>
          </div>
          <button type="button" className="dialog-close" onClick={onClose} disabled={submitting} aria-label="关闭">
            <X size={17} weight="bold" />
          </button>
        </div>
        <div className="credential-assurance">
          <ShieldCheck size={20} weight="duotone" aria-hidden />
          <span><strong>凭据由服务器加密保存</strong><small>Api-Key 不会写入浏览器存储或页面日志。</small></span>
        </div>
        <form onSubmit={async (event) => {
          event.preventDefault();
          setSubmitting(true);
          setError(null);
          try {
            const created = await createSellerAccount({
              display_name: displayName,
              workspace_name: workspaceName,
              client_id: clientId,
              api_key: apiKey
            });
            setApiKey("");
            await onCreated(created.workspace_id);
          } catch (creationError) {
            setError(creationError instanceof Error ? creationError.message : "店铺账号创建失败");
          } finally {
            setSubmitting(false);
          }
        }}>
          <div className="account-form-grid">
            <label className="account-field"><span>店铺显示名称</span><input required maxLength={120} value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="例如：俄罗斯主店" /></label>
            <label className="account-field"><span>工作区名称</span><input required maxLength={120} value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} placeholder="例如：主店运营组" /></label>
            <label className="account-field"><span>Client-Id</span><input required maxLength={200} autoComplete="off" value={clientId} onChange={(event) => setClientId(event.target.value)} placeholder="输入 Ozon Client-Id" /></label>
            <label className="account-field"><span>Api-Key</span><input required maxLength={500} type="password" autoComplete="new-password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="输入 Ozon Api-Key" /></label>
          </div>
          {error ? <p className="account-form-error" role="alert">{error}</p> : null}
          <div className="account-dialog-actions">
            <button type="button" className="secondary-button" onClick={onClose} disabled={submitting}>取消</button>
            <button type="submit" className="primary-button" disabled={submitting}>{submitting ? "正在验证…" : "验证并添加"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

export function App() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null), [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [workspaces, setWorkspaces] = useState<StoreWorkspace[]>([]), [selectedWorkspaceId, setSelectedWorkspaceId] = useState(""), [workspaceError, setWorkspaceError] = useState("");
  const [state, setState] = useState<LoadState>({ status: "idle" }), [view, setView] = useState<View>("overview"), [query, setQuery] = useState(""), [stockFilter, setStockFilter] = useState<StockFilter>("all");
  const [operationState, setOperationState] = useState<OperationLoadState>({ status: "idle" });
  const [taskState, setTaskState] = useState<{ status: "idle" | "loading" | "ready" | "error"; operations: SellerOperationSummary[]; jobs: SyncJob[]; message?: string }>({ status: "idle", operations: [], jobs: [] });
  const [currentJob, setCurrentJob] = useState<SyncJob | null>(null), [syncBusy, setSyncBusy] = useState<SyncResourceType | "">("");
  const [taskActionBusy, setTaskActionBusy] = useState("");
  const [qualityState, setQualityState] = useState<{ status: "idle" | "loading" | "ready" | "error"; result?: import("./api").QualityCheckResult; message?: string }>({ status: "idle" });
  const [qualitySummary, setQualitySummary] = useState<import("./api").QualitySummary>();
  const [qualityFindings, setQualityFindings] = useState<import("./api").QualityFinding[]>([]);
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null), [formBusy, setFormBusy] = useState(false), [verifyBusyId, setVerifyBusyId] = useState(""), [formMessage, setFormMessage] = useState("");
  const deferredQuery = useDeferredValue(query), selectedWorkspace = workspaces.find(({ id }) => id === selectedWorkspaceId);
  useEffect(() => { const controller = new AbortController(); void fetchCurrentUser(controller.signal).then(setAuthUser).catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setAuthUser(null); }).finally(() => setAuthLoading(false)); return () => controller.abort(); }, []);
  const refreshWorkspaces = useCallback(async (signal?: AbortSignal) => { try { const [items, storedId] = await Promise.all([fetchStoreWorkspaces(signal), loadSelectedWorkspaceId()]); setWorkspaces(items); setWorkspaceError(""); setSelectedWorkspaceId((current) => { const preferred = current || storedId || ""; return items.some(({ id }) => id === preferred) ? preferred : (items[0]?.id ?? ""); }); } catch (error) { if (error instanceof DOMException && error.name === "AbortError") return; setWorkspaceError(error instanceof Error ? error.message : "无法加载工作区"); } }, []);
  useEffect(() => { if (!authUser) return; const controller = new AbortController(); void refreshWorkspaces(controller.signal); return () => controller.abort(); }, [authUser, refreshWorkspaces]);
  useEffect(() => { if (!selectedWorkspaceId) return; void saveSelectedWorkspaceId(selectedWorkspaceId); const controller = new AbortController(); if (selectedWorkspace?.status !== "active") { setState({ status: "idle" }); return () => controller.abort(); } setState({ status: "loading" }); void fetchProductOffers(selectedWorkspaceId, controller.signal).then((data) => { setState({ status: "ready", data }); setLastSyncedAt(new Date()); }).catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setState({ status: "error", message: error instanceof Error ? error.message : "无法加载商品数据" }); }); return () => controller.abort(); }, [selectedWorkspace?.status, selectedWorkspaceId]);
  useEffect(() => { if (view !== "operations" || !selectedWorkspaceId || selectedWorkspace?.status !== "active") return; const controller = new AbortController(); setOperationState({ status: "loading" }); void fetchOperationData(selectedWorkspaceId, controller.signal).then((data) => setOperationState({ status: "ready", data })).catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setOperationState({ status: "error", message: error instanceof Error ? error.message : "无法加载运营数据" }); }); return () => controller.abort(); }, [selectedWorkspace?.status, selectedWorkspaceId, view]);
  useEffect(() => { if (view !== "tasks" || !selectedWorkspaceId || selectedWorkspace?.status !== "active") return; const controller = new AbortController(); setTaskState({ status: "loading", operations: [], jobs: [] }); void fetchTaskData(selectedWorkspaceId, controller.signal).then((data) => { setTaskState({ status: "ready", operations: data.operations, jobs: data.jobs }); setCurrentJob((current) => current ?? data.jobs[0] ?? null); }).catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setTaskState({ status: "error", operations: [], jobs: [], message: error instanceof Error ? error.message : "无法加载任务与审计" }); }); return () => controller.abort(); }, [selectedWorkspace?.status, selectedWorkspaceId, view]);
  useEffect(() => { if (view !== "quality" || !selectedWorkspaceId || selectedWorkspace?.status !== "active") return; const controller = new AbortController(); void fetchQualityFindings(selectedWorkspaceId, "open").then(setQualityFindings).catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setQualityState({ status: "error", message: error instanceof Error ? error.message : "无法加载质量隔离记录" }); }); return () => controller.abort(); }, [selectedWorkspace?.status, selectedWorkspaceId, view]);
  useEffect(() => { if (view !== "quality" || !selectedWorkspaceId || selectedWorkspace?.status !== "active") return; void fetchQualitySummary(selectedWorkspaceId).then(setQualitySummary).catch(() => setQualitySummary(undefined)); }, [selectedWorkspace?.status, selectedWorkspaceId, view]);
  useEffect(() => { if (!currentJob || !selectedWorkspaceId || !["queued", "running"].includes(currentJob.status)) return; const controller = new AbortController(); const timer = window.setTimeout(() => { void fetchSyncJob(currentJob.id, controller.signal).then((job) => { setCurrentJob(job); if (["succeeded", "partial", "failed", "cancelled"].includes(job.status)) { void fetchTaskData(selectedWorkspaceId, controller.signal).then((data) => setTaskState({ status: "ready", operations: data.operations, jobs: data.jobs })); } }).catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setTaskState((current) => ({ ...current, status: "error", message: error instanceof Error ? error.message : "无法刷新同步任务" })); }); }, 2_000); return () => { window.clearTimeout(timer); controller.abort(); }; }, [currentJob, selectedWorkspaceId]);
  const loadOffers = useCallback(async () => { if (!selectedWorkspaceId || selectedWorkspace?.status !== "active") return; setState({ status: "loading" }); try { const data = await fetchProductOffers(selectedWorkspaceId); setState({ status: "ready", data }); setLastSyncedAt(new Date()); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "无法加载商品数据" }); } }, [selectedWorkspace?.status, selectedWorkspaceId]);
  const changeWorkspace = (id: string) => { setSelectedWorkspaceId(id); setQuery(""); setStockFilter("all"); setCurrentJob(null); setOperationState({ status: "idle" }); setTaskState({ status: "idle", operations: [], jobs: [] }); setTaskActionBusy(""); };
  const handleCredentialSubmit = async (event: FormEvent<HTMLFormElement>, mode: "create" | "replace") => { event.preventDefault(); const form = event.currentTarget, data = new FormData(form), clientId = String(data.get("client_id") ?? "").trim(), apiKey = String(data.get("api_key") ?? "").trim(), displayName = String(data.get("display_name") ?? "").trim(); if (!clientId || !apiKey || (mode === "create" && !displayName)) { setFormMessage("请完整填写店铺名称、Client ID 和 Api-Key。"); return; } setFormBusy(true); setFormMessage(""); try { const workspace = mode === "create" ? await createStoreWorkspace({ display_name: displayName, client_id: clientId, api_key: apiKey }) : await replaceStoreCredentials(selectedWorkspaceId, { client_id: clientId, api_key: apiKey }); form.reset(); await refreshWorkspaces(); changeWorkspace(workspace.id); setFormMessage(mode === "create" ? "工作区已创建，请继续验证凭据。" : "凭据已更换，请重新验证。"); } catch (error) { setFormMessage(error instanceof Error ? error.message : "保存凭据失败"); } finally { setFormBusy(false); } };
  const handleVerify = async (id: string) => { setVerifyBusyId(id); setFormMessage(""); try { await verifyStoreWorkspace(id); await refreshWorkspaces(); changeWorkspace(id); setFormMessage("验证成功，店铺数据已连接。"); } catch (error) { await refreshWorkspaces(); setFormMessage(error instanceof Error ? error.message : "验证失败，请稍后重试"); } finally { setVerifyBusyId(""); } };
  const handleSync = async (resourceType: SyncResourceType) => { if (!selectedWorkspaceId || !active) return; setSyncBusy(resourceType); try { setCurrentJob(await createSyncJob(selectedWorkspaceId, resourceType)); } catch (error) { setTaskState((current) => ({ ...current, status: "error", message: error instanceof Error ? error.message : "无法创建同步任务" })); } finally { setSyncBusy(""); } };
  const handleQualityCheck = async () => { const sample = offers[0]; if (!sample || !selectedWorkspaceId) return; setQualityState({ status: "loading" }); try { const result = await checkQuality({ offer_id: sample.offer_id, status: "active", price: sample.price, available_stock: sample.available_stock }); setQualityState({ status: "ready", result }); if (result.findings.length) await createQualityFindings(selectedWorkspaceId, result.findings); setQualityFindings(await fetchQualityFindings(selectedWorkspaceId, "open")); } catch (error) { setQualityState({ status: "error", message: error instanceof Error ? error.message : "质量检查失败" }); } };
  const handleResolveQualityFinding = async (findingId: string) => { if (!selectedWorkspaceId) return; try { await updateQualityFinding(findingId, selectedWorkspaceId, "resolved"); setQualityFindings(await fetchQualityFindings(selectedWorkspaceId, "open")); } catch (error) { setQualityState({ status: "error", message: error instanceof Error ? error.message : "更新质量记录失败" }); } };
  const handleTaskAction = async (jobId: string, action: "cancel" | "retry") => { setTaskActionBusy(jobId); try { const job = action === "cancel" ? await cancelSyncJob(jobId) : await retrySyncJob(jobId); setCurrentJob(job); const data = await fetchTaskData(selectedWorkspaceId); setTaskState({ status: "ready", operations: data.operations, jobs: data.jobs }); } catch (error) { setTaskState((current) => ({ ...current, status: "error", message: error instanceof Error ? error.message : "任务操作失败" })); } finally { setTaskActionBusy(""); } };
  const offers = state.status === "ready" ? state.data.items : [];
  const operationFreshness = operationState.status === "ready" ? latestOperationSyncAt(operationState.data) : null;
  const metrics = useMemo(() => offers.reduce((sum, offer) => { sum.stock += offer.available_stock; sum.value += Number(offer.price) * offer.available_stock; if (!offer.available_stock) sum.empty++; else if (offer.available_stock <= LOW_STOCK_THRESHOLD) sum.risk++; return sum; }, { stock: 0, risk: 0, empty: 0, value: 0 }), [offers]);
  const filteredOffers = useMemo(() => { const needle = deferredQuery.trim().toLocaleLowerCase(); return offers.filter((offer) => (!needle || offer.name.toLocaleLowerCase().includes(needle) || offer.offer_id.toLocaleLowerCase().includes(needle)) && (stockFilter === "all" || (stockFilter === "available" && offer.available_stock > LOW_STOCK_THRESHOLD) || (stockFilter === "risk" && offer.available_stock > 0 && offer.available_stock <= LOW_STOCK_THRESHOLD) || (stockFilter === "empty" && !offer.available_stock))); }, [deferredQuery, offers, stockFilter]);
  const active = selectedWorkspace?.status === "active";
  const pageAccessible = Boolean(active) || isSellerGateExempt(view);
  const currentViewLabel = VIEW_LABELS[view] ?? "当前功能";
  if (authLoading) return <div className="auth-state">正在恢复登录状态…</div>;
  if (!authUser) return <LoginView busy={authLoading} error={authError} onLogin={async (email, password) => { setAuthLoading(true); setAuthError(""); try { setAuthUser(await login(email, password)); } catch (error) { setAuthError(error instanceof Error ? error.message : "登录失败"); } finally { setAuthLoading(false); } }} />;
  return <main className="app-shell">
    <header className="masthead"><div className="brand"><div className="brand-mark"><Cube size={19} weight="fill" /></div><div><strong>Ozon SLJ</strong><span>SELLER OPERATIONS</span></div></div><div className="header-actions"><span className="user-name">{authUser.display_name}</span><button className="icon-button" onClick={() => void loadOffers()} aria-label="同步数据"><ArrowClockwise size={17} /></button><button className="icon-button" onClick={() => void logout().then(() => setAuthUser(null))} aria-label="退出登录">退出</button></div></header>
    <WorkspaceSwitcher workspaces={workspaces} selectedId={selectedWorkspaceId} onChange={changeWorkspace} title={operationFreshness ? `最近同步：${new Date(operationFreshness).toLocaleString("zh-CN")}` : "暂无同步时间"} />
    <nav className="view-tabs" aria-label="工作台导航"><p className="nav-section-label">运营中心</p><button className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}><ChartLineUp size={17} />总览</button><button className={view === "products" ? "active" : ""} onClick={() => setView("products")}><Package size={17} />商品{metrics.empty ? <span>{metrics.empty}</span> : null}</button><button className={view === "operations" ? "active" : ""} onClick={() => setView("operations")}><Truck size={17} />运营</button><button className={view === "tasks" ? "active" : ""} onClick={() => setView("tasks")}><ClipboardText size={17} />任务</button><button className={view === "accounts" ? "active" : ""} onClick={() => setView("accounts")}><Storefront size={17} />店铺</button><AdvancedNavigation view={view} onNavigate={setView} /></nav>
    {false && <><button className="text-button quality-shortcut" onClick={() => setView("quality")} type="button"><ShieldCheck size={14} /> 数据质量</button>
    <button className="text-button quality-shortcut" onClick={() => setView("imports")} type="button"><ClipboardText size={14} /> 搜索词导入</button>
    <button className="text-button quality-shortcut" onClick={() => setView("competitors")} type="button"><MagnifyingGlass size={14} /> 竞品种子</button>
    <button className="text-button quality-shortcut" onClick={() => setView("sampling-policy")} type="button"><ShieldCheck size={14} /> 合规检查</button>
    <button className="text-button quality-shortcut" onClick={() => setView("sampling")} type="button"><MagnifyingGlass size={14} /> 采样预览</button>
    <button className="text-button quality-shortcut" onClick={() => setView("snapshots")} type="button"><ClipboardText size={14} /> 快照规范化</button>
    <button className="text-button quality-shortcut" onClick={() => setView("sample-scope")} type="button"><ShieldCheck size={14} /> 样本范围</button>
    <button className="text-button quality-shortcut" onClick={() => setView("parser-alerts")} type="button"><WarningCircle size={14} /> 解析告警</button>
    <button className="text-button quality-shortcut" onClick={() => setView("explore")} type="button"><ChartLineUp size={14} /> Explore 选品</button>
    <button className="text-button quality-shortcut" onClick={() => setView("validate")} type="button"><ChartLineUp size={14} /> Validate 验证</button>
    <button className="text-button quality-shortcut" onClick={() => setView("expand")} type="button"><ChartLineUp size={14} /> Expand 扩展</button>
    <button className="text-button quality-shortcut" onClick={() => setView("competition")} type="button"><ChartLineUp size={14} /> 竞争度</button>
    <button className="text-button quality-shortcut" onClick={() => setView("profit")} type="button"><ChartLineUp size={14} /> 利润模型</button>
    <button className="text-button quality-shortcut" onClick={() => setView("sensitivity")} type="button"><ChartLineUp size={14} /> 成本敏感性</button>
    <button className="text-button quality-shortcut" onClick={() => setView("listing-keywords")} type="button"><ClipboardText size={14} /> Listing 关键词</button>
    <button className="text-button quality-shortcut" onClick={() => setView("listing-layering")} type="button"><ClipboardText size={14} /> 关键词分层</button>
    <button className="text-button quality-shortcut" onClick={() => setView("listing-title")} type="button"><ClipboardText size={14} /> 标题草稿</button>
    <button className="text-button quality-shortcut" onClick={() => setView("search-attributes")} type="button"><ClipboardText size={14} /> Search Attributes</button>
    <button className="text-button quality-shortcut" onClick={() => setView("fabe")} type="button"><ClipboardText size={14} /> FABE 草稿</button>
    <button className="text-button quality-shortcut" onClick={() => setView("smart-search")} type="button"><ShieldCheck size={14} /> Smart Search</button>
    <button className="text-button quality-shortcut" onClick={() => setView("listing-risk")} type="button"><WarningCircle size={14} /> 内容风险</button>
    <button className="text-button quality-shortcut" onClick={() => setView("listing-versions")} type="button"><ClipboardText size={14} /> 版本管理</button>
    <button className="text-button quality-shortcut" onClick={() => setView("listing-publish")} type="button"><ShieldCheck size={14} /> 受控发布</button>
    <button className="text-button quality-shortcut" onClick={() => setView("performance-oauth")} type="button"><ShieldCheck size={14} /> Performance OAuth</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-campaigns")} type="button"><ChartLineUp size={14} /> 广告活动</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-reports")} type="button"><ChartLineUp size={14} /> 广告报表</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-metrics")} type="button"><ChartLineUp size={14} /> 广告指标</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-keywords")} type="button"><ChartLineUp size={14} /> 关键词诊断</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-thresholds")} type="button"><ChartLineUp size={14} /> 阈值配置</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-calendar")} type="button"><ChartLineUp size={14} /> 30 天日历</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-readonly")} type="button"><ShieldCheck size={14} /> 只读边界</button>
    <button className="text-button quality-shortcut" onClick={() => setView("model-adapter")} type="button"><ShieldCheck size={14} /> 模型适配器</button>
    <button className="text-button quality-shortcut" onClick={() => setView("readonly-tools")} type="button"><ShieldCheck size={14} /> 只读工具</button>
    <button className="text-button quality-shortcut" onClick={() => setView("sales-analysis")} type="button"><ChartLineUp size={14} /> 销售分析</button>
    <button className="text-button quality-shortcut" onClick={() => setView("inventory-analysis")} type="button"><Warehouse size={14} /> 库存分析</button>
    <button className="text-button quality-shortcut" onClick={() => setView("advertising-analysis")} type="button"><ChartLineUp size={14} /> 广告分析</button>
    <button className="text-button quality-shortcut" onClick={() => setView("competitor-selection-analysis")} type="button"><MagnifyingGlass size={14} /> 竞品选品分析</button>
    <button className="text-button quality-shortcut" onClick={() => setView("summary-report")} type="button"><ClipboardText size={14} /> 汇总报告</button>
    <button className="text-button quality-shortcut" onClick={() => setView("agent-triggers")} type="button"><ShieldCheck size={14} /> 触发器</button>
    <button className="text-button quality-shortcut" onClick={() => setView("agent-permissions")} type="button"><ShieldCheck size={14} /> Agent 权限</button>
    <button className="text-button quality-shortcut" onClick={() => setView("external-notifications")} type="button"><ShieldCheck size={14} /> 外部通知</button>
    <button className="text-button quality-shortcut" onClick={() => setView("performance-credentials")} type="button"><Key size={14} /> Performance 凭据</button>
    <button className="text-button quality-shortcut" onClick={() => setView("seller-product-sync")} type="button"><Package size={14} /> Seller 商品同步</button>
    <button className="text-button quality-shortcut" onClick={() => setView("seller-stock-sync")} type="button"><Warehouse size={14} /> Seller 库存同步</button>
    <button className="text-button quality-shortcut" onClick={() => setView("seller-order-sync")} type="button"><ShoppingCart size={14} /> Seller 订单同步</button>
    <button className="text-button quality-shortcut" onClick={() => setView("seller-fulfillment-sync")} type="button"><Truck size={14} /> Seller 履约同步</button>
    <button className="text-button quality-shortcut" onClick={() => setView("sync-processor")} type="button"><ClipboardText size={14} /> 同步处理器</button>
    <button className="text-button quality-shortcut" onClick={() => setView("data-source-labels")} type="button"><ShieldCheck size={14} /> 来源标签</button>
    <button className="text-button quality-shortcut" onClick={() => setView("data-quality-schema")} type="button"><ShieldCheck size={14} /> Schema 质量</button>
    <button className="text-button quality-shortcut" onClick={() => setView("erp-import")} type="button"><ClipboardText size={14} /> ERP 补充数据</button></>}
    {view === "quality" && active ? <DataQualityDashboardView workspaceId={selectedWorkspaceId} /> : null}
    {view === "knowledge-query" ? <KnowledgeQueryView /> : null}
    {view === "knowledge-sources" ? <KnowledgeSourcesView /> : null}
    {/* RAG 供应商配置是账号级能力，不依赖当前 Ozon 店铺是否已验证。 */}
    {view === "model-providers" ? <RagModelProvidersView /> : null}
    {/* 模型额度按供应商账号统计，不依赖当前店铺状态。 */}
    {view === "model-budget" ? <ModelBudgetView /> : null}
    {view === "rag-evaluation" ? <RagEvaluationView /> : null}
    {view === "imports" && active && selectedWorkspaceId ? <KeywordImportView workspaceId={selectedWorkspaceId} /> : null}
    {view === "competitors" && active && selectedWorkspaceId ? <CompetitorSeedsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "sampling-policy" && active ? <SamplingPolicyView workspaceId={selectedWorkspaceId} /> : null}
    {view === "sampling" && active ? <PublicSamplingView workspaceId={selectedWorkspaceId} /> : null}
    {view === "snapshots" && active ? <PublicSnapshotView workspaceId={selectedWorkspaceId} /> : null}
    {view === "sample-scope" && active ? <SampleScopeView workspaceId={selectedWorkspaceId} /> : null}
    {view === "parser-alerts" && active ? <ParserAlertsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "explore" && active ? <SelectionExploreView workspaceId={selectedWorkspaceId} /> : null}
    {view === "validate" && active ? <SelectionValidateView workspaceId={selectedWorkspaceId} /> : null}
    {view === "expand" && active ? <SelectionExpandView workspaceId={selectedWorkspaceId} /> : null}
    {view === "decision-book" && active ? <SelectionDecisionBookView workspaceId={selectedWorkspaceId} /> : null}
    {view === "competition" && active ? <CompetitionAnalysisView workspaceId={selectedWorkspaceId} /> : null}
    {view === "profit" && active ? <ProfitModelView workspaceId={selectedWorkspaceId} /> : null}
    {view === "sensitivity" && active ? <CostSensitivityView workspaceId={selectedWorkspaceId} /> : null}
    {view === "listing-keywords" && active ? <ListingKeywordsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "listing-layering" && active ? <ListingLayeringView workspaceId={selectedWorkspaceId} /> : null}
    {view === "listing-title" && active ? <ListingTitleDraftView workspaceId={selectedWorkspaceId} /> : null}
    {view === "search-attributes" && active ? <SearchAttributesView workspaceId={selectedWorkspaceId} /> : null}
    {view === "fabe" && active ? <ListingFabeView workspaceId={selectedWorkspaceId} /> : null}
    {view === "smart-search" && active ? <SmartSearchView workspaceId={selectedWorkspaceId} /> : null}
    {view === "listing-risk" && active ? <ListingRiskView workspaceId={selectedWorkspaceId} /> : null}
    {view === "listing-versions" && active ? <ListingVersionView workspaceId={selectedWorkspaceId} /> : null}
    {view === "listing-publish" && active ? <><ListingPublishView workspaceId={selectedWorkspaceId} /><DiffPreviewView workspaceId={selectedWorkspaceId} /><DataFreshnessView workspaceId={selectedWorkspaceId} /><DataProvenanceView workspaceId={selectedWorkspaceId} /><RelationshipQualityView workspaceId={selectedWorkspaceId} /><MoneyInventoryQualityView workspaceId={selectedWorkspaceId} /><SourceConflictView workspaceId={selectedWorkspaceId} /><QualityIsolationView workspaceId={selectedWorkspaceId} /><PriceBatchView /><ExecutionResultsView workspaceId={selectedWorkspaceId} /><ReadbackVerificationView workspaceId={selectedWorkspaceId} /><AuditEventsView workspaceId={selectedWorkspaceId} /><ManualApprovalView workspaceId={selectedWorkspaceId} /></> : null}
    {view === "performance-oauth" && pageAccessible ? <PerformanceOAuthView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-campaigns" && pageAccessible ? <AdvertisingCampaignsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-reports" && pageAccessible ? <AdvertisingReportsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-metrics" && pageAccessible ? <AdvertisingMetricsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-keywords" && pageAccessible ? <AdvertisingKeywordDiagnosisView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-thresholds" && pageAccessible ? <AdvertisingThresholdsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-calendar" && pageAccessible ? <AdvertisingCalendarView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-readonly" && pageAccessible ? <AdvertisingReadonlyView workspaceId={selectedWorkspaceId} /> : null}
    {view === "model-adapter" && pageAccessible ? <ModelAdapterView workspaceId={selectedWorkspaceId} /> : null}
    {view === "readonly-tools" && active ? <ReadonlyToolsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "sales-analysis" && active ? <SalesAnalysisView workspaceId={selectedWorkspaceId} /> : null}
    {view === "inventory-analysis" && active ? <InventoryAnalysisView workspaceId={selectedWorkspaceId} /> : null}
    {view === "advertising-analysis" && pageAccessible ? <AdvertisingAnalysisView workspaceId={selectedWorkspaceId} /> : null}
    {view === "competitor-selection-analysis" && active ? <CompetitorSelectionAnalysisView workspaceId={selectedWorkspaceId} /> : null}
    {view === "summary-report" && pageAccessible ? <SummaryReportView workspaceId={selectedWorkspaceId} /> : null}
    {view === "agent-triggers" && active ? <AgentTriggersView workspaceId={selectedWorkspaceId} /> : null}
    {view === "agent-permissions" && pageAccessible ? <AgentPermissionsView workspaceId={selectedWorkspaceId} /> : null}
    {view === "external-notifications" && pageAccessible ? <ExternalNotificationsView workspaceId={selectedWorkspaceId} /> : null}
    {/* Performance 凭据属于独立凭据域，不与 Seller 店铺绑定。 */}
    {/* Performance 凭据是账号级配置，不应被当前店铺 active 状态阻断。 */}
    {view === "performance-credentials" ? <PerformanceOAuthView workspaceId={selectedWorkspaceId} /> : null}
    {view === "seller-product-sync" && active ? <SellerProductSyncView workspaceId={selectedWorkspaceId} /> : null}
    {view === "seller-stock-sync" && active ? <SellerStockSyncView workspaceId={selectedWorkspaceId} /> : null}
    {view === "seller-order-sync" && active ? <SellerOrderSyncView workspaceId={selectedWorkspaceId} /> : null}
    {view === "seller-fulfillment-sync" && active ? <SellerFulfillmentSyncView workspaceId={selectedWorkspaceId} /> : null}
    {view === "sync-processor" && active ? <SyncProcessorView /> : null}
    {view === "data-source-labels" && active ? <DataSourceLabelsView /> : null}
    {view === "data-quality-schema" && active ? <DataQualitySchemaView workspaceId={selectedWorkspaceId} /> : null}
    {view === "erp-import" && active ? <ErpImportView /> : null}
    {workspaceError ? <StatePanel icon={<WarningCircle size={27} />} title="本地服务未连接" body={workspaceError} action="重新连接" onAction={() => void refreshWorkspaces()} /> : null}
    {/* 店铺状态兜底不得覆盖账号级 RAG 供应商配置页面。 */}
    {!workspaceError && view !== "accounts" && !pageAccessible ? <StatePanel icon={<Key size={27} />} title={selectedWorkspace ? `${currentViewLabel}暂不可用` : "还没有店铺"} body={selectedWorkspace ? `当前店铺状态为“${STATUS_LABELS[selectedWorkspace.status]}”。请先完成 Ozon Seller 凭据验证，再使用${currentViewLabel}。` : "请先连接并验证 Ozon Seller 店铺，再使用运营功能。"} action="管理店铺连接" onAction={() => setView("accounts")} /> : null}
    {view !== "accounts" && active && state.status === "loading" ? <div className="loading-grid"><div /><div /><div /></div> : null}
    {view !== "accounts" && active && state.status === "error" ? <StatePanel icon={<WarningCircle size={27} />} title="商品读取失败" body={state.message} action="重新加载" onAction={() => void loadOffers()} /> : null}
    {state.status === "ready" && view === "overview" ? <div className="view-content"><PageHeading label="运营总览" title="晚上好，运营人" note={`${selectedWorkspace?.display_name} · ${lastSyncedAt?.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })} 更新`} /><section className="hero-metric"><div><span>在库商品总量</span><strong>{metrics.stock.toLocaleString()}</strong><small><b>↑ 已同步</b> Ozon 实时库存</small></div><Cube size={34} weight="duotone" /></section><section className="metric-grid"><article><span>库存货值</span><strong>{Math.round(metrics.value / 1000).toLocaleString()}k</strong><small>按当前售价估算</small></article><article className="risk"><span>风险 SKU</span><strong>{metrics.risk + metrics.empty}</strong><small>{metrics.empty} 项已缺货</small></article></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">库存信号</p><h2>优先处理</h2></div><button className="text-button" onClick={() => setView("products")}>查看全部 <ArrowRight size={14} /></button></div>{offers.filter((o) => o.available_stock <= LOW_STOCK_THRESHOLD).slice(0, 4).map((o) => <ProductRow offer={o} key={o.offer_id} />)}{!metrics.risk && !metrics.empty ? <div className="healthy-state"><CheckCircle size={22} />当前库存状态健康</div> : null}</section></div> : null}
    {state.status === "ready" && view === "products" ? <div className="view-content"><PageHeading label="商品 LISTING" title="商品与库存" note={`共 ${offers.length} 个 SKU`} compact /><div className="toolbar"><label><MagnifyingGlass size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索商品名称或 SKU" /></label><select value={stockFilter} onChange={(e) => setStockFilter(e.target.value as StockFilter)}><option value="all">全部</option><option value="available">在售</option><option value="risk">低库存</option><option value="empty">缺货</option></select></div><section className="panel"><div className="list-summary"><span>商品列表</span><b>{filteredOffers.length}</b></div>{filteredOffers.map((o) => <ProductRow offer={o} key={o.offer_id} />)}{!filteredOffers.length ? <div className="empty-search"><MagnifyingGlass size={24} /><strong>没有匹配的商品</strong><span>更换关键词或筛选条件后重试</span></div> : null}</section></div> : null}
    {view === "operations" && active && operationState.status === "loading" ? <div className="loading-grid"><div /><div /><div /></div> : null}
    {view === "operations" && active && operationState.status === "error" ? <StatePanel icon={<WarningCircle size={27} />} title="运营数据读取失败" body={operationState.message} action="重新加载" onAction={() => { setOperationState({ status: "idle" }); setView("overview"); queueMicrotask(() => setView("operations")); }} /> : null}
    {view === "operations" && operationState.status === "ready" ? <OperationsView data={operationState.data} /> : null}
    {view === "tasks" && active && taskState.status === "loading" ? <div className="loading-grid"><div /><div /><div /></div> : null}
    {view === "tasks" && active && taskState.status === "error" ? <StatePanel icon={<WarningCircle size={27} />} title="任务与审计读取失败" body={taskState.message ?? "请求失败"} action="重新加载" onAction={() => setView("overview")} /> : null}
    {view === "tasks" && taskState.status === "ready" ? <><TaskView operations={taskState.operations} currentJob={currentJob} busy={syncBusy} onSync={(type) => void handleSync(type)} /><TaskHistory jobs={taskState.jobs} actionBusy={taskActionBusy} onAction={(id, action) => void handleTaskAction(id, action)} /></> : null}
    {view === "accounts" ? <div className="view-content account-view"><PageHeading label="安全连接" title="卖家工作区" note={`${workspaces.length} 个店铺账户`} compact /><section className="workspace-list">{workspaces.map((w) => <article className={`workspace-card ${w.id === selectedWorkspaceId ? "selected" : ""}`} key={w.id}><button className="workspace-main" onClick={() => changeWorkspace(w.id)}><span className={`workspace-avatar ${w.status}`}><Storefront size={18} /></span><span><strong>{w.display_name}</strong><small>{STATUS_LABELS[w.status]}</small></span></button>{w.status !== "active" && w.status !== "disabled" ? <button className="verify-button" disabled={verifyBusyId === w.id} onClick={() => void handleVerify(w.id)}>{verifyBusyId === w.id ? "验证中" : "验证"}</button> : <CheckCircle className="verified" size={18} weight="fill" />}</article>)}</section><CredentialForm busy={formBusy} onSubmit={(e) => void handleCredentialSubmit(e, "create")} />{selectedWorkspace && selectedWorkspace.id !== "local" ? <form className="credential-form" onSubmit={(e) => void handleCredentialSubmit(e, "replace")}><FormTitle icon={<Key size={17} />} title="更换当前凭据" note={selectedWorkspace.display_name} /><label><span>新 Client ID</span><input name="client_id" required /></label><label><span>新 Api-Key</span><input name="api_key" type="password" required /></label><button className="secondary-button" disabled={formBusy}>更换凭据</button></form> : null}{formMessage ? <p className="form-message">{formMessage}</p> : null}</div> : null}
  </main>;
}
function PageHeading({ label, title, note, compact }: { label: string; title: string; note: string; compact?: boolean }) { return <section className={`page-heading ${compact ? "compact" : ""}`}><div><p className="eyebrow">{label}</p><h1>{title}</h1><p>{note}</p></div>{compact ? <ShieldCheck size={28} weight="duotone" /> : <span className="live-badge"><i />实时</span>}</section>; }
function LoginView({ busy, error, onLogin }: { busy: boolean; error: string; onLogin: (email: string, password: string) => Promise<void> }) { const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); void onLogin(String(data.get("email") ?? "").trim(), String(data.get("password") ?? "")); }; return <main className="auth-shell"><section className="auth-card"><div className="brand-mark"><Cube size={22} weight="fill" /></div><p className="eyebrow">OZON SELLER OPERATIONS</p><h1>登录运营工作台</h1><p className="auth-note">使用项目运营账号进入工作区。</p><form onSubmit={submit}><label>邮箱<input name="email" type="email" autoComplete="username" required /></label><label>密码<input name="password" type="password" autoComplete="current-password" minLength={12} required /></label>{error ? <p className="form-message">{error}</p> : null}<button className="primary-button" disabled={busy}>{busy ? "登录中…" : "登录"}</button></form></section></main>; }
function StatePanel({ icon, title, body, action, onAction }: { icon: React.ReactNode; title: string; body: string; action: string; onAction: () => void }) { return <section className="state-panel">{icon}<h2>{title}</h2><p>{body}</p><button className="primary-button" onClick={onAction}>{action}</button></section>; }
function FormTitle({ icon, title, note }: { icon: React.ReactNode; title: string; note: string }) { return <div className="form-title"><span>{icon}</span><div><h2>{title}</h2><p>{note}</p></div></div>; }
function CredentialForm({ busy, onSubmit }: { busy: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) { return <form className="credential-form" onSubmit={onSubmit}><FormTitle icon={<Plus size={16} />} title="连接新店铺" note="凭据由后端加密保存" /><label><span>工作区名称</span><input name="display_name" placeholder="例如：俄罗斯主店" required /></label><label><span>Client ID</span><input name="client_id" placeholder="Ozon Seller Client ID" required /></label><label><span>Api-Key</span><input name="api_key" type="password" placeholder="不会保存在浏览器中" required /></label><button className="primary-button" disabled={busy}>{busy ? "正在安全保存…" : "创建待验证工作区"}</button></form>; }
function OperationsView({ data }: { data: OperationData }) { return <div className="view-content"><PageHeading label="运营事实" title="库存、订单与履约" note="数据来自最近一次成功同步" compact /><section className="operation-summary"><article><Warehouse size={19} /><span>库存仓位</span><strong>{data.stockPositions.length}</strong></article><article><ShoppingCart size={19} /><span>客户订单</span><strong>{data.customerOrders.length}</strong></article><article><Truck size={19} /><span>履约单</span><strong>{data.postings.length}</strong></article></section><OperationSection title="库存仓位" empty="暂无库存仓位" count={data.stockPositions.length}><>{data.stockPositions.map((item) => <div className="operation-row" key={`${item.offer_id}-${item.warehouse_id}-${item.fulfillment_type}`}><span><strong>{item.offer_id}</strong><small>{item.warehouse_name ?? item.warehouse_id} · {item.fulfillment_type}</small></span><b>{item.available_quantity} 可售</b><em>{item.reserved_quantity} 预留</em></div>)}</></OperationSection><OperationSection title="最近订单" empty="暂无客户订单" count={data.customerOrders.length}><>{data.customerOrders.map((item) => <div className="operation-row" key={item.order_id}><span><strong>{item.ozon_order_id}</strong><small>{new Date(item.ordered_at).toLocaleString("zh-CN")}</small></span><b>{formatPrice(item.total_amount, item.currency)}</b><em>{item.status}</em></div>)}</></OperationSection><OperationSection title="FBO/FBS 履约" empty="暂无履约单" count={data.postings.length}><>{data.postings.map((item) => <div className="operation-row" key={item.posting_id}><span><strong>{item.ozon_posting_number}</strong><small>{item.fulfillment_type} · {item.item_count} 项 / {item.total_quantity} 件</small></span><b>{item.shipment_date ?? "待排期"}</b><em>{item.status}</em></div>)}</></OperationSection></div>; }
function OperationSection({ title, empty, count, children }: { title: string; empty: string; count: number; children: React.ReactElement }) { return <section className="panel operation-panel"><div className="list-summary"><span>{title}</span><b>{count}</b></div>{count > 0 ? children : <div className="empty-search"><strong>{empty}</strong><span>完成同步后将在这里显示</span></div>}</section>; }
function syncStatusLabel(status: SyncJob["status"]): string { return { queued: "排队中", running: "执行中", succeeded: "已完成", partial: "部分成功", failed: "失败", cancelled: "已取消" }[status]; }
function TaskHistory({ jobs, actionBusy, onAction }: { jobs: SyncJob[]; actionBusy: string; onAction: (jobId: string, action: "cancel" | "retry") => void }) { const labels: Record<SyncResourceType, string> = { products: "商品", stock: "库存", orders: "订单", postings: "履约" }; return <OperationSection title="同步任务历史" empty="暂无同步任务" count={jobs.length}><>{jobs.map((job) => <div className="operation-row" key={job.id}><span><strong>{labels[job.resource_type]}同步</strong><small>{new Date(job.created_at).toLocaleString("zh-CN")} · {job.id}</small></span><b>{job.processed_count} 已处理</b><em>{syncStatusLabel(job.status)}</em><div className="task-actions">{job.status === "queued" || job.status === "running" ? <button className="text-button" disabled={Boolean(actionBusy)} onClick={() => onAction(job.id, "cancel")}>{actionBusy === job.id ? "处理中…" : "取消"}</button> : null}{job.status === "failed" || job.status === "partial" ? <button className="text-button" disabled={Boolean(actionBusy)} onClick={() => onAction(job.id, "retry")}>{actionBusy === job.id ? "处理中…" : "重试"}</button> : null}</div></div>)}</></OperationSection>; }
function TaskView({ operations, currentJob, busy, onSync }: { operations: SellerOperationSummary[]; currentJob: SyncJob | null; busy: SyncResourceType | ""; onSync: (type: SyncResourceType) => void }) { const labels: Record<SyncResourceType, string> = { products: "商品", stock: "库存", orders: "订单", postings: "履约" }; return <div className="view-content"><PageHeading label="任务中心" title="同步与操作审计" note="同步任务先持久化，再进入队列执行" compact /><section className="panel"><div className="section-heading"><div><p className="eyebrow">手动同步</p><h2>创建同步任务</h2></div></div><div className="sync-actions">{(Object.keys(labels) as SyncResourceType[]).map((type) => <button className="secondary-button" disabled={Boolean(busy)} onClick={() => onSync(type)} key={type}>{busy === type ? "创建中…" : `同步${labels[type]}`}</button>)}</div>{currentJob ? <div className="job-card"><strong>{labels[currentJob.resource_type]}同步任务</strong><span>{syncStatusLabel(currentJob.status)} · 已处理 {currentJob.processed_count} · 失败 {currentJob.failure_count}</span>{currentJob.error_message ? <small className="task-error">{currentJob.error_message}</small> : null}<small>{currentJob.id}</small></div> : null}</section><OperationSection title="最近操作审计" empty="暂无操作记录" count={operations.length}><>{operations.map((item) => <div className="operation-row" key={item.operation_id}><span><strong>{item.operation_type}</strong><small>{new Date(item.occurred_at).toLocaleString("zh-CN")} · {item.risk_level}</small></span><b>{item.target_count} 个目标</b><em>{item.result}</em></div>)}</></OperationSection></div>; }
