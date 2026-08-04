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

export interface StoreWorkspace {
  id: string;
  name: string;
  seller_display_name: string;
  seller_status: "pending" | "active" | "invalid" | "disabled";
}

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "supervisor" | "operator" | "finance" | "readonly_analyst";
  workspace_ids: string[];
}

export type SyncJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "partial"
  | "failed"
  | "cancelled";

export interface SyncJob {
  id: string;
  workspace_id: string;
  resource_type: "products" | "stocks" | "orders" | "postings" | "all";
  sync_mode: "initial" | "incremental" | "reconcile";
  status: SyncJobStatus;
  created_at: string;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
}

interface StoreWorkspaceList {
  items: StoreWorkspace[];
}

interface LoginResponse extends CurrentUser {
  session_token?: string;
}

const API_BASE_URL =
  globalThis.location.protocol === "chrome-extension:"
    ? (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000")
    : "/api";
const SELECTED_WORKSPACE_KEY = "selectedWorkspaceId";
const SESSION_TOKEN_KEY = "sessionToken";

function createRequestId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  const bytes = new Uint8Array(16);
  if (typeof globalThis.crypto?.getRandomValues === "function") {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex
    .slice(6, 8)
    .join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}

async function getSessionToken(): Promise<string | null> {
  if (typeof chrome !== "undefined" && chrome.storage?.session) {
    const result = await chrome.storage.session.get(SESSION_TOKEN_KEY);
    return typeof result[SESSION_TOKEN_KEY] === "string" ? result[SESSION_TOKEN_KEY] : null;
  }
  return sessionStorage.getItem(SESSION_TOKEN_KEY);
}

async function setSessionToken(token: string | null): Promise<void> {
  if (typeof chrome !== "undefined" && chrome.storage?.session) {
    if (token === null) await chrome.storage.session.remove(SESSION_TOKEN_KEY);
    else await chrome.storage.session.set({ [SESSION_TOKEN_KEY]: token });
    return;
  }
  if (token === null) sessionStorage.removeItem(SESSION_TOKEN_KEY);
  else sessionStorage.setItem(SESSION_TOKEN_KEY, token);
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const sessionToken = await getSessionToken();
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "X-Request-Id": createRequestId(),
      ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
      ...init.headers
    }
  });
}

export async function login(email: string, password: string): Promise<CurrentUser> {
  const response = await apiFetch("/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (response.status === 401) throw new Error("邮箱或密码错误");
  if (!response.ok) throw new Error(`登录失败，状态码 ${response.status}`);
  const result = (await response.json()) as LoginResponse;
  if (result.session_token) await setSessionToken(result.session_token);
  const { session_token: _sessionToken, ...user } = result;
  return user;
}

export async function fetchCurrentUser(signal?: AbortSignal): Promise<CurrentUser | null> {
  const response = await apiFetch("/v1/auth/me", { signal });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`登录状态检查失败，状态码 ${response.status}`);
  return (await response.json()) as CurrentUser;
}

export async function logout(): Promise<void> {
  try {
    const response = await apiFetch("/v1/auth/logout", { method: "POST" });
    if (!response.ok) throw new Error(`退出失败，状态码 ${response.status}`);
  } finally {
    await setSessionToken(null);
  }
}

export async function fetchStoreWorkspaces(
  signal?: AbortSignal
): Promise<StoreWorkspace[]> {
  const response = await apiFetch("/v1/store-workspaces", { signal });

  if (!response.ok) {
    throw new Error(`工作区请求失败，状态码 ${response.status}`);
  }

  return ((await response.json()) as StoreWorkspaceList).items;
}

export async function fetchProductOffers(
  workspaceId: string,
  signal?: AbortSignal
): Promise<ProductOfferPage> {
  const response = await apiFetch(
    `/v1/store-workspaces/${encodeURIComponent(workspaceId)}/product-offers?limit=20`,
    { signal }
  );

  if (!response.ok) {
    throw new Error(`商品数据请求失败，状态码 ${response.status}`);
  }

  return (await response.json()) as ProductOfferPage;
}

export async function createSyncJob(
  workspaceId: string,
  signal?: AbortSignal
): Promise<SyncJob> {
  const response = await apiFetch(
    `/v1/store-workspaces/${encodeURIComponent(workspaceId)}/sync-jobs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resource_type: "products", sync_mode: "incremental" }),
      signal
    }
  );
  if (response.status === 409) throw new Error("当前店铺已有同步任务正在执行");
  if (!response.ok) throw new Error(`同步任务创建失败，状态码 ${response.status}`);
  return (await response.json()) as SyncJob;
}

export async function fetchSyncJob(jobId: string, signal?: AbortSignal): Promise<SyncJob> {
  const response = await apiFetch(`/v1/sync-jobs/${encodeURIComponent(jobId)}`, { signal });
  if (!response.ok) throw new Error(`同步状态查询失败，状态码 ${response.status}`);
  return (await response.json()) as SyncJob;
}

export async function getSelectedWorkspaceId(): Promise<string | null> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    const result = await chrome.storage.local.get(SELECTED_WORKSPACE_KEY);
    const value = result[SELECTED_WORKSPACE_KEY];
    return typeof value === "string" ? value : null;
  }
  return localStorage.getItem(SELECTED_WORKSPACE_KEY);
}

export async function setSelectedWorkspaceId(workspaceId: string): Promise<void> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    await chrome.storage.local.set({ [SELECTED_WORKSPACE_KEY]: workspaceId });
    return;
  }
  localStorage.setItem(SELECTED_WORKSPACE_KEY, workspaceId);
}
