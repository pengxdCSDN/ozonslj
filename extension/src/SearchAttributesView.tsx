import { useEffect, useState } from "react";
import { listSearchAttributesHistory, suggestAndSaveSearchAttributes, type SearchAttributesReport } from "./api";

export function SearchAttributesView({ workspaceId }: { workspaceId: string }) {
  const [reports, setReports] = useState<SearchAttributesReport[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Search Attributes 建议可编辑，不自动发布");
  const load = async () => { try { setReports(await listSearchAttributesHistory(workspaceId)); setMessage("已加载属性报告历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "属性历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { setBusy(true); try { await suggestAndSaveSearchAttributes(workspaceId, { required: { volume: "", material: "", color: "" }, current: { volume: "500 мл" }, keyword_terms: { material: "нержавеющая сталь" } }); setMessage("Search Attributes 报告已保存"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "属性报告保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-004</p><h1>Search Attributes</h1><p>生成搜索属性建议，查看必填属性覆盖率和缺失项；结果可编辑，不自动发布。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "分析并保存中…" : "生成并保存属性报告"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近报告</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{reports.length ? reports.map((report, index) => <article className="history-item" key={`${report.coverage_percent}-${index}`}><strong>覆盖率 {report.coverage_percent}% · {report.editable ? "可编辑" : "只读"}</strong><span>{report.suggestions.map((item) => `${item.name}=${item.suggested_value ?? "缺失"}${item.covered ? " ✓" : ""}`).join("；")}</span><small>缺失必填：{report.missing_required.join("、") || "无"}</small></article>) : <div className="empty-search"><strong>暂无属性报告</strong><span>属性建议生成后需人工校对类目和字段。</span></div>}</section></div>;
}
