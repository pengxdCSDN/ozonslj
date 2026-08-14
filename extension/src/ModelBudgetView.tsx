import { CheckCircle, FloppyDisk, Gauge, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import { listModelBudgets, listRagModelProviders, saveModelBudget, type ModelBudget, type RagModelProvider } from "./api";

const PURPOSE_LABELS: Record<string, string> = {
  embedding: "嵌入",
  intent_rewrite: "意图与重写",
  rerank: "精排",
  answer_generation: "回答生成",
};

export function ModelBudgetView() {
  const [budgets, setBudgets] = useState<ModelBudget[]>([]);
  const [providers, setProviders] = useState<RagModelProvider[]>([]);
  const [drafts, setDrafts] = useState<Record<string, BudgetDraft>>({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const refresh = async () => {
    try {
      const [nextBudgets, nextProviders] = await Promise.all([listModelBudgets(), listRagModelProviders()]);
      setBudgets(nextBudgets);
      setProviders(nextProviders.filter((provider) => provider.enabled));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "额度状态加载失败");
    }
  };
  useEffect(() => { void refresh(); }, []);
  // 同一个模型的多个 RAG 用途共用一条额度策略；保存时再同步到用途级后端记录。
  const rows = useMemo(() => providers.map((provider) => {
    const purposes = provider.model_kind === "embedding" ? ["embedding"] : ["intent_rewrite", "rerank", "answer_generation"];
    const current = purposes.map((purpose) => budgets.find((item) => item.provider_id === provider.provider_id && item.purpose === purpose)).find(Boolean);
    return { provider, purposes, current };
  }), [budgets, providers]);
  const configuredCount = rows.filter((row) => row.current).length;
  const warningCount = budgets.filter((budget) => budget.state === "warning").length;
  const blockedCount = budgets.filter((budget) => !budget.allowed).length;
  const getDraft = (row: Row): BudgetDraft => drafts[row.provider.provider_id] ?? fromBudget(row.current);
  const updateDraft = (key: string, field: keyof BudgetDraft, value: string) => setDrafts((current) => ({ ...current, [key]: { ...getDraft(rows.find((row) => row.provider.provider_id === key)!), [field]: value } }));
  const save = async (row: Row) => {
    const key = row.provider.provider_id;
    const draft = getDraft(row);
    setSaving(key);
    try {
      const results = await Promise.all(row.purposes.map((purpose) => saveModelBudget(row.provider.provider_id, { ...draftToPayload(draft), purpose })));
      setBudgets((current) => [...current.filter((item) => item.provider_id !== row.provider.provider_id), ...results]);
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "额度策略保存失败"); }
    finally { setSaving(null); }
  };
  return <div className="view-content budget-view">
    <div className="page-heading budget-heading"><div><span className="eyebrow">系统工具 / 模型治理 / RAG-024</span><h1>模型额度与降级</h1><p>给每个已启用模型设定边界，系统会在真正调用前检查预算并保留可追溯的用量台账。</p></div><div className="budget-heading-mark"><Gauge size={28} /><span>预算中枢</span></div></div>
    <section className="budget-overview" aria-label="额度概览">
      <div className="budget-overview-lead"><span className="eyebrow">当前治理范围</span><strong>{providers.length}</strong><span>个已启用模型</span><small>{configuredCount} 个用途已配置策略</small></div>
      <div className="budget-stat"><span>正常运行</span><strong>{Math.max(configuredCount - warningCount - blockedCount, 0)}</strong><small>可继续调用</small></div>
      <div className="budget-stat budget-stat-warning"><span>临界预警</span><strong>{warningCount}</strong><small>达到 90% 以上</small></div>
      <div className="budget-stat budget-stat-danger"><span>已阻断</span><strong>{blockedCount}</strong><small>等待备用或调整策略</small></div>
    </section>
    {error ? <p className="form-message" role="alert">{error}</p> : null}
    <section className="panel budget-panel">
      <div className="section-heading budget-section-heading"><div><span className="eyebrow">策略与用量</span><h2>供应商用量</h2></div><span className="budget-help">按用途独立设定 · 保存后立即生效</span></div>
      {rows.length ? rows.map((row) => { const key = row.provider.provider_id; const draft = getDraft(row); const budget = row.current; return <article className="operation-row" key={key}>
        <div className="budget-row-identity"><div className="budget-provider-orb"><Gauge size={17} /></div><span><strong>{row.provider.name}</strong><small>{row.provider.model} · {/(rerank|reranker)/i.test(row.provider.model) ? "精排" : row.purposes.length > 1 ? "多用途共用策略" : PURPOSE_LABELS[row.purposes[0]] ?? row.purposes[0]}</small></span></div>
        <div className="budget-row-state"><em className={budget?.state === "exceeded" ? "danger" : budget?.state === "warning" ? "warning" : budget ? "success" : "pending"}>{budget?.state === "exceeded" ? "已阻断" : budget?.state === "warning" ? "接近上限" : budget ? "运行正常" : "待配置"}</em><small>{budget ? `今日 ${budget.usage.daily_tokens.toLocaleString()} / ${budget.policy.daily_token_limit.toLocaleString()} tokens` : "保存策略后开始记录用量"}</small></div>
        <div className="budget-fields"><label><span>日 token 上限</span><input aria-label={`${row.provider.name} 日 token 上限`} type="number" min="1" value={draft.daily_token_limit} onChange={(event) => updateDraft(key, "daily_token_limit", event.target.value)} /></label><label><span>月 token 上限</span><input aria-label={`${row.provider.name} 月 token 上限`} type="number" min="1" value={draft.monthly_token_limit} onChange={(event) => updateDraft(key, "monthly_token_limit", event.target.value)} /></label><label><span>每日请求数</span><input aria-label={`${row.provider.name} 每日请求数`} type="number" min="1" value={draft.daily_request_limit} onChange={(event) => updateDraft(key, "daily_request_limit", event.target.value)} /></label><label><span>月度预算（人民币 RMB）</span><input aria-label={`${row.provider.name} 月度预算（人民币 RMB）`} type="number" min="0.01" step="0.01" value={draft.monthly_budget} onChange={(event) => updateDraft(key, "monthly_budget", event.target.value)} /></label></div>
        <button className="secondary-button budget-save" type="button" disabled={saving !== null} onClick={() => void save(row)}>{saving === key ? <Gauge size={16} className="spin" /> : <FloppyDisk size={16} />}{saving === key ? "保存中" : "保存策略"}</button>
        {!budget?.allowed ? <WarningCircle className="budget-alert-icon" size={18} weight="fill" aria-label="已阻断" /> : budget ? <CheckCircle className="budget-ok-icon" size={18} weight="fill" aria-label="运行正常" /> : null}
      </article>; }) : <div className="empty-search"><Gauge size={24} /><strong>尚未配置启用的模型供应商</strong><span>请先在“模型供应商”页面新增并启用模型。</span></div>}
    </section>
  </div>;
}

type BudgetDraft = { daily_token_limit: string; monthly_token_limit: string; daily_request_limit: string; monthly_budget: string };
type Row = { provider: RagModelProvider; purposes: string[]; current?: ModelBudget };
function fromBudget(budget?: ModelBudget): BudgetDraft { return { daily_token_limit: String(budget?.policy.daily_token_limit ?? 100000), monthly_token_limit: String(budget?.policy.monthly_token_limit ?? 3000000), daily_request_limit: String(budget?.policy.daily_request_limit ?? 1000), monthly_budget: String(budget?.policy.monthly_budget ?? 100) }; }
function draftToPayload(draft: BudgetDraft) { return { daily_token_limit: Number(draft.daily_token_limit), monthly_token_limit: Number(draft.monthly_token_limit), daily_request_limit: Number(draft.daily_request_limit), monthly_budget: Number(draft.monthly_budget), budget_currency: "RMB" as const }; }
