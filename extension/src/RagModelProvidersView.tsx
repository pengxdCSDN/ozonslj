import {
  ArrowsClockwise,
  CaretDown,
  CheckCircle,
  Check,
  FloppyDisk,
  Key,
  PencilSimple,
  Plus,
  ShieldCheck,
  Trash,
  WarningCircle,
  XCircle,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  bindRagModelPurpose,
  createRagModelProvider,
  deleteRagModelProvider,
  listRagModelBindings,
  listRagModelProviders,
  testRagModelConnectivity,
  updateRagModelProvider,
  type RagModelAdapter,
  type RagModelBinding,
  type RagModelProvider,
  type RagModelPurpose,
} from "./api";

type ModelKind = "embedding" | "text";
type FormState = {
  name: string;
  adapter_type: RagModelAdapter;
  model: string;
  base_url: string;
  api_key: string;
  priority: string;
  model_kind: ModelKind;
};

const EMPTY_FORM: FormState = {
  name: "",
  adapter_type: "openai-compatible",
  model: "",
  base_url: "",
  api_key: "",
  priority: "100",
  model_kind: "embedding",
};

const TEXT_PURPOSES: Array<{ key: RagModelPurpose; label: string }> = [
  { key: "translation", label: "俄语 → 中文翻译" },
  { key: "intent_rewrite", label: "查询重写 / 意图识别" },
  { key: "rerank", label: "重排序精排" },
  { key: "answer_generation", label: "答案生成" },
];

const ADAPTER_OPTIONS: Array<{ value: RagModelAdapter | "custom"; label: string }> = [
  { value: "openai-compatible", label: "OpenAI 兼容" },
  { value: "dashscope", label: "阿里云百炼" },
  { value: "siliconflow", label: "SiliconFlow" },
  { value: "zhipu", label: "智谱 AI" },
  { value: "custom", label: "自定义协议" },
];

export function RagModelProvidersView() {
  const [providers, setProviders] = useState<RagModelProvider[]>([]);
  const [bindings, setBindings] = useState<RagModelBinding[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [testingConnectivity, setTestingConnectivity] = useState(false);
  const [message, setMessage] = useState("先新增模型配置，再按优先级生成自动降级链。");
  const [connectivityState, setConnectivityState] = useState<"idle" | "success" | "error">("idle");
  const [customAdapter, setCustomAdapter] = useState(false);
  const [adapterMenuOpen, setAdapterMenuOpen] = useState(false);
  const adapterMenuRef = useRef<HTMLDivElement>(null);

  const refresh = async () => {
    setBusy(true);
    setConnectivityState("idle");
    try {
      const [nextProviders, nextBindings] = await Promise.all([
        listRagModelProviders(),
        listRagModelBindings(),
      ]);
      setProviders(nextProviders);
      setBindings(nextBindings);
      setMessage(nextProviders.length ? "配置已刷新。优先级数字越小，越优先使用。" : "还没有模型配置，请从上方新增。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型配置加载失败");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  useEffect(() => {
    if (!adapterMenuOpen) return;
    const closeMenu = (event: MouseEvent) => {
      if (adapterMenuRef.current && !adapterMenuRef.current.contains(event.target as Node)) {
        setAdapterMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, [adapterMenuOpen]);

  const updateForm = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setCustomAdapter(false);
  };

  const submit = async () => {
    if (!form.name.trim() || !form.adapter_type.trim() || !form.model.trim() || !form.base_url.trim()) {
      setMessage("请填写供应商名称、调用协议、Model 和 Base URL。");
      return;
    }
    if (!editingId && !form.api_key.trim()) {
      setMessage("新增配置必须填写 API Key；编辑时留空表示保留原 Key。");
      return;
    }
    setBusy(true);
    setConnectivityState("idle");
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        adapter_type: form.adapter_type.trim(),
        model: form.model.trim(),
        base_url: form.base_url.trim(),
        model_kind: form.model_kind,
        priority: Number(form.priority),
      };
      if (form.api_key.trim()) payload.api_key = form.api_key.trim();
      if (editingId) {
        await updateRagModelProvider(editingId, payload);
        setMessage("模型配置已更新。");
      } else {
        await createRagModelProvider({ ...payload, api_key: form.api_key.trim() });
        setMessage("模型配置已新增。请在下方生成用途路由。");
      }
      resetForm();
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型配置保存失败");
      setBusy(false);
    }
  };

  const editProvider = (provider: RagModelProvider) => {
    setEditingId(provider.provider_id);
    setForm({
      name: provider.name,
      adapter_type: provider.adapter_type,
      model: provider.model,
      base_url: provider.base_url,
      api_key: "",
      priority: String(provider.priority),
      model_kind: provider.model_kind,
    });
    setCustomAdapter(!["openai-compatible", "dashscope", "siliconflow", "zhipu"].includes(provider.adapter_type));
    setMessage("正在编辑；API Key 留空会保留服务端已有凭据。");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const toggleProvider = async (provider: RagModelProvider) => {
    setBusy(true);
    setConnectivityState("idle");
    try {
      await updateRagModelProvider(provider.provider_id, {
        name: provider.name,
        adapter_type: provider.adapter_type,
        model: provider.model,
        base_url: provider.base_url,
        model_kind: provider.model_kind,
        priority: provider.priority,
        enabled: !provider.enabled,
      });
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型状态更新失败");
      setBusy(false);
    }
  };

  const removeProvider = async (provider: RagModelProvider) => {
    if (!window.confirm(`确定删除“${provider.name} / ${provider.model}”吗？`)) return;
    setBusy(true);
    setConnectivityState("idle");
    try {
      await deleteRagModelProvider(provider.provider_id);
      await refresh();
      setMessage("模型配置已删除。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型删除失败；已绑定用途请先重新生成路由。");
      setBusy(false);
    }
  };

  const testConnectivity = async () => {
    const missingFields = [
      !form.adapter_type.trim() ? "调用协议" : "",
      !form.model.trim() ? "Model" : "",
      !form.base_url.trim() ? "Base URL" : "",
      !editingId && !form.api_key.trim() ? "API Key" : "",
    ].filter(Boolean);
    if (missingFields.length) {
      setConnectivityState("error");
      setMessage(`测试连接未执行：请填写${missingFields.join("、")}。`);
      return;
    }
    let parsedUrl: URL;
    try {
      parsedUrl = new URL(form.base_url.trim());
    } catch {
      setConnectivityState("error");
      setMessage("测试连接未执行：Base URL 不是合法地址，请填写 https:// 开头的接口根地址。");
      return;
    }
    if (!['https:', 'http:'].includes(parsedUrl.protocol) || (parsedUrl.protocol === 'http:' && !['localhost', '127.0.0.1'].includes(parsedUrl.hostname))) {
      setConnectivityState("error");
      setMessage("测试连接未执行：Base URL 必须使用 HTTPS 地址。");
      return;
    }
    setBusy(true);
    setConnectivityState("idle");
    setTestingConnectivity(true);
    try {
      const result = await testRagModelConnectivity({
        purpose: form.model_kind === "embedding" ? "embedding" : "translation",
        adapter_type: form.adapter_type,
        model: form.model,
        base_url: form.base_url,
        ...(form.api_key.trim() ? { api_key: form.api_key.trim() } : {}),
        ...(editingId ? { provider_id: editingId } : {}),
      });
      setConnectivityState(result.ok ? "success" : "error");
      setMessage(`${result.ok ? "连接成功" : "连接失败"}：${result.message} · 外部请求${result.external_request_sent ? "已发出" : "未发出"} · ${result.endpoint_host}${result.http_status ? ` · HTTP ${result.http_status}` : ""}`);
    } catch (error) {
      setConnectivityState("error");
      setMessage(error instanceof Error ? error.message : "模型连接测试失败");
    } finally {
      setTestingConnectivity(false);
      setBusy(false);
    }
  };

  const saveAutomaticRoute = async (purpose: RagModelPurpose, kind: ModelKind) => {
    const candidates = providers
      .filter((provider) => provider.enabled && provider.model_kind === kind)
      .sort((left, right) => left.priority - right.priority || left.provider_id.localeCompare(right.provider_id));
    if (!candidates.length) {
      setMessage(`${kind === "embedding" ? "向量" : "文本"}模型池没有启用的候选。`);
      return;
    }
    setBusy(true);
    setConnectivityState("idle");
    try {
      await bindRagModelPurpose(purpose, {
        primary_provider_id: candidates[0].provider_id,
        fallback_provider_ids: candidates.slice(1).map((provider) => provider.provider_id),
      });
      await refresh();
      setMessage(`${purposeLabel(purpose)} 已生成 ${candidates.length} 级自动降级链。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "自动降级链保存失败");
      setBusy(false);
    }
  };

  const embeddingProviders = useMemo(() => sortedProviders(providers, "embedding"), [providers]);
  const textProviders = useMemo(() => sortedProviders(providers, "text"), [providers]);

  return (
    <div className="view-content model-pool-view">
      <section className="page-heading model-pool-heading">
        <div>
          <span className="eyebrow">系统工具 / RAG-025</span>
          <h1>模型供应商与自动降级</h1>
          <p>分别维护向量模型与文本模型。额度耗尽、超时或供应商不可用时，系统按优先级自动切换。</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => void refresh()} disabled={busy}>
          <ArrowsClockwise size={16} /> 刷新配置
        </button>
      </section>

      <div
        className={`model-pool-callout${connectivityState === "success" ? " is-success" : connectivityState === "error" ? " is-error" : ""}`}
        role={connectivityState === "error" ? "alert" : "status"}
        aria-live="polite"
      >
        {connectivityState === "success" ? <CheckCircle size={17} /> : connectivityState === "error" ? <WarningCircle size={17} /> : <ShieldCheck size={17} />}
        <span>{message}</span>
      </div>

      <section className="panel model-form-panel">
        <div className="section-heading model-form-heading">
          <div><span className="eyebrow">配置入口</span><h2>{editingId ? "编辑模型配置" : "新增模型配置"}</h2></div>
        </div>
        <div className="model-form-grid">
          <label><span>模型类型</span><select value={form.model_kind} onChange={(event) => updateForm("model_kind", event.target.value as ModelKind)}><option value="embedding">向量模型 · Embedding</option><option value="text">文本模型 · 翻译 / Agent</option></select></label>
          <label><span>供应商名称</span><input value={form.name} onChange={(event) => updateForm("name", event.target.value)} placeholder="例如：阿里云百炼 / SiliconFlow" /></label>
          <label><span>调用协议</span><div className="soft-select" ref={adapterMenuRef}><button className="soft-select-trigger" type="button" aria-haspopup="listbox" aria-expanded={adapterMenuOpen} onClick={() => setAdapterMenuOpen((current) => !current)}><span>{customAdapter ? "自定义协议" : ADAPTER_OPTIONS.find((option) => option.value === form.adapter_type)?.label ?? form.adapter_type}</span><CaretDown size={16} /></button>{adapterMenuOpen ? <div className="soft-select-menu" role="listbox">{ADAPTER_OPTIONS.map((option) => { const selected = option.value === (customAdapter ? "custom" : form.adapter_type); return <button className="soft-select-option" type="button" role="option" aria-selected={selected} key={option.value} onClick={() => { setAdapterMenuOpen(false); setCustomAdapter(option.value === "custom"); if (option.value !== "custom") updateForm("adapter_type", option.value); }}><span>{option.label}</span>{selected ? <Check className="soft-select-check" size={15} weight="bold" /> : null}</button>; })}</div> : null}</div>{customAdapter ? <input value={form.adapter_type === "openai-compatible" ? "" : form.adapter_type} onChange={(event) => updateForm("adapter_type", event.target.value)} placeholder="输入协议标识" required /> : null}</label>
          <label className="model-field"><span>Model <em>必填</em></span><input value={form.model} onChange={(event) => updateForm("model", event.target.value)} placeholder="text-embedding-v4 / Qwen/Qwen2.5-7B-Instruct" /></label>
          <label className="url-field"><span>Base URL <em>必填</em></span><input value={form.base_url} onChange={(event) => updateForm("base_url", event.target.value)} placeholder="https://api.example.com/v1" /></label>
          <label><span>API Key <em>仅提交服务端</em></span><input type="password" autoComplete="new-password" value={form.api_key} onChange={(event) => updateForm("api_key", event.target.value)} placeholder={editingId ? "留空表示保留原 Key" : "不会回显到浏览器"} /></label>
          <label className="priority-field"><span>优先级 <em>数字越小越优先</em></span><input type="number" min="1" max="1000" value={form.priority} onChange={(event) => updateForm("priority", event.target.value)} /></label>
        </div>
        <div className="model-form-actions">
          <button className="secondary-button model-action-button" type="button" disabled={busy} onClick={() => void testConnectivity()}><ArrowsClockwise size={16} /> {testingConnectivity ? "测试中…" : "测试连接"}</button>
          {editingId && <button className="secondary-button model-action-button" type="button" disabled={busy} onClick={resetForm}>取消编辑</button>}
          <button className="primary-button model-action-button model-add-button" type="button" disabled={busy} onClick={() => void submit()}>{editingId ? <FloppyDisk size={17} /> : <Plus size={17} />}{editingId ? "保存修改" : "新增模型配置"}</button>
        </div>
      </section>

      <ProviderPool title="向量模型池" eyebrow="Embedding / 向量检索" providers={embeddingProviders} busy={busy} onEdit={editProvider} onToggle={(provider) => void toggleProvider(provider)} onDelete={(provider) => void removeProvider(provider)} />
      <ProviderPool title="文本模型池" eyebrow="翻译 / 意图 / 重排 / 答案" providers={textProviders} busy={busy} onEdit={editProvider} onToggle={(provider) => void toggleProvider(provider)} onDelete={(provider) => void removeProvider(provider)} />

      <section className="panel route-panel">
        <div className="section-heading"><div><span className="eyebrow">用途路由</span><h2>按优先级生成自动降级链</h2></div><ShieldCheck size={22} /></div>
        <div className="route-list">
          <RouteCard label="向量化 / Embedding" providers={embeddingProviders} binding={bindings.find((item) => item.purpose === "embedding")} disabled={busy} onSave={() => void saveAutomaticRoute("embedding", "embedding")} />
          {TEXT_PURPOSES.map(({ key, label }) => <RouteCard key={key} label={label} providers={textProviders} binding={bindings.find((item) => item.purpose === key)} disabled={busy} onSave={() => void saveAutomaticRoute(key, "text")} />)}
        </div>
      </section>
    </div>
  );
}

function sortedProviders(providers: RagModelProvider[], kind: ModelKind) {
  return providers.filter((provider) => provider.model_kind === kind).sort((left, right) => left.priority - right.priority || left.provider_id.localeCompare(right.provider_id));
}

function purposeLabel(purpose: RagModelPurpose) {
  return purpose === "embedding" ? "向量化" : TEXT_PURPOSES.find((item) => item.key === purpose)?.label ?? purpose;
}

function ProviderPool({ title, eyebrow, providers, busy, onEdit, onToggle, onDelete }: { title: string; eyebrow: string; providers: RagModelProvider[]; busy: boolean; onEdit: (provider: RagModelProvider) => void; onToggle: (provider: RagModelProvider) => void; onDelete: (provider: RagModelProvider) => void }) {
  return <section className="panel provider-pool-panel"><div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div><span className="pool-count">{providers.length} 个配置</span></div>{providers.length ? <div className="provider-table">{providers.map((provider, index) => <div className={`provider-card ${provider.enabled ? "" : "is-disabled"}`} key={provider.provider_id}><div className="priority-mark">{String(index + 1).padStart(2, "0")}</div><div className="provider-main"><div className="provider-title"><strong>{provider.name}</strong><span className={provider.enabled ? "status-on" : "status-off"}>{provider.enabled ? "启用" : "停用"}</span></div><div className="provider-model">{provider.model}</div><div className="provider-meta"><span>{provider.adapter_type}</span><span>{provider.base_url}</span><span>{provider.credential_configured ? `API Key ${provider.credential_mask}` : "未配置 API Key"}</span></div></div><div className="provider-priority"><small>优先级</small><strong>{provider.priority}</strong></div><div className="provider-actions"><button className="text-button" type="button" disabled={busy} onClick={() => onEdit(provider)}><PencilSimple size={15} /> 编辑</button><button className="text-button" type="button" disabled={busy} onClick={() => onToggle(provider)}>{provider.enabled ? <XCircle size={15} /> : <CheckCircle size={15} />}{provider.enabled ? "停用" : "启用"}</button><button className="text-button danger-button" type="button" disabled={busy} onClick={() => onDelete(provider)}><Trash size={15} /> 删除</button></div></div>)}</div> : <div className="empty-search"><WarningCircle size={21} /><strong>暂无{title}配置</strong><span>使用上方“新增模型配置”填写 API Key、Base URL 和 Model。</span></div>}</section>;
}

function RouteCard({ label, providers, binding, disabled, onSave }: { label: string; providers: RagModelProvider[]; binding?: RagModelBinding; disabled: boolean; onSave: () => void }) {
  return <div className="route-card"><div className="route-icon"><ShieldCheck size={18} /></div><div className="route-copy"><strong>{label}</strong><small>{providers.length ? `候选链：${providers.map((provider) => `${provider.priority} · ${provider.name}`).join("  →  ")}` : "暂无启用的候选模型"}</small><small className={binding ? "route-ready" : "route-muted"}>{binding ? `已绑定 ${binding.fallback_provider_ids.length + 1} 个模型` : "尚未生成用途路由"}</small></div><button className="secondary-button" type="button" disabled={disabled || !providers.length} onClick={onSave}><ShieldCheck size={15} /> 生成降级链</button></div>;
}
