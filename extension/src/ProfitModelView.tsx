import { useState } from "react";
import { calculateAndSaveProfitModel, type ProfitScenario } from "./api";

export function ProfitModelView({ workspaceId }: { workspaceId: string }) {
  const [results, setResults] = useState<ProfitScenario[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("输入假设会用于 FBO/FBS 利润和敏感性分析");
  const run = async () => { setBusy(true); try { setResults(await calculateAndSaveProfitModel(workspaceId, { selling_price_minor: 10000, purchase_cost_minor: 3000, fbo_logistics_minor: 700, fbs_logistics_minor: 1000, commission_minor: 1000, ad_cost_minor: 500, return_loss_minor: 200, fixed_cost_minor: 30000 })); setMessage("FBO/FBS 利润模型已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "利润模型保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">选品 Skill / SEL-005</p><h1>FBO/FBS 利润模型</h1><p>计算贡献利润、利润率、ROI、盈亏平衡和广告/采购/物流成本敏感性。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "计算并保存中…" : "计算并保存利润模型"}</button><p className="form-message">{message}</p>{results.map((item) => <div className="quality-result" key={item.fulfillment_type}><strong>{item.fulfillment_type} · 利润 {item.contribution_profit_minor} · ROI {item.roi_percent}%</strong><span>利润率 {item.contribution_margin_percent}% · 盈亏平衡 {item.break_even_units ?? "不可计算"} 件</span><small>广告 +20%：{item.ad_cost_plus_20_profit_minor} · 采购 +20%：{item.purchase_cost_plus_20_profit_minor} · 物流 +20%：{item.logistics_cost_plus_20_profit_minor}</small></div>)}{!results.length ? <div className="empty-search"><strong>尚未计算利润模型</strong><span>所有金额使用最小货币单位，假设必须可回溯。</span></div> : null}</section></div>;
}
