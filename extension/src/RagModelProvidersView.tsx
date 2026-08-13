import { ArrowsClockwise, Key, ShieldCheck, Trash } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import {
  bindRagModelPurpose,
  createRagModelProvider,
  disableRagModelProvider,
  getRagModelCatalog,
  listRagModelBindings,
  listRagModelProviders,
  testRagModelConnectivity,
  type RagModelAdapter,
  type RagModelBinding,
  type RagModelCatalog,
  type RagModelProvider,
  type RagModelPurpose,
} from "./api";

const PURPOSES: Array<{ key: RagModelPurpose; label: string }> = [
  { key: "embedding", label: "Embedding 向量化" },
  { key: "translation", label: "俄语 → 中文翻译" },
];

const EMPTY_FORM = {
  name: "",
  adapter_type: "siliconflow" as RagModelAdapter,
  model: "",
  base_url: "",
  api_key: "",
  priority: "100",
  purpose: "translation" as "embedding" | "translation",
};

export function RagModelProvidersView() {
  const [providers, setProviders] = useState<RagModelProvider[]>([]);
  const [bindings, setBindings] = useState<RagModelBinding[]>([]);
  const [catalog, setCatalog] = useState<RagModelCatalog | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState("API Key 只提交到后端 Secret 卷，页面不会保存或回显明文。");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    try {
      const [nextProviders, nextBindings, nextCatalog] = await Promise.all([
        listRagModelProviders(), listRagModelBindings(), getRagModelCatalog(),
      ]);
      setProviders(nextProviders); setBindings(nextBindings); setCatalog(nextCatalog);
      setMessage("已加载供应商、用途主备绑定和官方默认地址。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型供应商配置加载失败");
    } finally { setBusy(false); }
  };
  useEffect(() => { void refresh(); }, []);

  const suggestions = useMemo(() => [...(catalog?.embedding ?? []), ...(catalog?.translation ?? [])], [catalog]);
  const useSuggestion = (item: Record<string, string>) => setForm((current) => ({
    ...current,
    name: item.name ?? current.name,
    adapter_type: (item.adapter_type as RagModelAdapter) ?? current.adapter_type,
    model: item.model ?? current.model,
    base_url: item.base_url?.replace("{WorkspaceId}", "你的WorkspaceId") ?? current.base_url,
    purpose: item.model?.includes("embedding") || item.model?.toLowerCase().includes("bge") ? "embedding" : "translation",
  }));

  const submit = async () => {
    if (!form.name.trim() || !form.model.trim() || !form.base_url.trim() || !form.api_key.trim()) {
      setMessage("请填写供应商名称、模型、Base URL 和 API Key。"); return;
    }
    setBusy(true);
    try {
      await createRagModelProvider({ ...form, priority: Number(form.priority) });
      setForm(EMPTY_FORM); await refresh(); setMessage("供应商已保存；下一步请绑定主模型和备用模型。");
    } catch (error) { setMessage(error instanceof Error ? error.message : "供应商保存失败"); setBusy(false); }
  };

  const testConnectivity = async () => {
    if (!form.model.trim() || !form.base_url.trim() || !form.api_key.trim()) {
      setMessage("测试网络前请填写模型、Base URL 和 API Key。"); return;
    }
    setBusy(true);
    try {
      const result = await testRagModelConnectivity({
        purpose: form.purpose,
        adapter_type: form.adapter_type, model: form.model, base_url: form.base_url,
        api_key: form.api_key,
      });
      setMessage(result.ok ? `连接成功：${result.message}` : `连接失败：${result.message}`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "模型网络测试失败"); }
    finally { setBusy(false); }
  };

  const bind = async (purpose: RagModelPurpose, primary: string, fallback: string) => {
    if (!primary) { setMessage("请先选择主模型。"); return; }
    setBusy(true);
    try {
      await bindRagModelPurpose(purpose, { primary_provider_id: primary, fallback_provider_ids: fallback ? [fallback] : [] });
      await refresh(); setMessage(`${purpose === "embedding" ? "Embedding" : "翻译"} 主备模型已更新。`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "主备绑定失败"); setBusy(false); }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div><span className="eyebrow">系统工具 / RAG-023</span><h1>模型供应商与主备</h1><p>维护 Embedding 与俄中翻译模型；额度耗尽、超时或供应商不可用时自动切换一次备用模型。</p></div><button className="secondary-button" type="button" onClick={() => void refresh()} disabled={busy}><ArrowsClockwise size={16} />刷新</button></section>
    <p className="form-message" role="status">{message}</p>
    <section className="panel">
      <div className="section-heading"><div><span className="eyebrow">供应商注册</span><h2>新增云端模型</h2></div><Key size={22} /></div>
      <div className="button-row">{suggestions.map((item) => <button className="text-button" type="button" key={`${item.adapter_type}-${item.model}`} onClick={() => useSuggestion(item)}>使用 {item.name} · {item.model}</button>)}</div>
      <div className="form-grid">
        <label>供应商名称<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="例如 SiliconFlow" /></label>
        <label>测试用途<select value={form.purpose} onChange={(event) => setForm({ ...form, purpose: event.target.value as "embedding" | "translation" })}><option value="embedding">Embedding 向量化</option><option value="translation">俄语 → 中文翻译</option></select></label>
        <label>适配器<select value={form.adapter_type} onChange={(event) => setForm({ ...form, adapter_type: event.target.value as RagModelAdapter })}><option value="dashscope">阿里云百炼</option><option value="siliconflow">SiliconFlow</option><option value="zhipu">智谱 AI</option></select></label>
        <label>模型 ID<input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} placeholder="BAAI/bge-m3 或 Qwen/Qwen2.5-7B-Instruct" /></label>
        <label>Base URL<input value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} placeholder="https://api.siliconflow.cn/v1" /></label>
        <label>API Key（只写入后端）<input type="password" autoComplete="new-password" value={form.api_key} onChange={(event) => setForm({ ...form, api_key: event.target.value })} placeholder="不会显示或写入浏览器" /></label>
        <label>优先级<input type="number" min="1" max="1000" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} /></label>
      </div>
      <div className="button-row"><button className="secondary-button" type="button" disabled={busy} onClick={() => void testConnectivity()}><ArrowsClockwise size={17} />测试网络</button><button className="primary-button" type="button" disabled={busy} onClick={() => void submit()}><ShieldCheck size={17} />保存供应商</button></div>
    </section>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">用途路由</span><h2>主模型 / 备用模型</h2></div><ShieldCheck size={22} /></div>
      {PURPOSES.map(({ key, label }) => { const binding = bindings.find((item) => item.purpose === key); return <PurposeBinding key={key} label={label} providers={providers} binding={binding} disabled={busy} onSave={(primary, fallback) => void bind(key, primary, fallback)} />; })}
    </section>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">已注册供应商</span><h2>凭据状态</h2></div><Key size={22} /></div>{providers.length ? providers.map((provider) => <div className="operation-row" key={provider.provider_id}><span><strong>{provider.name} · {provider.model}</strong><small>{provider.adapter_type} · {provider.base_url}</small></span><em>{provider.credential_configured ? `已配置 ${provider.credential_mask}` : "未配置 API Key"}</em><button className="text-button" type="button" onClick={() => { void disableRagModelProvider(provider.provider_id).then(refresh); }} disabled={busy || !provider.enabled}><Trash size={15} />停用</button></div>) : <div className="empty-search"><strong>尚未注册供应商</strong><span>先添加 SiliconFlow、智谱或百炼模型。</span></div>}</section>
  </div>;
}

function PurposeBinding({ label, providers, binding, disabled, onSave }: { label: string; providers: RagModelProvider[]; binding?: RagModelBinding; disabled: boolean; onSave: (primary: string, fallback: string) => void }) {
  const [primary, setPrimary] = useState(binding?.primary_provider_id ?? "");
  const [fallback, setFallback] = useState(binding?.fallback_provider_ids[0] ?? "");
  useEffect(() => { setPrimary(binding?.primary_provider_id ?? ""); setFallback(binding?.fallback_provider_ids[0] ?? ""); }, [binding]);
  return <div className="form-grid"><label>{label} · 主模型<select value={primary} onChange={(event) => setPrimary(event.target.value)}><option value="">请选择</option>{providers.filter((item) => item.enabled).map((item) => <option value={item.provider_id} key={item.provider_id}>{item.name} · {item.model}</option>)}</select></label><label>备用模型<select value={fallback} onChange={(event) => setFallback(event.target.value)}><option value="">不设置</option>{providers.filter((item) => item.enabled && item.provider_id !== primary).map((item) => <option value={item.provider_id} key={item.provider_id}>{item.name} · {item.model}</option>)}</select></label><button className="secondary-button" type="button" disabled={disabled || !primary} onClick={() => onSave(primary, fallback)}>保存绑定</button></div>;
}
