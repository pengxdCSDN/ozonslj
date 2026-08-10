import { useCallback, useEffect, useState } from "react";
import { fetchQualityFindings, fetchQualitySummary, updateQualityFinding, type QualityFinding, type QualitySummary } from "./api";

export function DataQualityDashboardView({ workspaceId }: { workspaceId: string }) {
  const [summary, setSummary] = useState<QualitySummary | null>(null);
  const [findings, setFindings] = useState<QualityFinding[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("质量中心只展示问题，不修改业务事实。");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [nextSummary, nextFindings] = await Promise.all([
        fetchQualitySummary(workspaceId),
        fetchQualityFindings(workspaceId, "open"),
      ]);
      setSummary(nextSummary);
      setFindings(nextFindings);
      setMessage("质量摘要已更新。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "质量摘要加载失败，请重试。");
    } finally {
      setBusy(false);
    }
  }, [workspaceId]);

  useEffect(() => { void load(); }, [load]);

  const resolve = async (finding: QualityFinding) => {
    if (!finding.id) return;
    setBusy(true);
    try {
      await updateQualityFinding(finding.id, workspaceId, "resolved");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "处理质量问题失败，请重试。");
      setBusy(false);
    }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div>
      <p className="eyebrow">数据质量 / DQ-008</p>
      <h1>数据质量中心</h1>
      <p>集中查看问题数量、严重级别、规则来源和处理状态；异常数据不会静默覆盖业务事实。</p>
    </div></section>
    <section className="panel">
      <div className="panel-heading"><h2>问题摘要</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>
      {summary ? <div className="metric-grid"><div><small>开放问题</small><strong>{summary.total}</strong></div><div><small>错误</small><strong>{summary.by_severity.error ?? 0}</strong></div><div><small>警告</small><strong>{summary.by_severity.warning ?? 0}</strong></div><div><small>规则数</small><strong>{Object.keys(summary.by_rule).length}</strong></div></div> : <p className="empty-state">正在加载质量摘要…</p>}
      <p className="form-message" role="status">{message}</p>
    </section>
    <section className="panel"><div className="panel-heading"><h2>开放问题与影响字段</h2><span className="status-pill warning">{findings.length} 条待处理</span></div>
      {findings.length ? findings.map((finding) => <article className="operation-row" key={finding.id ?? `${finding.rule_code}-${finding.field_name}`}><span><strong>{finding.rule_code}</strong><small>{finding.field_name} · 来源：{finding.source} · 级别：{finding.severity}</small></span><em>{finding.message}</em>{finding.id ? <button className="text-button" disabled={busy} onClick={() => void resolve(finding)}>标记已处理</button> : null}</article>) : <p className="empty-state">暂无开放质量问题。</p>}
    </section>
  </div>;
}
