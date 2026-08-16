import { CheckCircle, ClipboardText, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { confirmRagEvaluationCasesBatch, listRagEvaluationCases, startRagEvaluation, type RagEvaluationCase, type RagEvaluationRun } from "./api";

const SUITES: Array<{ value: RagEvaluationRun["suite"]; label: string }> = [
  { value: "quick", label: "30 例快速评测" },
  { value: "standard", label: "120 例标准回归" },
  { value: "full", label: "240 例完整验收" },
];

export function RagEvaluationView() {
  const [cases, setCases] = useState<RagEvaluationCase[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [reviewer, setReviewer] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<RagEvaluationRun | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try { setCases(await listRagEvaluationCases()); } catch (cause) { setError(cause instanceof Error ? cause.message : "评测案例加载失败"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const draftCases = useMemo(() => cases.filter((item) => item.status === "draft"), [cases]);
  const confirmedCount = cases.filter((item) => item.status === "confirmed").length;
  const toggle = (caseId: string) => setSelected((current) => { const next = new Set(current); if (next.has(caseId)) next.delete(caseId); else next.add(caseId); return next; });
  const confirmSelected = async () => {
    if (!reviewer.trim() || !selected.size) return;
    setBusy(true); setError("");
    try { const result = await confirmRagEvaluationCasesBatch([...selected], reviewer.trim()); setSelected(new Set()); setMessage(`已确认 ${result.confirmed_count} 个案例，并已写入 PostgreSQL`); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "批量确认失败"); }
    finally { setBusy(false); }
  };
  const launch = async (suite: RagEvaluationRun["suite"]) => {
    setBusy(true); setError("");
    try { setRun(await startRagEvaluation(suite)); setMessage(`${suite} 评测已创建，门禁状态已返回`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "评测启动失败"); }
    finally { setBusy(false); }
  };
  return <div className="view-content">
    <div className="page-heading"><span className="eyebrow">知识中心 / RAG-QUALITY</span><h1>评测案例确认</h1><p>案例确认人与状态持久化到 PostgreSQL；未确认案例不能进入评测门禁。</p></div>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">人工确认</span><h2>固定评测语料</h2></div><ClipboardText size={24} /></div>
      <div className="metric-grid"><div><small>案例总数</small><strong>{cases.length}</strong></div><div><small>待确认</small><strong>{draftCases.length}</strong></div><div><small>已确认</small><strong>{confirmedCount}</strong></div></div>
      <div className="form-grid"><label>确认人<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="填写操作人" /></label><div className="sync-actions"><button type="button" className="secondary-button" onClick={() => setSelected(new Set(draftCases.map((item) => item.case_id)))} disabled={!draftCases.length}>全选待确认</button><button type="button" className="primary-button" onClick={() => void confirmSelected()} disabled={busy || !reviewer.trim() || !selected.size}>批量确认 ({selected.size})</button><button type="button" className="secondary-button" onClick={() => void refresh()} disabled={loading}>刷新</button></div></div>
      {loading ? <div className="empty-search">案例加载中…</div> : null}
      {!loading && !cases.length ? <div className="empty-search"><WarningCircle size={24} /><strong>暂无评测案例</strong><span>后端首次读取会幂等写入固定 400 例语料</span></div> : null}
      {cases.map((item) => <label className="operation-row" key={item.case_id}><input type="checkbox" checked={selected.has(item.case_id)} disabled={item.status !== "draft"} onChange={() => toggle(item.case_id)} /><span><strong>{item.case_id} · {item.question}</strong><small>{item.expected_status} · {item.safety_tags.join(" / ") || "常规"}</small></span><em>{item.status === "confirmed" ? "已确认" : item.status === "draft" ? "待确认" : "已拒绝"}</em></label>)}
    </section>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">运行门禁</span><h2>启动质量评测</h2></div><CheckCircle size={24} /></div><div className="sync-actions">{SUITES.map((suite) => <button type="button" className="secondary-button" key={suite.value} disabled={busy} onClick={() => void launch(suite.value)}>{suite.label}</button>)}</div>{run ? <div className="quality-result"><strong>{run.suite}：{run.gate_status === "ready" ? "门禁已通过" : "仍被阻塞"}</strong><span>已确认 {run.confirmed_count} / 目标 {run.target_count}</span></div> : null}</section>
    {message ? <p className="form-message">{message}</p> : null}{error ? <p className="form-message">{error}</p> : null}
  </div>;
}
