import { useState } from "react";
import { analyzeAndSaveCostSensitivity, type CostSensitivityScenario } from "./api";

export function CostSensitivityView({ workspaceId }: { workspaceId: string }) {
  const [results, setResults] = useState<CostSensitivityScenario[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("敏感性分析会同时调整采购、物流和广告成本");
  const run = async () => { setBusy(true); try { setResults(await analyzeAndSaveCostSensitivity(workspaceId, { selling_price_minor: 10000, purchase_cost_minor: 3000, logistics_cost_minor: 700, commission_minor: 1000, ad_cost_minor: 500, return_loss_minor: 200 })); setMessage("成本敏感性结果已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "敏感性分析保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">选品 Skill / SEL-006</p><h1>成本敏感性分析</h1><p>比较采购、物流和广告成本变化对利润与利润率的影响，保留原始输入假设。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "分析并保存中…" : "分析并保存敏感性"}</button><p className="form-message">{message}</p>{results.length ? <div className="quality-result">{results.map((item) => <div className="operation-row" key={item.change_percent}><span><strong>{item.label} {item.change_percent > 0 ? "+" : ""}{item.change_percent}%</strong><small>利润率 {item.margin_percent}%</small></span><em>{item.profit_minor} 利润</em></div>)}</div> : <div className="empty-search"><strong>尚未运行敏感性分析</strong><span>结果用于比较成本变化，不会自动修改售价或广告预算。</span></div>}</section></div>;
}
