import {
  ArrowClockwise,
  ArrowRight,
  CaretDown,
  ChartLineUp,
  CheckCircle,
  Cube,
  MagnifyingGlass,
  Package,
  SlidersHorizontal,
  Storefront,
  WarningCircle
} from "@phosphor-icons/react";
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";

import {
  fetchCurrentUser,
  fetchProductOffers,
  fetchStoreWorkspaces,
  getSelectedWorkspaceId,
  login,
  logout,
  setSelectedWorkspaceId,
  type CurrentUser,
  type ProductOffer,
  type ProductOfferPage,
  type StoreWorkspace
} from "./api";

type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "authenticated"; user: CurrentUser }
  | { status: "error"; message: string };

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: ProductOfferPage }
  | { status: "error"; message: string };
type View = "overview" | "products";
type StockFilter = "all" | "available" | "risk" | "empty";

const LOW_STOCK_THRESHOLD = 15;

function formatPrice(value: string, currency: string): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(Number(value));
}

function stockState(stock: number): { label: string; className: string } {
  if (stock === 0) return { label: "缺货", className: "danger" };
  if (stock <= LOW_STOCK_THRESHOLD) return { label: "低库存", className: "warning" };
  return { label: "库存正常", className: "success" };
}

function ProductRow({ offer }: { offer: ProductOffer }) {
  const status = stockState(offer.available_stock);
  return (
    <article className="product-row">
      <div className="product-visual" aria-hidden>
        <Package size={21} weight="duotone" />
      </div>
      <div className="product-identity">
        <h3>{offer.name}</h3>
        <p>{offer.offer_id}</p>
      </div>
      <div className="product-price">
        <span>售价</span>
        <strong>{formatPrice(offer.price, offer.currency)}</strong>
      </div>
      <div className="product-stock">
        <span className={`status-pill ${status.className}`}>{status.label}</span>
        <strong>{offer.available_stock}</strong>
      </div>
      <button className="row-action" type="button" aria-label={`查看 ${offer.name}`}>
        <ArrowRight size={17} weight="bold" />
      </button>
    </article>
  );
}

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

export function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [view, setView] = useState<View>("overview");
  const [query, setQuery] = useState("");
  const [stockFilter, setStockFilter] = useState<StockFilter>("all");
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);
  const [workspaces, setWorkspaces] = useState<StoreWorkspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspace] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    const controller = new AbortController();
    void fetchCurrentUser(controller.signal)
      .then((user) => setAuth(user ? { status: "authenticated", user } : { status: "anonymous" }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setAuth({
          status: "error",
          message: error instanceof Error ? error.message : "无法检查登录状态"
        });
      });
    return () => controller.abort();
  }, []);

  const loadOffers = useCallback(async (workspaceId: string, signal?: AbortSignal) => {
    setState({ status: "loading" });
    try {
      const data = await fetchProductOffers(workspaceId, signal);
      setState({ status: "ready", data });
      setLastSyncedAt(new Date());
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "无法加载商品数据"
      });
    }
  }, []);

  useEffect(() => {
    if (auth.status !== "authenticated") return;
    const controller = new AbortController();
    async function initializeWorkspace(): Promise<void> {
      try {
        const [availableWorkspaces, persistedWorkspaceId] = await Promise.all([
          fetchStoreWorkspaces(controller.signal),
          getSelectedWorkspaceId()
        ]);
        if (availableWorkspaces.length === 0) {
          setState({ status: "error", message: "尚未配置可用的店铺工作区" });
          return;
        }
        setWorkspaces(availableWorkspaces);
        const initialWorkspace =
          availableWorkspaces.find(({ id }) => id === persistedWorkspaceId) ??
          availableWorkspaces[0];
        setSelectedWorkspace(initialWorkspace.id);
        await setSelectedWorkspaceId(initialWorkspace.id);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "无法加载店铺工作区"
        });
      }
    }
    void initializeWorkspace();
    return () => controller.abort();
  }, [auth.status]);

  useEffect(() => {
    if (selectedWorkspaceId === null) return;
    const controller = new AbortController();
    void loadOffers(selectedWorkspaceId, controller.signal);
    return () => controller.abort();
  }, [loadOffers, selectedWorkspaceId]);

  const offers = state.status === "ready" ? state.data.items : [];
  const selectedWorkspace = workspaces.find(({ id }) => id === selectedWorkspaceId);
  const metrics = useMemo(() => {
    let stock = 0;
    let risk = 0;
    let empty = 0;
    let value = 0;
    for (const offer of offers) {
      stock += offer.available_stock;
      value += Number(offer.price) * offer.available_stock;
      if (offer.available_stock === 0) empty += 1;
      else if (offer.available_stock <= LOW_STOCK_THRESHOLD) risk += 1;
    }
    return { stock, risk, empty, value };
  }, [offers]);

  const filteredOffers = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLocaleLowerCase();
    return offers.filter((offer) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        offer.name.toLocaleLowerCase().includes(normalizedQuery) ||
        offer.offer_id.toLocaleLowerCase().includes(normalizedQuery);
      const matchesStock =
        stockFilter === "all" ||
        (stockFilter === "available" && offer.available_stock > LOW_STOCK_THRESHOLD) ||
        (stockFilter === "risk" &&
          offer.available_stock > 0 &&
          offer.available_stock <= LOW_STOCK_THRESHOLD) ||
        (stockFilter === "empty" && offer.available_stock === 0);
      return matchesQuery && matchesStock;
    });
  }, [deferredQuery, offers, stockFilter]);

  if (auth.status === "loading") {
    return <main className="login-shell"><div className="auth-loading">正在检查登录状态…</div></main>;
  }
  if (auth.status === "anonymous") {
    return <LoginPanel onAuthenticated={(user) => setAuth({ status: "authenticated", user })} />;
  }
  if (auth.status === "error") {
    return (
      <main className="login-shell">
        <section className="login-card"><h1>暂时无法连接服务</h1><p className="login-error">{auth.message}</p></section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="masthead">
        <div className="brand-mark" aria-hidden>O</div>
        <div className="brand-copy">
          <span>Ozon 跨境运营</span>
          <strong>本地控制台</strong>
        </div>
        <label className="workspace-switcher">
          <span className="online-dot" aria-hidden />
          <span className="sr-only">当前店铺工作区</span>
          <select
            aria-label="当前店铺工作区"
            value={selectedWorkspaceId ?? ""}
            onChange={(event) => {
              const workspaceId = event.target.value;
              setSelectedWorkspace(workspaceId);
              void setSelectedWorkspaceId(workspaceId);
            }}
          >
            {workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
            ))}
          </select>
          <CaretDown size={13} weight="bold" aria-hidden />
        </label>
        <button
          className="logout-button"
          type="button"
          title={`退出 ${auth.user.display_name}`}
          onClick={async () => {
            await logout();
            setAuth({ status: "anonymous" });
          }}
        >退出</button>
      </header>

      <section className="route-strip" aria-label="店铺连接状态">
        <div className="route-node active"><Storefront size={14} weight="fill" /><span>{selectedWorkspace?.name ?? "正在加载工作区"}</span></div>
        <span className="route-line" aria-hidden />
        <div className="route-node active"><CheckCircle size={14} weight="fill" /><span>PostgreSQL 已连接</span></div>
        <span className={`route-line ${metrics.empty > 0 ? "alert" : ""}`} aria-hidden />
        <div className={`route-node ${metrics.empty > 0 ? "alert" : "active"}`}>
          <WarningCircle size={14} weight="fill" />
          <span>{metrics.empty > 0 ? `${metrics.empty} 项缺货` : "库存健康"}</span>
        </div>
      </section>

      <nav className="view-tabs" aria-label="主要功能">
        <button type="button" className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}>
          经营概览
        </button>
        <button type="button" className={view === "products" ? "active" : ""} onClick={() => setView("products")}>
          商品与库存
          {metrics.empty > 0 ? <span>{metrics.empty}</span> : null}
        </button>
      </nav>

      {state.status === "loading" ? (
        <section className="loading-grid" aria-label="正在加载运营数据">
          <div className="hero-skeleton" /><div className="metric-skeleton" /><div className="list-skeleton" />
        </section>
      ) : null}

      {state.status === "error" ? (
        <section className="state-panel">
          <WarningCircle aria-hidden size={28} weight="duotone" />
          <h2>本地服务未连接</h2>
          <p>{state.message}</p>
          <button
            className="primary-button"
            type="button"
            disabled={selectedWorkspaceId === null}
            onClick={() => {
              if (selectedWorkspaceId !== null) void loadOffers(selectedWorkspaceId);
            }}
          >
            重新连接
          </button>
        </section>
      ) : null}

      {state.status === "ready" && view === "overview" ? (
        <div className="view-content">
          <section className="command-hero">
            <div>
              <p className="eyebrow">今日运营简报</p>
              <h1>库存正在流动，<br /><em>{metrics.empty + metrics.risk} 项</em>需要关注。</h1>
              <p className="hero-note">
                数据来自 PostgreSQL。最后同步：
                {lastSyncedAt ? lastSyncedAt.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "尚未同步"}
              </p>
            </div>
            <button className="sync-button" type="button" onClick={() => void loadOffers(selectedWorkspaceId!)}>
              <ArrowClockwise size={16} weight="bold" />同步数据
            </button>
          </section>

          <section className="metric-rail" aria-label="经营指标">
            <article><span className="metric-icon blue"><Cube size={17} weight="duotone" /></span><p>在库总量</p><strong>{metrics.stock}</strong><small>件可售库存</small></article>
            <article><span className="metric-icon orange"><WarningCircle size={17} weight="duotone" /></span><p>库存风险</p><strong>{metrics.risk + metrics.empty}</strong><small>项需要补货</small></article>
            <article><span className="metric-icon cyan"><ChartLineUp size={17} weight="duotone" /></span><p>库存货值</p><strong>{Math.round(metrics.value / 1000)}k</strong><small>卢布估算</small></article>
          </section>

          <section className="section-block">
            <div className="section-heading">
              <div><p className="eyebrow">库存信号</p><h2>优先处理</h2></div>
              <button className="text-button" type="button" onClick={() => setView("products")}>查看全部 <ArrowRight size={14} weight="bold" /></button>
            </div>
            <div className="priority-list">
              {offers.filter((offer) => offer.available_stock <= LOW_STOCK_THRESHOLD).map((offer) => <ProductRow offer={offer} key={offer.offer_id} />)}
              {metrics.risk + metrics.empty === 0 ? <div className="healthy-state"><CheckCircle size={22} weight="duotone" />当前没有需要处理的库存风险</div> : null}
            </div>
          </section>
        </div>
      ) : null}

      {state.status === "ready" && view === "products" ? (
        <div className="view-content">
          <section className="products-header">
            <div><p className="eyebrow">商品目录</p><h1>商品与库存</h1><p>快速定位缺货和低库存商品。</p></div>
            <button className="square-button" type="button" onClick={() => void loadOffers(selectedWorkspaceId!)} aria-label="刷新商品"><ArrowClockwise size={17} weight="bold" /></button>
          </section>
          <div className="toolbar">
            <label className="search-field">
              <MagnifyingGlass size={17} aria-hidden /><span className="sr-only">搜索商品</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索商品名称或报价编号" />
            </label>
            <div className="filter-control">
              <SlidersHorizontal size={16} aria-hidden />
              <select aria-label="库存筛选" value={stockFilter} onChange={(event) => setStockFilter(event.target.value as StockFilter)}>
                <option value="all">全部库存</option><option value="available">库存正常</option><option value="risk">低库存</option><option value="empty">缺货</option>
              </select>
              <CaretDown size={12} aria-hidden />
            </div>
          </div>
          <section className="catalog-summary" aria-live="polite"><span>显示 {filteredOffers.length} 个商品</span><span>{query ? `关键词“${query}”` : "全部商品"}</span></section>
          <section className="product-table" aria-label="商品列表">
            <div className="table-head" aria-hidden><span>商品</span><span>售价</span><span>库存</span><span /></div>
            {filteredOffers.map((offer) => <ProductRow offer={offer} key={offer.offer_id} />)}
            {filteredOffers.length === 0 ? <div className="empty-search"><MagnifyingGlass size={22} /><strong>没有匹配的商品</strong><span>更换关键词或库存条件后重试。</span></div> : null}
          </section>
        </div>
      ) : null}
    </main>
  );
}
