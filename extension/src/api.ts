export type WorkspaceStatus = "pending" | "active" | "invalid" | "disabled";

export interface StoreWorkspace {
  id: string;
  display_name: string;
  status: WorkspaceStatus;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

export interface KnowledgeAnswer {
  answer_id: string;
  trace_id: string;
  status: string;
  segments: Array<{
    text: string;
    intent: string;
    status: string;
    answer: string;
    reason: string | null;
    normalized_query: string;
    citations: Array<{ chunk_id: string; source_locator: string; title_path: string[]; score: number; excerpt: string }>;
  }>;
  message: string;
}

export interface KnowledgeSource {
  id: string;
  title: string;
  source_type: string;
  business_domain: string;
  source_locator: string;
  authority_level: string;
  sensitivity: string;
  status: string;
}

export interface KnowledgeVersion {
  id: string;
  source_id: string;
  version_number: number;
  content_hash: string;
  status: string;
}

export interface KnowledgeIngestionResult {
  document_id: string;
  document_version_id: string;
  parser_name: string;
  cleaner_version: string;
  content_hash: string;
  quality_passed: boolean;
  blocked_reason: string | null;
  chunks: Array<{ chunk_id: string; ordinal: number; source_locator: string; title_path: string[]; content: string }>;
}

export interface ModelBudget {
  provider_id: string;
  purpose: string;
  policy: {
    daily_token_limit: number;
    monthly_token_limit: number;
    daily_request_limit: number;
    monthly_budget: number;
    budget_currency: "RMB";
    purpose: string;
  };
  usage: {
    daily_tokens: number;
    monthly_tokens: number;
    daily_requests: number;
    monthly_cost: number;
  };
  state: "normal" | "warning" | "exceeded";
  allowed: boolean;
  reason: string | null;
}

let sessionToken: string | null = null;

/**
 * 生成请求追踪与幂等标识。
 * HTTP 开发站点可能不暴露 randomUUID，但 getRandomValues 仍可提供密码学安全随机数；
 * 禁止退化为 Math.random，避免碰撞导致不同写请求被错误视为同一请求。
 */
export function createRequestId(): string {
  const webCrypto = globalThis.crypto;
  if (typeof webCrypto?.randomUUID === "function") {
    return webCrypto.randomUUID();
  }
  if (typeof webCrypto?.getRandomValues !== "function") {
    throw new Error("当前浏览器不支持安全随机数，无法创建请求标识");
  }

  const bytes = webCrypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join("")
  ].join("-");
}

export interface StoreCredentials {
  client_id: string;
  api_key: string;
}

export interface CreateWorkspaceRequest extends StoreCredentials {
  display_name: string;
}

export interface CreateSellerAccountRequest {
  display_name: string;
  workspace_name: string;
  client_id: string;
  api_key: string;
}

export interface CreatedSellerAccount {
  seller_account_id: string;
  workspace_id: string;
}

export interface ProductOffer {
  offer_id: string;
  ozon_product_id: string | null;
  name: string;
  price: string;
  currency: string;
  available_stock: number;
}

export interface ProductOfferPage {
  items: ProductOffer[];
  total: number;
  next_cursor: string | null;
  source: string;
}

export interface StockPosition {
  offer_id: string;
  warehouse_id: string;
  warehouse_name: string | null;
  fulfillment_type: "FBO" | "FBS";
  available_quantity: number;
  reserved_quantity: number;
  synced_at: string;
}

export interface CustomerOrder {
  order_id: string;
  ozon_order_id: string;
  status: string;
  total_amount: string;
  currency: string;
  ordered_at: string;
  synced_at: string;
}

export interface PostingSummary {
  posting_id: string;
  customer_order_id: string | null;
  ozon_posting_number: string;
  fulfillment_type: "FBO" | "FBS";
  status: string;
  shipment_date: string | null;
  item_count: number;
  total_quantity: number;
  synced_at: string;
}

export interface OperationData {
  stockPositions: StockPosition[];
  customerOrders: CustomerOrder[];
  postings: PostingSummary[];
}

/** 返回运营事实中最近一次成功同步时间，页面据此标注数据新鲜度。 */
export function latestOperationSyncAt(data: OperationData): string | null {
  const timestamps = [...data.stockPositions, ...data.customerOrders, ...data.postings]
    .map((item) => item.synced_at)
    .filter(Boolean)
    .sort();
  return timestamps.at(-1) ?? null;
}

export type SyncResourceType = "products" | "stock" | "orders" | "postings";
export type SyncJobStatus = "queued" | "running" | "succeeded" | "partial" | "failed" | "cancelled";

export interface SyncJob {
  id: string;
  workspace_id: string;
  resource_type: SyncResourceType;
  status: SyncJobStatus;
  processed_count: number;
  failure_count: number;
  error_message: string | null;
  attempt_count: number;
  max_attempts: number;
  created_at: string;
  completed_at: string | null;
}

export interface SellerOperationSummary {
  operation_id: string;
  operation_type: string;
  risk_level: "read" | "reversible_write" | "destructive_write";
  target_type: string | null;
  target_count: number;
  request_id: string | null;
  result: "success" | "partial" | "failed" | "cancelled";
  occurred_at: string;
}

export interface TaskData {
  jobs: SyncJob[];
  operations: SellerOperationSummary[];
}

export interface QualityFinding {
  id?: string;
  workspace_id?: string;
  rule_code: string;
  field_name: string;
  severity: "warning" | "error";
  message: string;
  status: "open" | "accepted" | "resolved" | "ignored";
  source: "derived_quality";
  created_at?: string;
}

export interface QualitySummary {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_rule: Record<string, number>;
}

export interface QualityCheckResult {
  findings: QualityFinding[];
  valid: boolean;
}

interface ApiErrorPayload {
  detail?: string | {
    code?: string;
    message?: string;
  } | Array<{ loc?: Array<string | number>; msg?: string }>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string
  ) {
    super(message);
  }
}

/**
 * 解析当前客户端使用的 API 根地址。
 * Web 页面必须走 Nginx 的同源 `/api` 代理，以便会话 Cookie 随请求发送；Chrome 扩展没有
 * HTTP(S) 页面源，开发时才回退到本机 FastAPI。显式环境变量始终拥有最高优先级。
 */
export function resolveApiBaseUrl(
  configuredUrl: string | undefined,
  protocol: string = globalThis.location?.protocol ?? ""
): string {
  if (configuredUrl) return configuredUrl.replace(/\/$/, "");
  return protocol === "http:" || protocol === "https:" ? "/api" : "http://127.0.0.1:8000";
}

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL as string | undefined);

async function requestJson<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": createRequestId(),
      ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
      ...init.headers
    }
  });

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      // 非 JSON 错误由统一消息处理，避免把后端原始内容带入界面。
    }
    const detail = payload.detail;
    const detailMessage = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg ?? "字段校验失败").join("；")
        : detail?.message;
    const detailCode = typeof detail === "object" && !Array.isArray(detail) ? detail?.code : undefined;
    throw new ApiError(
      detailMessage ?? `本地服务请求失败，状态码 ${response.status}`,
      response.status,
      detailCode ?? "request_failed"
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const result = await requestJson<AuthUser & { session_token?: string }>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  sessionToken = result.session_token ?? null;
  return result;
}

export function fetchCurrentUser(signal?: AbortSignal): Promise<AuthUser> {
  return requestJson("/v1/auth/me", { signal });
}

export async function logout(): Promise<void> {
  try {
    await requestJson<void>("/v1/auth/logout", { method: "POST" });
  } finally {
    sessionToken = null;
  }
}

export function fetchStoreWorkspaces(signal?: AbortSignal): Promise<StoreWorkspace[]> {
  return requestJson("/v1/store-workspaces", { signal });
}

/** 管理员创建卖家账户和首个工作区；凭据只进入请求体，不写入浏览器存储。 */
export function createSellerAccount(
  request: CreateSellerAccountRequest
): Promise<CreatedSellerAccount> {
  return requestJson("/v1/seller-accounts", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

export function createStoreWorkspace(
  request: CreateWorkspaceRequest
): Promise<StoreWorkspace> {
  return requestJson("/v1/store-workspaces", {
    method: "POST",
    body: JSON.stringify(request)
  });
}

export function replaceStoreCredentials(
  workspaceId: string,
  request: StoreCredentials
): Promise<StoreWorkspace> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/credentials`, {
    method: "PUT",
    body: JSON.stringify(request)
  });
}

export function verifyStoreWorkspace(workspaceId: string): Promise<StoreWorkspace> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/verify`, {
    method: "POST"
  });
}

export function fetchProductOffers(
  workspaceId: string,
  signal?: AbortSignal
): Promise<ProductOfferPage> {
  return requestJson(
    `/v1/store-workspaces/${encodeURIComponent(workspaceId)}/product-offers?limit=20`,
    { signal }
  );
}

export async function fetchOperationData(
  workspaceId: string,
  signal?: AbortSignal
): Promise<OperationData> {
  const encodedId = encodeURIComponent(workspaceId);
  const [stockPage, orderPage, postingPage] = await Promise.all([
    requestJson<{ items: StockPosition[] }>(
      `/v1/store-workspaces/${encodedId}/stock-positions?limit=20`,
      { signal }
    ),
    requestJson<{ items: CustomerOrder[] }>(
      `/v1/store-workspaces/${encodedId}/customer-orders?limit=20`,
      { signal }
    ),
    requestJson<{ items: PostingSummary[] }>(
      `/v1/store-workspaces/${encodedId}/postings?limit=20`,
      { signal }
    )
  ]);
  return {
    stockPositions: stockPage.items,
    customerOrders: orderPage.items,
    postings: postingPage.items
  };
}

export async function fetchTaskData(workspaceId: string, signal?: AbortSignal): Promise<TaskData> {
  const encodedId = encodeURIComponent(workspaceId);
  const [operations, jobs] = await Promise.all([
    requestJson<{ items: SellerOperationSummary[] }>(
      `/v1/store-workspaces/${encodedId}/seller-operations?limit=20`,
      { signal }
    ),
    requestJson<{ items: SyncJob[] }>(
      `/v1/store-workspaces/${encodedId}/sync-jobs?limit=20`,
      { signal }
    )
  ]);
  return { jobs: jobs.items, operations: operations.items };
}

export function createSyncJob(workspaceId: string, resourceType: SyncResourceType): Promise<SyncJob> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/sync-jobs`, {
    method: "POST",
    headers: { "Idempotency-Key": createRequestId() },
    body: JSON.stringify({ resource_type: resourceType })
  });
}

export function fetchSyncJob(jobId: string, signal?: AbortSignal): Promise<SyncJob> {
  return requestJson(`/v1/sync-jobs/${encodeURIComponent(jobId)}`, { signal });
}

export function cancelSyncJob(jobId: string): Promise<SyncJob> {
  return requestJson(`/v1/sync-jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
}

export function retrySyncJob(jobId: string): Promise<SyncJob> {
  return requestJson(`/v1/sync-jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST" });
}

export function checkQuality(record: Record<string, unknown>): Promise<QualityCheckResult> {
  return requestJson("/v1/data-quality/check", {
    method: "POST",
    body: JSON.stringify({ record, required_fields: ["offer_id"], enum_fields: { status: ["active", "disabled"] } })
  });
}

export function fetchQualityFindings(workspaceId: string, status?: string): Promise<QualityFinding[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/data-quality/findings${suffix}`);
}

export function fetchQualitySummary(workspaceId: string, status = "open"): Promise<QualitySummary> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/data-quality/summary?status=${encodeURIComponent(status)}`);
}

export function createQualityFindings(workspaceId: string, findings: QualityFinding[]): Promise<QualityFinding[]> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/data-quality/findings`, {
    method: "POST",
    body: JSON.stringify(findings)
  });
}

export function updateQualityFinding(findingId: string, workspaceId: string, status: "accepted" | "resolved" | "ignored"): Promise<QualityFinding> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/data-quality/findings/${encodeURIComponent(findingId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export interface KeywordImportRow {
  keyword: string;
  search_count: number | null;
  conversion_rate: string | null;
  source_row: number;
}

export interface KeywordImportPreview {
  rows: KeywordImportRow[];
  total: number;
  fingerprint: string;
}

export interface KeywordImportBatch {
  id: string;
  workspace_id: string;
  fingerprint: string;
  row_count: number;
  created_at: string;
  reused: boolean;
}

export function previewKeywordImport(workspaceId: string, content: string): Promise<KeywordImportPreview> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/keyword-report-imports/preview`, {
    method: "POST",
    headers: { "Content-Type": "text/csv" },
    body: content
  });
}

export function previewMappedKeywordImport(workspaceId: string, content: string, columnMapping: Record<string, string>): Promise<KeywordImportPreview> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/keyword-report-imports/preview-mapped`, {
    method: "POST",
    body: JSON.stringify({ content, column_mapping: columnMapping })
  });
}
export function previewKeywordXlsx(workspaceId: string, content: ArrayBuffer): Promise<KeywordImportPreview> { return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/keyword-report-imports/preview-xlsx`, { method: "POST", headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }, body: content }); }
export function previewMappedKeywordXlsx(workspaceId: string, contentBase64: string, columnMapping: Record<string, string>): Promise<KeywordImportPreview> { return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/keyword-report-imports/preview-xlsx-mapped`, { method: "POST", body: JSON.stringify({ content_base64: contentBase64, column_mapping: columnMapping }) }); }

export function commitKeywordImport(workspaceId: string, fingerprint: string, rows: KeywordImportRow[]): Promise<KeywordImportBatch> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/keyword-report-imports`, {
    method: "POST",
    body: JSON.stringify({ fingerprint, rows })
  });
}
export function listKeywordImportHistory(workspaceId: string): Promise<KeywordImportBatch[]> { return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/keyword-report-imports/history`, { method: "GET" }); }

export interface CompetitorSeed {
  id: string;
  workspace_id: string;
  url: string;
  title: string | null;
  status: "active" | "paused" | "blocked";
}

export function fetchCompetitorSeeds(workspaceId: string): Promise<CompetitorSeed[]> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/competitor-seeds`);
}

export function createCompetitorSeed(workspaceId: string, url: string): Promise<CompetitorSeed> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/competitor-seeds`, {
    method: "POST",
    body: JSON.stringify({ url })
  });
}

export function updateCompetitorSeed(workspaceId: string, seedId: string, status: CompetitorSeed["status"]): Promise<CompetitorSeed> {
  return requestJson(`/v1/store-workspaces/${encodeURIComponent(workspaceId)}/competitor-seeds/${encodeURIComponent(seedId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export interface SamplingPolicyDecision {
  allowed: boolean;
  code: string;
  message: string;
  normalized_url: string | null;
}

export function checkSamplingPolicy(url: string, robotsAllowed: boolean, rateLimited = false, stopRequested = false): Promise<SamplingPolicyDecision> {
  return requestJson("/v1/sampling-policy/check", {
    method: "POST",
    body: JSON.stringify({ url, robots_allowed: robotsAllowed, rate_limited: rateLimited, stop_requested: stopRequested })
  });
}
export function checkAndRecordSamplingPolicy(workspaceId: string, url: string, robotsAllowed: boolean, rateLimited = false, stopRequested = false): Promise<SamplingPolicyDecision> { return requestJson(`/v1/sampling-policy/store-workspaces/${encodeURIComponent(workspaceId)}/check-and-record`, { method: "POST", body: JSON.stringify({ url, robots_allowed: robotsAllowed, rate_limited: rateLimited, stop_requested: stopRequested }) }); }

export interface SamplingResult {
  url: string;
  allowed: boolean;
  status_code: number | null;
  attempts: number;
  message: string;
}

export function checkPublicSampling(urls: string[], globalLimit = 2, maxAttempts = 3): Promise<SamplingResult[]> {
  return requestJson("/v1/public-sampling/preview", {
    method: "POST",
    body: JSON.stringify({ requests: urls.map((url) => ({ url })), global_limit: globalLimit, max_attempts: maxAttempts })
  });
}
export function checkAndRecordPublicSampling(workspaceId: string, urls: string[], globalLimit = 2, maxAttempts = 3): Promise<SamplingResult[]> { return requestJson(`/v1/public-sampling/store-workspaces/${encodeURIComponent(workspaceId)}/preview-and-record`, { method: "POST", body: JSON.stringify({ requests: urls.map((url) => ({ url })), global_limit: globalLimit, max_attempts: maxAttempts }) }); }

export interface PublicSnapshot {
  url: string;
  sampled_at: string;
  title: string | null;
  price_minor: number | null;
  currency: string | null;
  rating: string | null;
  review_count: number | null;
  image_url: string | null;
  attributes: Record<string, string>;
  sample_size: number;
  estimated: boolean;
}

export function normalizePublicSnapshot(payload: Record<string, unknown>): Promise<PublicSnapshot> {
  return requestJson("/v1/public-snapshots/normalize", { method: "POST", body: JSON.stringify(payload) });
}

export function savePublicSnapshot(workspaceId: string, payload: Record<string, unknown>): Promise<PublicSnapshot> {
  return requestJson(`/v1/public-snapshots/store-workspaces/${encodeURIComponent(workspaceId)}/save`, { method: "POST", body: JSON.stringify(payload) });
}
export function listPublicSnapshotHistory(workspaceId: string): Promise<PublicSnapshot[]> { return requestJson(`/v1/public-snapshots/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface SampleScope {
  sample_count: number;
  sampled_from: string | null;
  sampled_to: string | null;
  estimated: boolean;
  missing_fields: string[];
  caveat: string;
}

export function summarizePublicSampleScope(records: Record<string, unknown>[]): Promise<SampleScope> {
  return requestJson("/v1/public-samples/scope", { method: "POST", body: JSON.stringify({ records }) });
}
export function fetchWorkspaceSampleScope(workspaceId: string): Promise<SampleScope> { return requestJson(`/v1/public-samples/store-workspaces/${encodeURIComponent(workspaceId)}/scope`, { method: "GET" }); }

export interface ParserChange {
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  severity: "warning" | "error";
  message: string;
}

export function compareParserResults(previous: Record<string, string | null>, current: Record<string, string | null>): Promise<ParserChange[]> {
  return requestJson("/v1/parser-alerts/compare", { method: "POST", body: JSON.stringify({ previous, current }) });
}

export function compareAndSaveParserResults(workspaceId: string, url: string, previous: Record<string, string | null>, current: Record<string, string | null>): Promise<ParserChange[]> {
  return requestJson(`/v1/parser-alerts/store-workspaces/${encodeURIComponent(workspaceId)}/compare-and-save`, { method: "POST", body: JSON.stringify({ url, previous, current }) });
}
export function listParserAlertHistory(workspaceId: string): Promise<ParserChange[]> { return requestJson(`/v1/parser-alerts/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface ExploreOpportunity {
  keyword: string;
  score: number;
  search_count: number;
  conversion_rate: number | null;
  sample_count: number;
  median_price_minor: number | null;
  own_coverage_gap: boolean;
  estimated: boolean;
  reasons: string[];
  missing_inputs: string[];
}

export function runSelectionExplore(items: Record<string, unknown>[]): Promise<ExploreOpportunity[]> {
  return requestJson("/v1/selection/explore/run", { method: "POST", body: JSON.stringify({ items }) });
}

export function runAndSaveSelectionExplore(workspaceId: string, items: Record<string, unknown>[]): Promise<ExploreOpportunity[]> {
  return requestJson(`/v1/selection/explore/store-workspaces/${encodeURIComponent(workspaceId)}/run-and-save`, { method: "POST", body: JSON.stringify({ items }) });
}
export function listSelectionExploreOpportunities(workspaceId: string): Promise<ExploreOpportunity[]> { return requestJson(`/v1/selection/explore/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface FulfillmentProfit { fulfillment_type: string; contribution_profit_minor: number; margin_percent: number; roi_percent: number; break_even_units: number | null; }
export interface ValidateResult { sku: string; fbo: FulfillmentProfit; fbs: FulfillmentProfit; risks: string[]; incomplete: boolean; incomplete_reasons: string[]; }
export function runSelectionValidate(payload: Record<string, unknown>): Promise<ValidateResult> { return requestJson("/v1/selection/validate/run", { method: "POST", body: JSON.stringify(payload) }); }
export function runAndSaveSelectionValidate(workspaceId: string, payload: Record<string, unknown>): Promise<ValidateResult> { return requestJson(`/v1/selection/validate/store-workspaces/${encodeURIComponent(workspaceId)}/run-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listSelectionValidations(workspaceId: string): Promise<ValidateResult[]> { return requestJson(`/v1/selection/validate/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface ExpandResult { seed_product: string; core_terms: string[]; attribute_terms: string[]; scene_terms: string[]; variant_candidates: string[]; estimated: boolean; missing_inputs: string[]; }
export function runSelectionExpand(payload: Record<string, unknown>): Promise<ExpandResult> { return requestJson("/v1/selection/expand/run", { method: "POST", body: JSON.stringify(payload) }); }
export function runAndSaveSelectionExpand(workspaceId: string, payload: Record<string, unknown>): Promise<ExpandResult> { return requestJson(`/v1/selection/expand/store-workspaces/${encodeURIComponent(workspaceId)}/run-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listSelectionExpansions(workspaceId: string): Promise<ExpandResult[]> { return requestJson(`/v1/selection/expand/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface SelectionDecisionBook { opportunity_summary: string; customer_scene: string; market_sample: string; competitor_snapshots: string[]; profit_calculation: string; risks: string[]; price_range: string; stock_recommendation: string; seed_keywords: string[]; data_sources: string[]; uncertainty: string; confirmation_status: "pending" | "confirmed" | "rejected"; }
export function generateAndSaveDecisionBook(workspaceId: string, payload: SelectionDecisionBook): Promise<SelectionDecisionBook> { return requestJson(`/v1/selection/decision-books/store-workspaces/${encodeURIComponent(workspaceId)}/generate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function confirmDecisionBook(workspaceId: string, payload: SelectionDecisionBook): Promise<SelectionDecisionBook> { return requestJson(`/v1/selection/decision-books/store-workspaces/${encodeURIComponent(workspaceId)}/confirm`, { method: "POST", body: JSON.stringify(payload) }); }
export function listDecisionBooks(workspaceId: string): Promise<SelectionDecisionBook[]> { return requestJson(`/v1/selection/decision-books/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }

export interface CompetitionAnalysis { sample_count: number; competition_score: number; median_price_minor: number | null; price_band_low_minor: number | null; price_band_high_minor: number | null; seller_concentration_percent: number; brand_concentration_percent: number; estimated: boolean; caveat: string; }
export function analyzeCompetition(items: Record<string, unknown>[]): Promise<CompetitionAnalysis> { return requestJson("/v1/selection/competition/analyze", { method: "POST", body: JSON.stringify({ items }) }); }
export function analyzeAndSaveCompetition(workspaceId: string, items: Record<string, unknown>[]): Promise<CompetitionAnalysis> { return requestJson(`/v1/selection/competition/store-workspaces/${encodeURIComponent(workspaceId)}/analyze-and-save`, { method: "POST", body: JSON.stringify({ items }) }); }
export function listCompetitionAnalyses(workspaceId: string): Promise<CompetitionAnalysis[]> { return requestJson(`/v1/selection/competition/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface ProfitScenario { fulfillment_type: string; contribution_profit_minor: number; contribution_margin_percent: number; roi_percent: number; break_even_units: number | null; ad_cost_plus_20_profit_minor: number; purchase_cost_plus_20_profit_minor: number; logistics_cost_plus_20_profit_minor: number; }
export function calculateProfitModel(payload: Record<string, unknown>): Promise<ProfitScenario[]> { return requestJson("/v1/selection/profit-model/calculate", { method: "POST", body: JSON.stringify(payload) }); }
export function calculateAndSaveProfitModel(workspaceId: string, payload: Record<string, unknown>): Promise<ProfitScenario[]> { return requestJson(`/v1/selection/profit-model/store-workspaces/${encodeURIComponent(workspaceId)}/calculate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }

export interface CostSensitivityScenario { label: string; change_percent: number; profit_minor: number; margin_percent: number; }
export function analyzeCostSensitivity(payload: Record<string, unknown>): Promise<CostSensitivityScenario[]> { return requestJson("/v1/selection/cost-sensitivity/analyze", { method: "POST", body: JSON.stringify(payload) }); }
export function analyzeAndSaveCostSensitivity(workspaceId: string, payload: Record<string, unknown>): Promise<CostSensitivityScenario[]> { return requestJson(`/v1/selection/cost-sensitivity/store-workspaces/${encodeURIComponent(workspaceId)}/analyze-and-save`, { method: "POST", body: JSON.stringify(payload) }); }

export interface ListingKeyword { keyword: string; source: string; observed_at: string; language: string; layer: "core" | "attribute" | "scene" | "long_tail"; product_scope: string; }
export function normalizeListingKeyword(payload: Record<string, unknown>): Promise<ListingKeyword> { return requestJson("/v1/listing/keywords/normalize", { method: "POST", body: JSON.stringify(payload) }); }
export function normalizeAndSaveListingKeyword(workspaceId: string, payload: Record<string, unknown>): Promise<ListingKeyword> { return requestJson(`/v1/listing/keywords/store-workspaces/${encodeURIComponent(workspaceId)}/normalize-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listListingKeywordHistory(workspaceId: string): Promise<ListingKeyword[]> { return requestJson(`/v1/listing/keywords/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface LayeredKeyword { keyword: string; layer: "core" | "attribute" | "scene" | "long_tail"; reason: string; manually_confirmed: boolean; }
export function classifyListingKeywords(payload: Record<string, unknown>): Promise<LayeredKeyword[]> { return requestJson("/v1/listing/keywords/classify", { method: "POST", body: JSON.stringify(payload) }); }
export function classifyAndSaveListingKeywords(workspaceId: string, payload: Record<string, unknown>): Promise<LayeredKeyword[]> { return requestJson(`/v1/listing/keywords/store-workspaces/${encodeURIComponent(workspaceId)}/classify-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listListingLayerHistory(workspaceId: string): Promise<LayeredKeyword[]> { return requestJson(`/v1/listing/keywords/store-workspaces/${encodeURIComponent(workspaceId)}/layers/history`, { method: "GET" }); }

export interface ListingTitleDraft { title: string; category: string; covered_terms: string[]; missing_terms: string[]; character_count: number; risks: string[]; editable: boolean; }
export function generateListingTitleDraft(payload: Record<string, unknown>): Promise<ListingTitleDraft> { return requestJson("/v1/listing/title-drafts/generate", { method: "POST", body: JSON.stringify(payload) }); }
export function generateAndSaveListingTitleDraft(workspaceId: string, payload: Record<string, unknown>): Promise<ListingTitleDraft> { return requestJson(`/v1/listing/title-drafts/store-workspaces/${encodeURIComponent(workspaceId)}/generate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listListingTitleDraftHistory(workspaceId: string): Promise<ListingTitleDraft[]> { return requestJson(`/v1/listing/title-drafts/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface SearchAttributeSuggestion { name: string; suggested_value: string | null; covered: boolean; source_term: string | null; }
export interface SearchAttributesReport { suggestions: SearchAttributeSuggestion[]; coverage_percent: number; missing_required: string[]; editable: boolean; }
export function suggestSearchAttributes(payload: Record<string, unknown>): Promise<SearchAttributesReport> { return requestJson("/v1/listing/search-attributes/suggest", { method: "POST", body: JSON.stringify(payload) }); }
export function suggestAndSaveSearchAttributes(workspaceId: string, payload: Record<string, unknown>): Promise<SearchAttributesReport> { return requestJson(`/v1/listing/search-attributes/store-workspaces/${encodeURIComponent(workspaceId)}/suggest-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listSearchAttributesHistory(workspaceId: string): Promise<SearchAttributesReport[]> { return requestJson(`/v1/listing/search-attributes/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface FabePoint { feature: string; advantage: string; benefit: string; evidence: string | null; copy: string; }
export interface ListingFabeDraft { bullets: FabePoint[]; long_description: string; image_copy_suggestions: string[]; missing_evidence: string[]; editable: boolean; }
export function generateFabeDraft(payload: Record<string, unknown>): Promise<ListingFabeDraft> { return requestJson("/v1/listing/fabe/generate", { method: "POST", body: JSON.stringify(payload) }); }
export function generateAndSaveFabeDraft(workspaceId: string, payload: Record<string, unknown>): Promise<ListingFabeDraft> { return requestJson(`/v1/listing/fabe/store-workspaces/${encodeURIComponent(workspaceId)}/generate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listFabeDraftHistory(workspaceId: string): Promise<ListingFabeDraft[]> { return requestJson(`/v1/listing/fabe/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface SmartSearchFinding { code: string; severity: "warning" | "error"; message: string; suggestion: string; }
export interface SmartSearchReport { findings: SmartSearchFinding[]; covered_terms: string[]; missing_terms: string[]; valid: boolean; original_text_preserved: boolean; }
export function checkSmartSearch(payload: Record<string, unknown>): Promise<SmartSearchReport> { return requestJson("/v1/listing/smart-search/check", { method: "POST", body: JSON.stringify(payload) }); }
export function checkAndSaveSmartSearch(workspaceId: string, payload: Record<string, unknown>): Promise<SmartSearchReport> { return requestJson(`/v1/listing/smart-search/store-workspaces/${encodeURIComponent(workspaceId)}/check-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listSmartSearchHistory(workspaceId: string): Promise<SmartSearchReport[]> { return requestJson(`/v1/listing/smart-search/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface ListingRiskFinding { risk_type: "absolute" | "medical" | "brand" | "certification"; matched_text: string; severity: "warning" | "error"; message: string; suggestion: string; }
export interface ListingRiskReport { findings: ListingRiskFinding[]; original_text: string; safe_to_review: boolean; }
export function checkListingRisks(payload: Record<string, unknown>): Promise<ListingRiskReport> { return requestJson("/v1/listing/risks/check", { method: "POST", body: JSON.stringify(payload) }); }
export function checkAndSaveListingRisks(workspaceId: string, payload: Record<string, unknown>): Promise<ListingRiskReport> { return requestJson(`/v1/listing/risks/store-workspaces/${encodeURIComponent(workspaceId)}/check-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listListingRiskHistory(workspaceId: string): Promise<ListingRiskReport[]> { return requestJson(`/v1/listing/risks/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }

export interface ListingVersion { version: number; original_text: string; edited_text: string; status: "draft" | "review" | "approved" | "rejected"; diff: string[]; }
export interface DiffPreview { field: string; old_value: string | null; new_value: string | null; source: string; impact: string; requires_review: boolean; }
export interface DataFreshnessDecision { data_domain: string; observed_at: string; max_age_seconds: number; age_seconds: number; fresh: boolean; requires_refresh: boolean; message: string; last_success_at: string | null; window: string | null; latency_seconds: number | null; record_count: number | null; error_summary: string | null; }
export function checkAndSaveDataFreshness(workspaceId: string, payload: Record<string, unknown>): Promise<DataFreshnessDecision> { return requestJson(`/v1/review/freshness/store-workspaces/${encodeURIComponent(workspaceId)}/check-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listDataFreshnessHistory(workspaceId: string): Promise<DataFreshnessDecision[]> { return requestJson(`/v1/review/freshness/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export function buildAndSaveDiffPreview(workspaceId: string, payload: Record<string, unknown>): Promise<DiffPreview[]> { return requestJson(`/v1/review/diff-previews/store-workspaces/${encodeURIComponent(workspaceId)}/build-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export interface ManualApproval { approval_id: string; workspace_id: string; command_type: string; payload: Record<string, unknown>; status: "pending" | "approved" | "rejected"; reviewer: string | null; idempotency_key: string; }
export function createManualApproval(workspaceId: string, payload: Record<string, unknown>): Promise<ManualApproval> { return requestJson(`/v1/review/approvals/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "POST", body: JSON.stringify(payload) }); }
export function approveManualApproval(approvalId: string, reviewer: string): Promise<ManualApproval> { return requestJson(`/v1/review/approvals/${encodeURIComponent(approvalId)}/approve`, { method: "POST", body: JSON.stringify({ reviewer }) }); }
export function listPendingManualApprovals(workspaceId: string): Promise<ManualApproval[]> { return requestJson(`/v1/review/approvals/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }
export interface PriceBatchValidation { valid: boolean; total_items: number; max_items: number; message: string; items: Array<{ sku: string; old_price_minor: number; new_price_minor: number; profit_line_minor?: number }>; max_change_percent: number; }
export function validatePriceBatch(items: PriceBatchValidation["items"], maxChangePercent = 10): Promise<PriceBatchValidation> { return requestJson("/v1/review/price-batches/validate", { method: "POST", body: JSON.stringify({ items, max_change_percent: maxChangePercent }) }); }
export interface BatchExecutionResult { total: number; succeeded: number; failed: number; status: "success" | "partial_failure" | "failure"; items: Array<{ item_id: string; success: boolean; message: string }>; }
export function summarizeExecution(items: BatchExecutionResult["items"]): Promise<BatchExecutionResult> { return requestJson("/v1/review/execution-results/summarize", { method: "POST", body: JSON.stringify({ items }) }); }
export interface StoredExecutionResult { result_id: string; workspace_id: string; result: BatchExecutionResult; created_at: string; }
export function saveExecutionResult(workspaceId: string, items: BatchExecutionResult["items"]): Promise<StoredExecutionResult> { return requestJson(`/v1/review/execution-results/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "POST", body: JSON.stringify({ items }) }); }
export function listExecutionResults(workspaceId: string): Promise<StoredExecutionResult[]> { return requestJson(`/v1/review/execution-results/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }
export interface ReadbackVerification { matched: boolean; fields: Array<{ field: string; expected: string | null; actual: string | null; matched: boolean }>; message: string; }
export function verifyReadback(expected: Record<string, unknown>, actual: Record<string, unknown>): Promise<ReadbackVerification> { return requestJson("/v1/review/readback/verify", { method: "POST", body: JSON.stringify({ expected, actual }) }); }
export interface StoredReadbackVerification { verification_id: string; workspace_id: string; verification: ReadbackVerification; created_at: string; }
export function saveReadbackVerification(workspaceId: string, expected: Record<string, unknown>, actual: Record<string, unknown>): Promise<StoredReadbackVerification> { return requestJson(`/v1/review/readback/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "POST", body: JSON.stringify({ expected, actual }) }); }
export function listReadbackVerifications(workspaceId: string): Promise<StoredReadbackVerification[]> { return requestJson(`/v1/review/readback/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }
export interface AuditEvent { event_type: string; subject_id: string; detail: Record<string, unknown>; occurred_at: string; }
export function buildAuditEvent(payload: Record<string, unknown>): Promise<AuditEvent> { return requestJson("/v1/review/audit-events/build", { method: "POST", body: JSON.stringify(payload) }); }
export interface StoredAuditEvent { event_id: string; workspace_id: string; event: AuditEvent; }
export function saveAuditEvent(workspaceId: string, payload: Record<string, unknown>): Promise<StoredAuditEvent> { return requestJson(`/v1/review/audit-events/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "POST", body: JSON.stringify(payload) }); }
export function listAuditEvents(workspaceId: string): Promise<StoredAuditEvent[]> { return requestJson(`/v1/review/audit-events/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }
export interface DataProvenance { source: "official_private" | "operator_imported" | "public_sample" | "derived_estimate"; observed_at: string; explanation: string; }
export function classifyDataSource(payload: Record<string, unknown>): Promise<DataProvenance> { return requestJson("/v1/data-provenance/classify", { method: "POST", body: JSON.stringify(payload) }); }
export function classifyAndSaveDataSource(workspaceId: string, payload: Record<string, unknown>): Promise<DataProvenance> { return requestJson(`/v1/data-provenance/store-workspaces/${encodeURIComponent(workspaceId)}/classify-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listDataProvenanceHistory(workspaceId: string): Promise<DataProvenance[]> { return requestJson(`/v1/data-provenance/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface RelationshipFinding { row_index: number; rule_code: string; message: string; severity: string; }
export function checkRelationshipQuality(payload: Record<string, unknown>): Promise<RelationshipFinding[]> { return requestJson("/v1/data-quality/relationship-check", { method: "POST", body: JSON.stringify(payload) }); }
export function checkAndIsolateRelationshipQuality(workspaceId: string, payload: Record<string, unknown>): Promise<RelationshipFinding[]> { return requestJson(`/v1/data-quality/store-workspaces/${encodeURIComponent(workspaceId)}/relationship-check-and-isolate`, { method: "POST", body: JSON.stringify(payload) }); }
export interface MoneyInventoryFinding { field: string; rule_code: string; message: string; }
export function checkMoneyInventory(payload: Record<string, unknown>): Promise<MoneyInventoryFinding[]> { return requestJson("/v1/data-quality/money-inventory-check", { method: "POST", body: JSON.stringify(payload) }); }
export function checkAndIsolateMoneyInventory(workspaceId: string, payload: Record<string, unknown>): Promise<MoneyInventoryFinding[]> { return requestJson(`/v1/data-quality/store-workspaces/${encodeURIComponent(workspaceId)}/money-inventory-check-and-isolate`, { method: "POST", body: JSON.stringify(payload) }); }
export interface SourceConflict { field: string; sources: string[]; values: string[]; message: string; }
export function findSourceConflicts(payload: Record<string, unknown>): Promise<SourceConflict[]> { return requestJson("/v1/data-quality/source-conflicts", { method: "POST", body: JSON.stringify(payload) }); }
export function findAndIsolateSourceConflicts(workspaceId: string, payload: Record<string, unknown>): Promise<SourceConflict[]> { return requestJson(`/v1/data-quality/store-workspaces/${encodeURIComponent(workspaceId)}/source-conflicts-and-isolate`, { method: "POST", body: JSON.stringify(payload) }); }
export interface IsolationResult { accepted: Array<Record<string, unknown>>; isolated: Array<{ row_index: number; reason: string; record: Record<string, unknown> }>; }
export function isolateQualityRecords(payload: Record<string, unknown>): Promise<IsolationResult> { return requestJson("/v1/data-quality/isolate", { method: "POST", body: JSON.stringify(payload) }); }
export function isolateAndSaveQualityRecords(workspaceId: string, payload: Record<string, unknown>): Promise<IsolationResult> { return requestJson(`/v1/data-quality/store-workspaces/${encodeURIComponent(workspaceId)}/isolate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function compareListingVersion(payload: Record<string, unknown>): Promise<ListingVersion> { return requestJson("/v1/listing/versions/compare", { method: "POST", body: JSON.stringify(payload) }); }
export function compareAndSaveListingVersion(workspaceId: string, payload: Record<string, unknown>): Promise<ListingVersion> { return requestJson(`/v1/listing/versions/store-workspaces/${encodeURIComponent(workspaceId)}/compare-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listListingVersions(workspaceId: string): Promise<ListingVersion[]> { return requestJson(`/v1/listing/versions/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }

export interface PublishCommand { idempotency_key: string; version: number; status: "pending" | "approved" | "executed" | "partial" | "rejected"; requested_text: string; readback_text: string | null; matched: boolean; message: string; }
export function executeListingPublish(payload: Record<string, unknown>): Promise<PublishCommand> { return requestJson("/v1/listing/publish/execute", { method: "POST", body: JSON.stringify(payload) }); }
export function executeWorkspaceListingPublish(workspaceId: string, payload: Record<string, unknown>): Promise<PublishCommand> { return requestJson(`/v1/listing/publish/store-workspaces/${encodeURIComponent(workspaceId)}/execute`, { method: "POST", body: JSON.stringify(payload) }); }
export function listListingPublishes(workspaceId: string): Promise<PublishCommand[]> { return requestJson(`/v1/listing/publish/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }

export interface PerformanceToken { access_token: string; expires_at: string; refresh_token_present: boolean; credential_scope: "performance_api"; needs_refresh: boolean; }
export function inspectPerformanceToken(payload: Record<string, unknown>): Promise<PerformanceToken> { return requestJson("/v1/advertising/performance-oauth/inspect", { method: "POST", body: JSON.stringify(payload) }); }

export interface AdvertisingKeyword { keyword: string; bid_minor: number | null; negative: boolean; }
export interface AdvertisingCampaign { campaign_id: string; name: string; campaign_type: string; status: "active" | "paused" | "archived"; keywords: AdvertisingKeyword[]; source: string; }
export function previewAdvertisingCampaignSync(campaigns: Record<string, unknown>[]): Promise<AdvertisingCampaign[]> { return requestJson("/v1/advertising/campaigns/sync-preview", { method: "POST", body: JSON.stringify({ campaigns }) }); }
export function saveAdvertisingCampaignSync(workspaceId: string, campaigns: Record<string, unknown>[]): Promise<AdvertisingCampaign[]> { return requestJson(`/v1/advertising/campaigns/store-workspaces/${encodeURIComponent(workspaceId)}/sync-and-save`, { method: "POST", body: JSON.stringify({ campaigns }) }); }
export function listAdvertisingCampaigns(workspaceId: string): Promise<AdvertisingCampaign[]> { return requestJson(`/v1/advertising/campaigns/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }
export interface AdvertisingReportRow { campaign_id: string; report_date: string; impressions: number; clicks: number; orders: number; sales_minor: number; spend_minor: number; currency: string; source: string; }
export function previewAdvertisingReportSync(rows: Record<string, unknown>[]): Promise<AdvertisingReportRow[]> { return requestJson("/v1/advertising/reports/sync-preview", { method: "POST", body: JSON.stringify({ rows }) }); }
export function saveAdvertisingReportSync(workspaceId: string, rows: Record<string, unknown>[]): Promise<AdvertisingReportRow[]> { return requestJson(`/v1/advertising/reports/store-workspaces/${encodeURIComponent(workspaceId)}/sync-and-save`, { method: "POST", body: JSON.stringify({ rows }) }); }
export function listAdvertisingReports(workspaceId: string): Promise<AdvertisingReportRow[]> { return requestJson(`/v1/advertising/reports/store-workspaces/${encodeURIComponent(workspaceId)}`, { method: "GET" }); }
export interface AdvertisingMetrics { acos_percent: number | null; tacos_percent: number | null; cpc_minor: number | null; ctr_percent: number | null; cvr_percent: number | null; roi_percent: number | null; currency: string; window: string; complete: boolean; formulas: Record<string, string>; }
export function calculateAdvertisingMetrics(payload: Record<string, unknown>): Promise<AdvertisingMetrics> { return requestJson("/v1/advertising/metrics/calculate", { method: "POST", body: JSON.stringify(payload) }); }
export function calculateAndSaveAdvertisingMetrics(workspaceId: string, payload: Record<string, unknown>): Promise<AdvertisingMetrics> { return requestJson(`/v1/advertising/metrics/store-workspaces/${encodeURIComponent(workspaceId)}/calculate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listAdvertisingMetricSnapshots(workspaceId: string): Promise<AdvertisingMetrics[]> { return requestJson(`/v1/advertising/metrics/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface AdvertisingKeywordDiagnosis { keyword: string; category: "star" | "high_cvr" | "potential" | "high_spend_no_conversion"; impressions: number; clicks: number; orders: number; spend_minor: number; sales_minor: number; ctr_percent: number | null; cvr_percent: number | null; acos_percent: number | null; reason: string; read_only: boolean; }
export function diagnoseAdvertisingKeywords(payload: Record<string, unknown>): Promise<AdvertisingKeywordDiagnosis[]> { return requestJson("/v1/advertising/keywords/diagnose", { method: "POST", body: JSON.stringify(payload) }); }
export function diagnoseAndSaveAdvertisingKeywords(workspaceId: string, payload: Record<string, unknown>): Promise<AdvertisingKeywordDiagnosis[]> { return requestJson(`/v1/advertising/keywords/store-workspaces/${encodeURIComponent(workspaceId)}/diagnose-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listAdvertisingKeywordReports(workspaceId: string): Promise<AdvertisingKeywordDiagnosis[][]> { return requestJson(`/v1/advertising/keywords/store-workspaces/${encodeURIComponent(workspaceId)}/reports`, { method: "GET" }); }
export interface AdvertisingThresholds { version: number; min_impressions: number; min_clicks: number; high_cvr_percent: number; high_spend_minor: number; }
export function validateAdvertisingThresholds(payload: Record<string, unknown>): Promise<AdvertisingThresholds> { return requestJson("/v1/advertising/thresholds/validate", { method: "POST", body: JSON.stringify(payload) }); }
export function validateAndSaveAdvertisingThresholds(workspaceId: string, payload: Record<string, unknown>): Promise<AdvertisingThresholds> { return requestJson(`/v1/advertising/thresholds/store-workspaces/${encodeURIComponent(workspaceId)}/validate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listAdvertisingThresholdVersions(workspaceId: string): Promise<AdvertisingThresholds[]> { return requestJson(`/v1/advertising/thresholds/store-workspaces/${encodeURIComponent(workspaceId)}/versions`, { method: "GET" }); }
export interface AdvertisingCalendarDay { day: number; date: string; phase: "testing" | "filtering" | "scaling" | "optimizing"; recommendation: string; read_only: boolean; }
export function buildAdvertisingCalendar(start_date: string): Promise<AdvertisingCalendarDay[]> { return requestJson("/v1/advertising/calendar/build", { method: "POST", body: JSON.stringify({ start_date }) }); }
export interface ErpSupplyRecord { external_id: string; offer_id: string; record_type: "purchase" | "inbound" | "cost"; quantity: number; amount_minor: number | null; currency: string | null; expected_date: string | null; source: string; }
export function previewErpCsv(content: string): Promise<ErpSupplyRecord[]> { return requestJson("/v1/erp/csv/preview", { method: "POST", body: JSON.stringify({ content }) }); }
export function buildAndSaveAdvertisingCalendar(workspaceId: string, start_date: string): Promise<AdvertisingCalendarDay[]> { return requestJson(`/v1/advertising/calendar/store-workspaces/${encodeURIComponent(workspaceId)}/build-and-save`, { method: "POST", body: JSON.stringify({ start_date }) }); }
export function listAdvertisingCalendarHistory(workspaceId: string): Promise<AdvertisingCalendarDay[][]> { return requestJson(`/v1/advertising/calendar/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface AdvertisingReadOnlyDecision { action: string; allowed: boolean; reason: string; audit_required: boolean; }
export function checkAdvertisingBoundary(action: string): Promise<AdvertisingReadOnlyDecision> { return requestJson("/v1/advertising/boundary/check", { method: "POST", body: JSON.stringify({ action }) }); }
export function checkAndSaveAdvertisingBoundary(workspaceId: string, action: string): Promise<AdvertisingReadOnlyDecision> { return requestJson(`/v1/advertising/boundary/store-workspaces/${encodeURIComponent(workspaceId)}/check-and-save`, { method: "POST", body: JSON.stringify({ action }) }); }
export function listAdvertisingBoundaryHistory(workspaceId: string): Promise<AdvertisingReadOnlyDecision[]> { return requestJson(`/v1/advertising/boundary/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface ModelAdapterConfig { adapter: string; provider: string; model: string; base_url: string | null; enabled: boolean; credential_configured: boolean; }
export function inspectModelAdapter(payload: Record<string, unknown>): Promise<ModelAdapterConfig> { return requestJson("/v1/model-adapters/inspect", { method: "POST", body: JSON.stringify(payload) }); }
export function inspectAndSaveModelAdapter(workspaceId: string, payload: Record<string, unknown>): Promise<ModelAdapterConfig> { return requestJson(`/v1/model-adapters/store-workspaces/${encodeURIComponent(workspaceId)}/inspect-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listModelAdapterConfigs(workspaceId: string): Promise<ModelAdapterConfig[]> { return requestJson(`/v1/model-adapters/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export function getActiveModelAdapter(workspaceId: string): Promise<ModelAdapterConfig | null> { return requestJson(`/v1/model-adapters/store-workspaces/${encodeURIComponent(workspaceId)}/active`, { method: "GET" }); }
export interface ReadonlyToolDecision { tool: string; allowed: boolean; parameters: Record<string, string>; reason: string; sql_allowed: boolean; }
export function authorizeReadonlyTool(tool: string, parameters: Record<string, unknown>): Promise<ReadonlyToolDecision> { return requestJson("/v1/assistant/tools/authorize", { method: "POST", body: JSON.stringify({ tool, parameters }) }); }
export function authorizeAndSaveReadonlyTool(workspaceId: string, tool: string, parameters: Record<string, unknown>): Promise<ReadonlyToolDecision> { return requestJson(`/v1/assistant/tools/store-workspaces/${encodeURIComponent(workspaceId)}/authorize-and-save`, { method: "POST", body: JSON.stringify({ tool, parameters }) }); }
export function listReadonlyToolHistory(workspaceId: string): Promise<ReadonlyToolDecision[]> { return requestJson(`/v1/assistant/tools/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface SalesAnalysis { current_sales_minor: number; previous_sales_minor: number; change_percent: number | null; current_orders: number; previous_orders: number; order_change_percent: number | null; anomalies: string[]; opportunities: string[]; incomplete: boolean; read_only: boolean; }
export function analyzeSales(payload: Record<string, unknown>): Promise<SalesAnalysis> { return requestJson("/v1/analysis/sales/analyze", { method: "POST", body: JSON.stringify(payload) }); }
export function analyzeAndSaveSales(workspaceId: string, payload: Record<string, unknown>): Promise<SalesAnalysis> { return requestJson(`/v1/analysis/sales/store-workspaces/${encodeURIComponent(workspaceId)}/analyze-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listSalesAnalysisReports(workspaceId: string): Promise<SalesAnalysis[]> { return requestJson(`/v1/analysis/sales/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface InventoryAnalysis { available_units: number; inbound_units: number; average_daily_sales: number; days_of_cover: number | null; stockout_risk: boolean; overstock_risk: boolean; recommendations: string[]; incomplete: boolean; read_only: boolean; }
export function analyzeInventory(payload: Record<string, unknown>): Promise<InventoryAnalysis> { return requestJson("/v1/analysis/inventory/analyze", { method: "POST", body: JSON.stringify(payload) }); }
export function analyzeAndSaveInventory(workspaceId: string, payload: Record<string, unknown>): Promise<InventoryAnalysis> { return requestJson(`/v1/analysis/inventory/store-workspaces/${encodeURIComponent(workspaceId)}/analyze-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listInventoryAnalysisReports(workspaceId: string): Promise<InventoryAnalysis[]> { return requestJson(`/v1/analysis/inventory/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface AdvertisingAnalysis { acos_percent: number | null; tacos_percent: number | null; roi_percent: number | null; anomalies: string[]; recommendations: string[]; incomplete: boolean; read_only: boolean; }
export function analyzeAdvertising(payload: Record<string, unknown>): Promise<AdvertisingAnalysis> { return requestJson("/v1/analysis/advertising/analyze", { method: "POST", body: JSON.stringify(payload) }); }
export function analyzeAndSaveAdvertising(workspaceId: string, payload: Record<string, unknown>): Promise<AdvertisingAnalysis> { return requestJson(`/v1/analysis/advertising/store-workspaces/${encodeURIComponent(workspaceId)}/analyze-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listAdvertisingAnalysisReports(workspaceId: string): Promise<AdvertisingAnalysis[]> { return requestJson(`/v1/analysis/advertising/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface CompetitorSelectionAnalysis { sample_count: number; opportunity_count: number; estimated: boolean; caveat: string; highlights: string[]; recommendations: string[]; read_only: boolean; }
export function analyzeCompetitorSelection(payload: Record<string, unknown>): Promise<CompetitorSelectionAnalysis> { return requestJson("/v1/analysis/competitor-selection/analyze", { method: "POST", body: JSON.stringify(payload) }); }
export function analyzeAndSaveCompetitorSelection(workspaceId: string, payload: Record<string, unknown>): Promise<CompetitorSelectionAnalysis> { return requestJson(`/v1/analysis/competitor-selection/store-workspaces/${encodeURIComponent(workspaceId)}/analyze-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listCompetitorSelectionReports(workspaceId: string): Promise<CompetitorSelectionAnalysis[]> { return requestJson(`/v1/analysis/competitor-selection/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface SummaryReport { report_type: "daily" | "weekly" | "monthly"; period: string; headline: string; metric_lines: string[]; anomalies: string[]; todos: string[]; read_only: boolean; }
export function buildSummaryReport(payload: Record<string, unknown>): Promise<SummaryReport> { return requestJson("/v1/reports/summary", { method: "POST", body: JSON.stringify(payload) }); }
export function buildAndSaveSummaryReport(workspaceId: string, payload: Record<string, unknown>): Promise<SummaryReport> { return requestJson(`/v1/reports/store-workspaces/${encodeURIComponent(workspaceId)}/summary-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listSummaryReports(workspaceId: string): Promise<SummaryReport[]> { return requestJson(`/v1/reports/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface AgentTrigger { trigger_type: "scheduled" | "event" | "manual"; target: string; schedule: string | null; event_name: string | null; enabled: boolean; read_only: boolean; }
export function validateAgentTrigger(payload: Record<string, unknown>): Promise<AgentTrigger> { return requestJson("/v1/agent-triggers/validate", { method: "POST", body: JSON.stringify(payload) }); }
export function validateAndSaveAgentTrigger(workspaceId: string, payload: Record<string, unknown>): Promise<AgentTrigger> { return requestJson(`/v1/agent-triggers/store-workspaces/${encodeURIComponent(workspaceId)}/validate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listAgentTriggers(workspaceId: string): Promise<AgentTrigger[]> { return requestJson(`/v1/agent-triggers/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface AgentPermissionDecision { agent: string; allowed_capabilities: string[]; denied_capabilities: string[]; sql_access: boolean; credential_access: boolean; external_write_access: boolean; read_only: boolean; }
export function checkAgentPermissions(agent: string, requested_capabilities: string[]): Promise<AgentPermissionDecision> { return requestJson("/v1/agents/permissions/check", { method: "POST", body: JSON.stringify({ agent, requested_capabilities }) }); }
export function checkAndSaveAgentPermissions(workspaceId: string, agent: string, requested_capabilities: string[]): Promise<AgentPermissionDecision> { return requestJson(`/v1/agents/permissions/store-workspaces/${encodeURIComponent(workspaceId)}/check-and-save`, { method: "POST", body: JSON.stringify({ agent, requested_capabilities }) }); }
export function listAgentPermissionHistory(workspaceId: string): Promise<AgentPermissionDecision[]> { return requestJson(`/v1/agents/permissions/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface ExternalNotificationConfig { channel: "feishu" | "dingtalk" | "wechat_work" | "email"; enabled: boolean; template: string; retry_limit: number; sensitive_data_allowed: boolean; preview_only: boolean; }
export function validateExternalNotification(payload: Record<string, unknown>): Promise<ExternalNotificationConfig> { return requestJson("/v1/notifications/validate", { method: "POST", body: JSON.stringify(payload) }); }
export function previewExternalNotification(template: string, values: Record<string, unknown>): Promise<string> { return requestJson("/v1/notifications/preview", { method: "POST", body: JSON.stringify({ template, values }) }); }
export function validateAndSaveExternalNotification(workspaceId: string, payload: Record<string, unknown>): Promise<ExternalNotificationConfig> { return requestJson(`/v1/notifications/store-workspaces/${encodeURIComponent(workspaceId)}/validate-and-save`, { method: "POST", body: JSON.stringify(payload) }); }
export function listExternalNotificationConfigs(workspaceId: string): Promise<ExternalNotificationConfig[]> { return requestJson(`/v1/notifications/store-workspaces/${encodeURIComponent(workspaceId)}/history`, { method: "GET" }); }
export interface PerformanceCredentialStatus { credential_scope: string; client_id_present: boolean; access_token_present: boolean; refresh_token_present: boolean; expires_at: string | null; isolated_from_seller: boolean; ready: boolean; }
export function inspectPerformanceCredentials(payload: Record<string, unknown>): Promise<PerformanceCredentialStatus> { return requestJson("/v1/performance/credentials/inspect", { method: "POST", body: JSON.stringify(payload) }); }
export function savePerformanceCredentials(workspaceId: string, payload: Record<string, unknown>): Promise<PerformanceCredentialStatus> { return requestJson(`/v1/advertising/performance-oauth/store-workspaces/${encodeURIComponent(workspaceId)}/credentials`, { method: "POST", body: JSON.stringify(payload) }); }
export function getPerformanceCredentialStatus(workspaceId: string): Promise<PerformanceCredentialStatus> { return requestJson(`/v1/advertising/performance-oauth/store-workspaces/${encodeURIComponent(workspaceId)}/credentials`, { method: "GET" }); }
export function savePerformanceClientCredentials(workspaceId: string, payload: Record<string, unknown>): Promise<PerformanceCredentialStatus> { return requestJson(`/v1/advertising/performance-oauth/store-workspaces/${encodeURIComponent(workspaceId)}/client-credentials`, { method: "POST", body: JSON.stringify(payload) }); }
export function requestPerformanceToken(workspaceId: string): Promise<PerformanceCredentialStatus> { return requestJson(`/v1/advertising/performance-oauth/store-workspaces/${encodeURIComponent(workspaceId)}/token`, { method: "POST" }); }
export function fetchPerformanceCampaigns(workspaceId: string): Promise<Record<string, unknown>> { return requestJson(`/v1/advertising/performance-oauth/store-workspaces/${encodeURIComponent(workspaceId)}/campaigns`, { method: "GET" }); }
export interface SellerProductSyncItem { offer_id: string; ozon_product_id: string | null; name: string; price_minor: number; currency: string; available_stock: number; source: string; }
export interface SellerProductSyncPreview { items: SellerProductSyncItem[]; total: number; next_cursor: string | null; source: string; credentials_required: boolean; dry_run: boolean; }
export function previewSellerProductSync(response: Record<string, unknown>, cursor?: string): Promise<SellerProductSyncPreview> { return requestJson("/v1/seller/products/sync-preview", { method: "POST", body: JSON.stringify({ response, cursor }) }); }
export function saveSellerProductSync(workspaceId: string, response: Record<string, unknown>, cursor?: string): Promise<SellerProductSyncPreview> { return requestJson(`/v1/seller/products/store-workspaces/${encodeURIComponent(workspaceId)}/sync-and-save`, { method: "POST", body: JSON.stringify({ response, cursor }) }); }
export function listSellerProductSnapshots(workspaceId: string): Promise<SellerProductSyncPreview[]> { return requestJson(`/v1/seller/products/store-workspaces/${encodeURIComponent(workspaceId)}/snapshots`, { method: "GET" }); }
export interface SellerStockSyncItem { offer_id: string; warehouse_id: string; available_quantity: number; reserved_quantity: number; source: string; }
export interface SellerStockSyncPreview { items: SellerStockSyncItem[]; total: number; next_cursor: string | null; source: string; credentials_required: boolean; dry_run: boolean; }
export function previewSellerStockSync(response: Record<string, unknown>): Promise<SellerStockSyncPreview> { return requestJson("/v1/seller/stock/sync-preview", { method: "POST", body: JSON.stringify({ response }) }); }
export function saveSellerStockSync(workspaceId: string, response: Record<string, unknown>): Promise<SellerStockSyncPreview> { return requestJson(`/v1/seller/stock/store-workspaces/${encodeURIComponent(workspaceId)}/sync-and-save`, { method: "POST", body: JSON.stringify({ response }) }); }
export function listSellerStockSnapshots(workspaceId: string): Promise<SellerStockSyncPreview[]> { return requestJson(`/v1/seller/stock/store-workspaces/${encodeURIComponent(workspaceId)}/snapshots`, { method: "GET" }); }
export interface SellerOrderSyncItem { order_id: string; ordered_at: string; status: string; total_amount_minor: number; currency: string; item_count: number; source: string; }
export interface SellerOrderSyncPreview { items: SellerOrderSyncItem[]; total: number; next_cursor: string | null; source: string; credentials_required: boolean; dry_run: boolean; }
export function previewSellerOrderSync(response: Record<string, unknown>): Promise<SellerOrderSyncPreview> { return requestJson("/v1/seller/orders/sync-preview", { method: "POST", body: JSON.stringify({ response }) }); }
export function saveSellerOrderSync(workspaceId: string, response: Record<string, unknown>): Promise<SellerOrderSyncPreview> { return requestJson(`/v1/seller/orders/store-workspaces/${encodeURIComponent(workspaceId)}/sync-and-save`, { method: "POST", body: JSON.stringify({ response }) }); }
export function listSellerOrderSnapshots(workspaceId: string): Promise<SellerOrderSyncPreview[]> { return requestJson(`/v1/seller/orders/store-workspaces/${encodeURIComponent(workspaceId)}/snapshots`, { method: "GET" }); }
export interface SellerFulfillmentSyncItem { posting_id: string; fulfillment_type: "FBO" | "FBS"; status: string; shipment_date: string | null; item_count: number; total_quantity: number; source: string; }
export interface SellerFulfillmentSyncPreview { items: SellerFulfillmentSyncItem[]; total: number; next_cursor: string | null; source: string; credentials_required: boolean; dry_run: boolean; }
export function previewSellerFulfillmentSync(response: Record<string, unknown>): Promise<SellerFulfillmentSyncPreview> { return requestJson("/v1/seller/fulfillment/sync-preview", { method: "POST", body: JSON.stringify({ response }) }); }
export function saveSellerFulfillmentSync(workspaceId: string, response: Record<string, unknown>): Promise<SellerFulfillmentSyncPreview> { return requestJson(`/v1/seller/fulfillment/store-workspaces/${encodeURIComponent(workspaceId)}/sync-and-save`, { method: "POST", body: JSON.stringify({ response }) }); }
export function listSellerFulfillmentSnapshots(workspaceId: string): Promise<SellerFulfillmentSyncPreview[]> { return requestJson(`/v1/seller/fulfillment/store-workspaces/${encodeURIComponent(workspaceId)}/snapshots`, { method: "GET" }); }
export interface SyncProcessorPlan { resource_type: string; initial_cursor: string | null; max_pages: number; max_retries: number; dry_run: boolean; watermark_policy: string; }
export function buildSyncProcessorPlan(payload: Record<string, unknown>): Promise<SyncProcessorPlan> { return requestJson("/v1/sync-processor/plan", { method: "POST", body: JSON.stringify(payload) }); }
export interface DataSourceLabel { source: "official_private" | "operator_imported" | "public_sample" | "derived_estimate"; label: string; estimated: boolean; description: string; }
export function labelDataSource(source: string): Promise<DataSourceLabel> { return requestJson("/v1/data-sources/label", { method: "POST", body: JSON.stringify({ source }) }); }
export interface QualitySchemaFinding { row_index: number; field: string; rule_code: string; value: string | null; message: string; severity: string; }
export interface QualitySchemaResult { valid: boolean; checked_rows: number; findings: QualitySchemaFinding[]; isolated_required: boolean; }
export function checkQualitySchema(payload: Record<string, unknown>): Promise<QualitySchemaResult> { return requestJson("/v1/data-quality/schema-check", { method: "POST", body: JSON.stringify(payload) }); }
export function checkAndIsolateQualitySchema(workspaceId: string, payload: Record<string, unknown>): Promise<QualitySchemaResult> { return requestJson(`/v1/data-quality/store-workspaces/${encodeURIComponent(workspaceId)}/schema-check-and-isolate`, { method: "POST", body: JSON.stringify(payload) }); }

export function queryKnowledge(question: string): Promise<KnowledgeAnswer> {
  return requestJson("/v1/knowledge-answers/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function listKnowledgeSources(): Promise<KnowledgeSource[]> {
  return requestJson("/v1/knowledge-sources", { method: "GET" });
}

export function createKnowledgeSource(payload: {
  title: string;
  source_type: string;
  business_domain: string;
  source_locator: string;
}): Promise<KnowledgeSource> {
  return requestJson("/v1/knowledge-sources", {
    method: "POST", body: JSON.stringify(payload),
  });
}

export function listKnowledgeVersions(sourceId: string): Promise<KnowledgeVersion[]> {
  return requestJson(`/v1/knowledge-sources/${encodeURIComponent(sourceId)}/versions`, { method: "GET" });
}
export function createKnowledgeVersion(sourceId: string, payload: { content_hash: string; parser_name: string; parser_version: string; cleaner_version: string }): Promise<KnowledgeVersion> {
  return requestJson(`/v1/knowledge-sources/${encodeURIComponent(sourceId)}/versions`, { method: "POST", body: JSON.stringify(payload) });
}
export function publishKnowledgeVersion(versionId: string): Promise<KnowledgeVersion> { return requestJson(`/v1/knowledge-sources/versions/${encodeURIComponent(versionId)}/publish`, { method: "POST" }); }
export function withdrawKnowledgeVersion(versionId: string): Promise<KnowledgeVersion> { return requestJson(`/v1/knowledge-sources/versions/${encodeURIComponent(versionId)}/withdraw`, { method: "POST" }); }
export function rebuildKnowledgeVersion(versionId: string): Promise<{ task_id: string; status: string; document_version_id: string }> { return requestJson(`/v1/knowledge-sources/versions/${encodeURIComponent(versionId)}/rebuild`, { method: "POST" }); }
export function withdrawKnowledgeSource(sourceId: string): Promise<KnowledgeSource> { return requestJson(`/v1/knowledge-sources/${encodeURIComponent(sourceId)}/withdraw`, { method: "POST" }); }
export function pauseKnowledgeSource(sourceId: string): Promise<KnowledgeSource> { return requestJson(`/v1/knowledge-sources/${encodeURIComponent(sourceId)}/pause`, { method: "POST" }); }
export function resumeKnowledgeSource(sourceId: string): Promise<KnowledgeSource> { return requestJson(`/v1/knowledge-sources/${encodeURIComponent(sourceId)}/resume`, { method: "POST" }); }
export function deleteKnowledgeSource(sourceId: string): Promise<KnowledgeSource> { return requestJson(`/v1/knowledge-sources/${encodeURIComponent(sourceId)}`, { method: "DELETE" }); }
export function previewKnowledgeIngestion(payload: Record<string, unknown>): Promise<KnowledgeIngestionResult> {
  return requestJson("/v1/knowledge-ingestion/run", { method: "POST", body: JSON.stringify(payload) });
}
export interface KnowledgePdfUploadResult {
  upload_id: string;
  status: string;
  byte_size: number;
  page_count: number | null;
  structural_safety_status: string;
  malware_scan_status: string;
  blocked_reason: string | null;
}
export function uploadKnowledgePdf(payload: { filename: string; mime_type: string; content_base64: string }): Promise<KnowledgePdfUploadResult> {
  return requestJson("/v1/knowledge-pdf-uploads", { method: "POST", body: JSON.stringify(payload) });
}
export interface KnowledgePdfExtractResult { upload_id: string; status: string; page_count: number; extracted_characters: number; text: string; blocked_reason: string | null; }
export function extractKnowledgePdfText(uploadId: string): Promise<KnowledgePdfExtractResult> { return requestJson(`/v1/knowledge-pdf-uploads/${encodeURIComponent(uploadId)}/extract-text`, { method: "POST" }); }
export interface KnowledgeTask { task_id: string; task_type: string; organization_id: string; status: "queued" | "running" | "succeeded" | "failed" | "cancelled"; attempt: number; error_code: string | null; }
export function listKnowledgeTasks(): Promise<KnowledgeTask[]> { return requestJson("/v1/knowledge-tasks", { method: "GET" }); }
export function cancelKnowledgeTask(taskId: string): Promise<KnowledgeTask> { return requestJson(`/v1/knowledge-tasks/${encodeURIComponent(taskId)}/cancel`, { method: "POST" }); }
export function retryKnowledgeTask(taskId: string): Promise<KnowledgeTask> { return requestJson(`/v1/knowledge-tasks/${encodeURIComponent(taskId)}/retry`, { method: "POST" }); }

export function submitKnowledgeFeedback(answerId: string, reason: string, note?: string): Promise<{ feedback_id: string; status: string }> {
  return requestJson(`/v1/knowledge-answers/${encodeURIComponent(answerId)}/feedback`, {
    method: "POST", body: JSON.stringify({ reason, note }),
  });
}

export interface RagEvaluationCase {
  case_id: string;
  question: string;
  expected_status: string;
  expected_sources: string[];
  safety_tags: string[];
  status: "draft" | "confirmed" | "rejected";
}
export interface RagEvaluationBatchConfirmResult { confirmed_count: number; confirmed_case_ids: string[]; }
export interface RagEvaluationRun {
  run_id: string; status: string; suite: "quick" | "standard" | "full";
  target_count: number; confirmed_count: number; case_ids: string[]; gate_status: "ready" | "blocked";
}
export function listRagEvaluationCases(): Promise<RagEvaluationCase[]> {
  return requestJson("/v1/rag-evaluation/cases", { method: "GET" });
}
export function confirmRagEvaluationCase(caseId: string, reviewer: string): Promise<RagEvaluationCase> {
  return requestJson(`/v1/rag-evaluation/cases/${encodeURIComponent(caseId)}/confirm`, {
    method: "POST", body: JSON.stringify({ reviewer }),
  });
}
export function confirmRagEvaluationCasesBatch(caseIds: string[], reviewer: string): Promise<RagEvaluationBatchConfirmResult> {
  return requestJson("/v1/rag-evaluation/cases/confirm-batch", {
    method: "POST", body: JSON.stringify({ case_ids: caseIds, reviewer }),
  });
}
export function startRagEvaluation(suite: RagEvaluationRun["suite"]): Promise<RagEvaluationRun> {
  return requestJson("/v1/rag-evaluation/runs", { method: "POST", body: JSON.stringify({ suite }) });
}

export function listModelBudgets(): Promise<ModelBudget[]> {
  return requestJson("/v1/model-budgets", { method: "GET" });
}

export function saveModelBudget(providerId: string, payload: {
  daily_token_limit: number;
  monthly_token_limit: number;
  daily_request_limit: number;
  monthly_budget: number;
  budget_currency: "RMB";
  purpose: string;
}): Promise<ModelBudget> {
  return requestJson(`/v1/model-budgets/${encodeURIComponent(providerId)}`, {
    method: "PUT", body: JSON.stringify(payload),
  });
}

/** 供应商适配器名称可扩展，不能把示例供应商固化为有限枚举。 */
export type RagModelAdapter = string;
export type RagModelPurpose = "embedding" | "translation" | "intent_rewrite" | "rerank" | "answer_generation";
export interface RagModelProvider {
  provider_id: string; name: string; adapter_type: RagModelAdapter; model: string; base_url: string;
  model_kind: "embedding" | "rerank" | "text"; priority: number; enabled: boolean; credential_configured: boolean; credential_mask: string;
}
export interface RagModelBinding { purpose: RagModelPurpose; primary_provider_id: string; fallback_provider_ids: string[]; revision: number; }
export interface RagModelCatalog { embedding: Array<Record<string, string>>; translation: Array<Record<string, string>>; }
export function getRagModelCatalog(): Promise<RagModelCatalog> { return requestJson("/v1/model-providers/managed/catalog", { method: "GET" }); }
export function listRagModelProviders(): Promise<RagModelProvider[]> { return requestJson("/v1/model-providers/managed", { method: "GET" }); }
export function createRagModelProvider(payload: Record<string, unknown>): Promise<RagModelProvider> { return requestJson("/v1/model-providers/managed", { method: "POST", body: JSON.stringify(payload) }); }
export interface RagModelConnectivityResult { ok: boolean; status: "reachable" | "quota_exceeded" | "failed"; message: string; model: string; external_request_sent: boolean; endpoint_host: string; http_status: number | null; }
export function testRagModelConnectivity(payload: Record<string, unknown>): Promise<RagModelConnectivityResult> { return requestJson("/v1/model-providers/managed/test", { method: "POST", body: JSON.stringify(payload) }); }
export function updateRagModelProvider(providerId: string, payload: Record<string, unknown>): Promise<RagModelProvider> { return requestJson(`/v1/model-providers/managed/${encodeURIComponent(providerId)}`, { method: "PUT", body: JSON.stringify(payload) }); }
export function disableRagModelProvider(providerId: string): Promise<RagModelProvider> { return requestJson(`/v1/model-providers/managed/${encodeURIComponent(providerId)}/disable`, { method: "POST" }); }
export function enableRagModelProvider(providerId: string, payload: Record<string, unknown>): Promise<RagModelProvider> { return updateRagModelProvider(providerId, { ...payload, enabled: true }); }
export function deleteRagModelProvider(providerId: string): Promise<void> { return requestJson(`/v1/model-providers/managed/${encodeURIComponent(providerId)}`, { method: "DELETE" }); }
export function listRagModelBindings(): Promise<RagModelBinding[]> { return requestJson("/v1/model-providers/managed/bindings", { method: "GET" }); }
export function bindRagModelPurpose(purpose: RagModelPurpose, payload: { primary_provider_id: string; fallback_provider_ids: string[] }): Promise<RagModelBinding> { return requestJson(`/v1/model-providers/managed/bindings/${encodeURIComponent(purpose)}`, { method: "PUT", body: JSON.stringify(payload) }); }
