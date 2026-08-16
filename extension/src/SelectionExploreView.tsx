import { useState } from "react";
import { listSelectionExploreOpportunities, runAndSaveSelectionExplore, type ExploreOpportunity } from "./api";

const items = [
  { keyword: "термос", search_count: 1000, conversion_rate: 12, sample_count: 5, median_price_minor: 199900, own_stock: 0, own_sales: 0 },
  { keyword: "чехол", search_count: 500, conversion_rate: 5, sample_count: 2, median_price_minor: 89900, own_stock: 10, own_sales: 4 },
];

export function SelectionExploreView({ workspaceId }: { workspaceId: string }) {
  const [results, setResults] = useState<ExploreOpportunity[]>([]);
  const [busy, setBusy] = useState(false);
  const [minScore, setMinScore] = useState(0);
  const [minSearch, setMinSearch] = useState(0);
  const [gapOnly, setGapOnly] = useState(false);
  const [message, setMessage] = useState("结果是搜索词、公开样本和自有覆盖缺口的估算融合");
  const run = async () => { setBusy(true); try { setResults(await runAndSaveSelectionExplore(workspaceId, items, { min_score: minScore, min_search_count: minSearch, coverage_gap_only: gapOnly })); setMessage("筛选后的机会结果已保存，可进入 Validate 复核"); } catch (error) { setMessage(error instanceof Error ? error.message : "Explore 失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setResults(await listSelectionExploreOpportunities(workspaceId)); setMessage("已加载 Explore 历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">选品 Skill / SEL-001</p><h1>Explore 机会探索</h1><p>融合搜索词、公开样本和自有覆盖缺口，生成可追溯机会估算。</p></div></section><section className="panel import-panel"><div className="form-grid"><label>最低机会分<input type="number" min="0" max="100" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} /></label><label>最低搜索量<input type="number" min="0" value={minSearch} onChange={(event) => setMinSearch(Number(event.target.value))} /></label><label className="checkbox-label"><input type="checkbox" checked={gapOnly} onChange={(event) => setGapOnly(event.target.checked)} />只看自有覆盖缺口</label></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void run()}>筛选、评分并保存</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div><p className="form-message">{message}</p>{results.map((item) => <div className="operation-row" key={item.keyword}><span><strong>{item.keyword} · {item.score} 分</strong><small>{item.reasons.join(" · ")} · 缺失：{item.missing_inputs.join("、") || "无"}</small></span><em>{item.estimated ? "采样估算" : "官方事实"}</em></div>)}{!results.length ? <div className="empty-search"><strong>尚未生成机会清单</strong><span>机会结果只用于辅助决策，不代表全市场精确销量。</span></div> : null}</section></div>;
}
