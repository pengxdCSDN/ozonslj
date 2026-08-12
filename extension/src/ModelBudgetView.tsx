import { Gauge, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { listModelBudgets, type ModelBudget } from "./api";

const PURPOSE_LABELS: Record<string, string> = {
  embedding: "嵌入",
  intent_rewrite: "意图与重写",
  rerank: "重排序",
  answer_generation: "回答生成",
};

export function ModelBudgetView() {
  const [budgets, setBudgets] = useState<ModelBudget[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    void listModelBudgets().then(setBudgets).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "额度状态加载失败");
    });
  }, []);
  return <div className="view-content">
    <div className="page-heading"><span className="eyebrow">系统工具 / 模型治理</span><h1>模型额度与降级</h1><p>达到 90% 时进入预警，达到上限后自动阻断当前供应商并切换备用模型。</p></div>
    {error ? <p className="form-message" role="alert">{error}</p> : null}
    <section className="panel">
      <div className="section-heading"><div><span className="eyebrow">RAG-024</span><h2>供应商用量</h2></div><Gauge size={24} /></div>
      {budgets.length ? budgets.map((budget) => <article className="operation-row" key={`${budget.provider_id}-${budget.purpose}`}>
        <span><strong>{budget.provider_id}</strong><small>{PURPOSE_LABELS[budget.purpose] ?? budget.purpose} · 今日 {budget.usage.daily_tokens.toLocaleString()} / {budget.policy.daily_token_limit.toLocaleString()} tokens</small></span>
        <em className={budget.state === "exceeded" ? "danger" : budget.state === "warning" ? "warning" : "success"}>{budget.state}</em>
        {!budget.allowed ? <WarningCircle size={18} weight="fill" aria-label="已阻断" /> : null}
      </article>) : <div className="empty-search"><Gauge size={24} /><strong>尚未配置模型额度</strong><span>管理员配置供应商策略后，系统会在这里显示预警和降级状态。</span></div>}
    </section>
  </div>;
}
