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
  const [page, setPage] = useState(1);
  const [jumpPage, setJumpPage] = useState("");
  const [query, setQuery] = useState("");
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [draftCount, setDraftCount] = useState(0);
  const [confirmedCount, setConfirmedCount] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [reviewer, setReviewer] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<RagEvaluationRun | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const result = await listRagEvaluationCases(page, 20, query);
      setCases(result.items); setTotal(result.total); setTotalPages(result.total_pages);
      setDraftCount(result.draft_count); setConfirmedCount(result.confirmed_count);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "评测案例加载失败"); }
    finally { setLoading(false); }
  }, [page, query]);
  useEffect(() => { void refresh(); }, [refresh]);
  const draftCases = useMemo(() => cases.filter((item) => item.status === "draft"), [cases]);
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
    try { setRun(await startRagEvaluation(suite)); setMessage(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "评测启动失败"); }
    finally { setBusy(false); }
  };
  const goToPage = () => {
    const requestedPage = Number(jumpPage);
    if (!Number.isInteger(requestedPage)) return;
    setPage(Math.min(totalPages, Math.max(1, requestedPage)));
    setJumpPage("");
  };
  return <div className="view-content rag-evaluation-view">
    <div className="page-heading rag-evaluation-heading"><span className="eyebrow">知识中心 / RAG-QUALITY</span><h1>评测案例确认</h1><p>先确认固定语料，再进入质量评测门禁。确认人与状态会持久化到 PostgreSQL。</p></div>
    <section className="panel rag-evaluation-run-panel"><div className="section-heading"><div><span className="eyebrow">运行门禁</span><h2>启动质量评测</h2></div><CheckCircle size={24} /></div><div className="sync-actions rag-suite-actions">{SUITES.map((suite) => <button type="button" className="secondary-button" key={suite.value} disabled={busy} onClick={() => void launch(suite.value)}>{suite.label}</button>)}</div>{run ? <div className="quality-result rag-run-result"><strong>{run.suite}：{run.gate_status === "ready" ? "门禁已通过" : "仍被阻塞"}</strong><span>已确认 {run.confirmed_count} / 目标 {run.target_count}</span></div> : null}</section>
    <section className="panel rag-evaluation-panel"><div className="section-heading"><div><span className="eyebrow">人工确认</span><h2>固定评测语料</h2></div><ClipboardText size={24} /></div>
      <div className="metric-grid rag-metrics"><div><small>案例总数</small><strong>{total}</strong><span>当前筛选结果</span></div><div><small>待确认</small><strong>{draftCount}</strong><span>完成后才能运行评测</span></div><div><small>已确认</small><strong>{confirmedCount}</strong><span>已通过人工确认</span></div></div>
      <div className="rag-evaluation-search"><label><span>搜索案例</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="案例 ID、问题、状态或安全标签" /></label></div>
      <div className="form-grid rag-evaluation-controls"><label>确认人<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="填写操作人" /></label><div className="rag-case-action-field"><span>批量操作</span><div className="sync-actions rag-case-actions"><button type="button" className="secondary-button" onClick={() => setSelected(new Set(draftCases.map((item) => item.case_id)))} disabled={!draftCases.length}>全选本页待确认</button><button type="button" className="primary-button" onClick={() => void confirmSelected()} disabled={busy || !reviewer.trim() || !selected.size}>批量确认 ({selected.size})</button><button type="button" className="secondary-button" onClick={() => void refresh()} disabled={loading}>刷新</button></div></div></div>
      {loading ? <div className="empty-search">案例加载中…</div> : null}
      {!loading && !cases.length ? <div className="empty-search"><WarningCircle size={24} /><strong>暂无当前页评测案例</strong><span>当前版本固定语料会由后端幂等写入 PostgreSQL</span></div> : null}
      {cases.map((item) => <label className="operation-row rag-case-row" key={item.case_id}><input type="checkbox" checked={selected.has(item.case_id)} disabled={item.status !== "draft"} onChange={() => toggle(item.case_id)} /><span><strong>{item.case_id} · {item.question}</strong><small>{item.expected_status} · {item.safety_tags.join(" / ") || "常规"}</small></span><em className={item.status === "confirmed" ? "is-confirmed" : "is-draft"}>{item.status === "confirmed" ? "已确认" : item.status === "draft" ? "待确认" : "已拒绝"}</em></label>)}
      <div className="sync-actions rag-pagination"><span>共 {total} 个案例 · 第 {page} / {totalPages} 页</span><div className="rag-page-controls"><button type="button" className="secondary-button" onClick={() => { setPage((current) => Math.max(1, current - 1)); setJumpPage(""); }} disabled={loading || page <= 1}>上一页</button><button type="button" className="secondary-button" onClick={() => { setPage((current) => Math.min(totalPages, current + 1)); setJumpPage(""); }} disabled={loading || page >= totalPages}>下一页</button><label className="rag-page-jump"><span>跳至</span><input type="number" min="1" max={totalPages} value={jumpPage} onChange={(event) => setJumpPage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") goToPage(); }} placeholder={String(page)} aria-label="输入页码" /><span>页</span><button type="button" className="secondary-button" onClick={goToPage} disabled={loading || !jumpPage}>确定</button></label></div></div>
    </section>
    {message ? <p className="form-message">{message}</p> : null}{error ? <p className="form-message">{error}</p> : null}
  </div>;
}
