import { ArrowsClockwise, CheckCircle, Key, PencilSimple, Plus, ShieldCheck, Trash, XCircle } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
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
  adapter_type: "",
  model: "",
  base_url: "",
  api_key: "",
  priority: "100",
  model_kind: "text",
};

const TEXT_PURPOSES: Array<{ key: RagModelPurpose; label: string }> = [
  { key: "translation", label: "俄语 → 中文翻译" },
  { key: "intent_rewrite", label: "查询重写 / 意图识别" },
  { key: "rerank", label: "重排序精排" },
  { key: "answer_generation", label: "答案生成" },
];

export function RagModelProvidersView() {
  const [providers, setProviders] = useState<RagModelProvider[]>([]);
  const [bindings, setBindings] = useState<RagModelBinding[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState("配置模型后，系统会按优先级自动选择并在失败时降级。");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    try {
      const [nextProviders, nextBindings] = await Promise.all([
        listRagModelProviders(),
        listRagModelBindings(),
      ]);
      setProviders(nextProviders);
      setBindings(nextBindings);
      setMessage("模型配置已刷新。优先级数值越小越高，系统会自动跳过不可用供应商。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型配置加载失败");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const updateForm = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const submit = async () => {
    if (!form.name.trim() || !form.adapter_type.trim() || !form.model.trim() || !form.base_url.trim()) {
      setMessage("请填写供应商名称、适配器、模型 ID 和 Base URL。");
      return;
    }
    if (!editingId && !form.api_key.trim()) {
      setMessage("首次添加供应商必须填写 API Key；更新时留空表示保留原凭据。");
      return;
    }
    setBusy(true);
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
        setMessage("模型配置已新增。请在用途路由中生成自动降级链。");
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
    setMessage("正在编辑模型；API Key 留空将保留服务端原凭据。");
  };

  const toggleProvider = async (provider: RagModelProvider) => {
    setBusy(true);
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
    setBusy(true);
    try {
      await deleteRagModelProvider(provider.provider_id);
      await refresh();
      setMessage("模型配置已删除。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型删除失败；已绑定用途的模型需要先重新生成路由。");
      setBusy(false);
    }
  };

  const testConnectivity = async () => {
    if (!form.model.trim() || !form.base_url.trim() || !form.api_key.trim()) {
      setMessage("测试连接前请填写模型 ID、Base URL 和 API Key。");
      return;
    }
    setBusy(true);
    try {
      const result = await testRagModelConnectivity({
        purpose: form.model_kind === "embedding" ? "embedding" : "translation",
        adapter_type: form.adapter_type,
        model: form.model,
        base_url: form.base_url,
        api_key: form.api_key,
      });
      setMessage(result.ok ? `连接成功：${result.message}` : `连接失败：${result.message}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型连接测试失败");
    } finally {
      setBusy(false);
    }
  };

  const saveAutomaticRoute = async (purpose: RagModelPurpose, kind: ModelKind) => {
    const candidates = providers
      .filter((provider) => provider.enabled && provider.model_kind === kind)
      .sort((left, right) => left.priority - right.priority || left.provider_id.localeCompare(right.provider_id));
    if (!candidates.length) {
      setMessage(`${kind === "embedding" ? "向量" : "文本"}模型池还没有可用供应商。`);
      return;
    }
    setBusy(true);
    try {
      await bindRagModelPurpose(purpose, {
        primary_provider_id: candidates[0].provider_id,
        fallback_provider_ids: candidates.slice(1).map((provider) => provider.provider_id),
      });
      await refresh();
      setMessage(`${purposeLabel(purpose)} 已按优先级生成自动降级链，共 ${candidates.length} 个候选。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "自动降级链保存失败");
      setBusy(false);
    }
  };

  const embeddingProviders = useMemo(() => sortedProviders(providers, "embedding"), [providers]);
  const textProviders = useMemo(() => sortedProviders(providers, "text"), [providers]);

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <span className="eyebrow">系统工具 / RAG-025</span>
          <h1>模型池与自动降级</h1>
          <p>向量模型与文本模型分开维护。优先使用数字更小的配置；遇到限额、超时、网络异常或供应商不可用时，自动切换到下一优先级。</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => void refresh()} disabled={busy}>
          <ArrowsClockwise size={16} />刷新
        </button>
      </section>
      <p className="form-message" role="status">{message}</p>

      <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">供应商配置</span><h2>{editingId ? "编辑模型配置" : "新增模型配置"}</h2></div><Key size={22} /></div>
        <div className="form-grid">
          <label>模型类型<select value={form.model_kind} onChange={(event) => updateForm("model_kind", event.target.value as ModelKind)}><option value="embedding">向量模型（Embedding）</option><option value="text">文本模型（翻译 / Agent）</option></select></label>
          <label>供应商名称<input value={form.name} onChange={(event) => updateForm("name", event.target.value)} placeholder="例如：我的云端模型供应商" /></label>
          <label>适配器<input value={form.adapter_type} onChange={(event) => updateForm("adapter_type", event.target.value)} placeholder="例如：openai-compatible" /></label>
          <label>模型 ID<input value={form.model} onChange={(event) => updateForm("model", event.target.value)} placeholder="按供应商文档填写，不限固定示例" /></label>
          <label>Base URL<input value={form.base_url} onChange={(event) => updateForm("base_url", event.target.value)} placeholder="https://api.example.com/v1" /></label>
          <label>API Key（仅提交到服务端）<input type="password" autoComplete="new-password" value={form.api_key} onChange={(event) => updateForm("api_key", event.target.value)} placeholder={editingId ? "留空表示保留原凭据" : "不会回显到浏览器"} /></label>
          <label>优先级（1 最高）<input type="number" min="1" max="1000" value={form.priority} onChange={(event) => updateForm("priority", event.target.value)} /></label>
        </div>
        <div className="button-row">
          <button className="secondary-button" type="button" disabled={busy} onClick={() => void testConnectivity()}><ArrowsClockwise size={17} />测试连接</button>
          <button className="primary-button" type="button" disabled={busy} onClick={() => void submit()}>{editingId ? <PencilSimple size={17} /> : <Plus size={17} />}{editingId ? "保存修改" : "新增模型"}</button>
          {editingId && <button className="text-button" type="button" disabled={busy} onClick={resetForm}>取消编辑</button>}
        </div>
      </section>

      <ProviderPool title="向量模型池" eyebrow="Embedding / 向量检索" providers={embeddingProviders} busy={busy} onEdit={editProvider} onToggle={(provider) => void toggleProvider(provider)} onDelete={(provider) => void removeProvider(provider)} />
      <ProviderPool title="文本模型池" eyebrow="翻译 / 意图 / 重排 / 答案" providers={textProviders} busy={busy} onEdit={editProvider} onToggle={(provider) => void toggleProvider(provider)} onDelete={(provider) => void removeProvider(provider)} />

      <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">用途路由</span><h2>按优先级生成自动降级链</h2></div><ShieldCheck size={22} /></div>
        <div className="route-list">
          <RouteCard purpose="embedding" label="向量化 / Embedding" providers={embeddingProviders} binding={bindings.find((item) => item.purpose === "embedding")} disabled={busy} onSave={() => void saveAutomaticRoute("embedding", "embedding")} />
          {TEXT_PURPOSES.map(({ key, label }) => <RouteCard key={key} purpose={key} label={label} providers={textProviders} binding={bindings.find((item) => item.purpose === key)} disabled={busy} onSave={() => void saveAutomaticRoute(key, "text")} />)}
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
  return <section className="panel"><div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div><Key size={22} /></div>{providers.length ? providers.map((provider) => <div className="operation-row" key={provider.provider_id}><span><strong>优先级 {provider.priority} · {provider.name} · {provider.model}</strong><small>{provider.adapter_type} · {provider.base_url} · {provider.credential_configured ? `已配置 ${provider.credential_mask}` : "未配置 API Key"}</small></span><em>{provider.enabled ? "可用" : "已停用"}</em><button className="text-button" type="button" disabled={busy} onClick={() => onEdit(provider)}><PencilSimple size={15} />编辑</button><button className="text-button" type="button" disabled={busy} onClick={() => onToggle(provider)}>{provider.enabled ? <XCircle size={15} /> : <CheckCircle size={15} />}{provider.enabled ? "停用" : "启用"}</button><button className="text-button" type="button" disabled={busy} onClick={() => onDelete(provider)}><Trash size={15} />删除</button></div>) : <div className="empty-search"><strong>暂无模型配置</strong><span>通过上方表单新增，不受示例供应商或固定模型限制。</span></div>}</section>;
}

function RouteCard({ label, purpose, providers, binding, disabled, onSave }: { label: string; purpose: RagModelPurpose; providers: RagModelProvider[]; binding?: RagModelBinding; disabled: boolean; onSave: () => void }) {
  return <div className="operation-row route-row"><span><strong>{label}</strong><small>{providers.length ? `当前候选：${providers.map((provider) => `${provider.priority} · ${provider.name}`).join(" → ")}` : "暂无启用的候选模型"}{binding ? `；已绑定 ${binding.fallback_provider_ids.length + 1} 个模型` : "；尚未生成用途路由"}</small></span><button className="secondary-button" type="button" disabled={disabled || !providers.length} onClick={onSave}><ShieldCheck size={15} />按优先级保存</button></div>;
}
