import { useState } from "react";
import { listSelectionValidations, runAndSaveSelectionValidate, type ValidateResult } from "./api";

const payload = { sku: "SKU-1", selling_price_minor: 10000, purchase_cost_minor: 3000, logistics_cost_minor: 1000, commission_minor: 1000, ad_cost_minor: 500, return_loss_minor: 200, fixed_launch_cost_minor: 30000, competitor_count: 25, own_stock: 100, monthly_sales: 20, certification_required: true };

export function SelectionValidateView({ workspaceId }: { workspaceId: string }) {
  const [results, setResults] = useState<ValidateResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("验证结果会保留输入假设、利润和风险结论");
  const run = async () => { setBusy(true); try { const result = await runAndSaveSelectionValidate(workspaceId, payload); setResults((current) => [result, ...current]); setMessage("验证结果已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "验证失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setResults(await listSelectionValidations(workspaceId)); setMessage("已加载 Validate 历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">选品 Skill / SEL-002</p><h1>Validate 商品验证</h1><p>分别测算 FBO/FBS 利润，保存输入假设、风险和盈亏平衡结果。</p></div></section><section className="panel import-panel"><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void run()}>开始验证并保存</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载验证历史</button></div><p className="form-message">{message}</p>{results.map((result, index) => <div className="quality-result" key={`${result.sku}-${index}`}><strong>{result.sku} · {result.incomplete ? "不完整估算" : "输入完整"}</strong><span>FBO：利润 {result.fbo.contribution_profit_minor} · 利润率 {result.fbo.margin_percent}% · ROI {result.fbo.roi_percent}% · 盈亏平衡 {result.fbo.break_even_units ?? "不可计算"} 件</span><span>FBS：利润 {result.fbs.contribution_profit_minor} · 利润率 {result.fbs.margin_percent}% · ROI {result.fbs.roi_percent}% · 盈亏平衡 {result.fbs.break_even_units ?? "不可计算"} 件</span><small>{result.risks.join(" · ") || "暂无风险提示"} · 缺失：{result.incomplete_reasons.join("、") || "无"}</small></div>)}{!results.length ? <div className="empty-search"><strong>尚未运行商品验证</strong><span>验证只生成决策辅助结果，不自动采购、上架或投放广告。</span></div> : null}</section></div>;
}
