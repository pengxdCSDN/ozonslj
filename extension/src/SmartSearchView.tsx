import { useEffect, useState } from "react";
import { checkAndSaveSmartSearch, listSmartSearchHistory, type SmartSearchReport } from "./api";

export function SmartSearchView({ workspaceId }: { workspaceId: string }) {
  const [reports, setReports] = useState<SmartSearchReport[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("检查只提供修改建议，原始文本始终保留");
  const load = async () => { try { setReports(await listSmartSearchHistory(workspaceId)); setMessage("已加载 Smart Search 历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "Smart Search 历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { setBusy(true); try { await checkAndSaveSmartSearch(workspaceId, { text: "Термос 500 мл из нержавеющей стали", required_terms: ["термос", "500 мл", "нержавеющая сталь"], category: "термосы", category_terms: ["термос"] }); setMessage("Smart Search 检查报告已保存，原文保持不变"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "Smart Search 保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-006</p><h1>Smart Search 检查</h1><p>检查关键词覆盖、重复、堆砌和类目一致性，只提供建议，不自动修改内容。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "检查并保存中…" : "检查并保存报告"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近检查</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{reports.length ? reports.map((report, index) => <article className="history-item" key={`${report.valid}-${index}`}><strong>{report.valid ? "检查通过" : "存在阻断问题"} · 原文已保留</strong><span>已覆盖：{report.covered_terms.join("、") || "无"} · 缺失：{report.missing_terms.join("、") || "无"}</span><small>{report.findings.map((finding) => `${finding.code}：${finding.message} → ${finding.suggestion}`).join("；") || "暂无检查发现"}</small></article>) : <div className="empty-search"><strong>暂无 Smart Search 报告</strong><span>原始 Listing 文本不会被自动删除或覆盖。</span></div>}</section></div>;
}
