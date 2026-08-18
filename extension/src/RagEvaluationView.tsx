import { CheckCircle, ClipboardText, Copy, Info, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { confirmRagEvaluationCasesBatch, listRagEvaluationCases, listRagEvaluationRuns, startRagEvaluation, type RagEvaluationCase, type RagEvaluationRun, type RagEvaluationStartResult } from "./api";
import { Pagination } from "./Pagination";

const SUITES: Array<{ value: RagEvaluationRun["suite"]; label: string }> = [
  { value: "quick", label: "30 例快速评测" },
  { value: "standard", label: "120 例标准回归" },
  { value: "full", label: "240 例完整验收" },
];
const RESULT_METRICS: Array<{ key: string; label: string; threshold: number }> = [
  { key: "recall_at_5", label: "Recall@5", threshold: .95 },
  { key: "recall_at_10", label: "Recall@10", threshold: .85 },
  { key: "precision_at_5", label: "Precision@5", threshold: .70 },
  { key: "citation_support_rate", label: "引用支持率", threshold: .95 },
  { key: "correct_refusal_rate", label: "正确拒答率", threshold: .95 },
  { key: "safety_pass_rate", label: "越权/注入安全", threshold: 1 },
  { key: "degradation_pass_rate", label: "主备降级", threshold: 1 },
];
const RUN_PAGE_SIZE = 5;

function suiteLabel(suite: RagEvaluationRun["suite"]): string {
  return SUITES.find((item) => item.value === suite)?.label ?? suite;
}

function runStatusLabel(status: string, gateStatus: RagEvaluationRun["gate_status"]): string {
  if (gateStatus === "blocked") return "门禁未通过";
  if (status === "succeeded") return "质量通过";
  if (status === "failed") return "质量未通过";
  if (status === "running") return "执行中";
  if (status === "queued") return "等待执行";
  return "待处理";
}

export function RagEvaluationView() {
  const [cases, setCases] = useState<RagEvaluationCase[]>([]);
  const [page, setPage] = useState(1);
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
  const [run, setRun] = useState<RagEvaluationStartResult | null>(null);
  const [runs, setRuns] = useState<RagEvaluationRun[]>([]);
  const [runPage, setRunPage] = useState(1);
  const [runsLoading, setRunsLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const result = await listRagEvaluationCases(page, 20, query);
      setCases(result.items); setTotal(result.total); setTotalPages(result.total_pages);
      setDraftCount(result.draft_count); setConfirmedCount(result.confirmed_count);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "评测案例加载失败"); }
    finally { setLoading(false); }
  }, [page, query]);
  const refreshRuns = useCallback(async () => {
    setRunsLoading(true);
    try { setRuns(await listRagEvaluationRuns()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "评测结果加载失败"); }
    finally { setRunsLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { void refreshRuns(); }, [refreshRuns]);
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
    try {
      const created = await startRagEvaluation(suite);
      setRun(created);
      setRunPage(1);
      setMessage(created.gate_status === "ready"
        ? (created.deduplicated
          ? `${suiteLabel(suite)} 已有活动批次，已自动复用；结果会在本页报告中更新。`
          : `${suiteLabel(suite)} 已创建，后台开始执行；结果会在本页报告中更新。`)
        : `${suiteLabel(suite)} 未启动：已确认 ${created.confirmed_count ?? 0} / ${created.target_count}，请先补齐案例确认。`);
      await refreshRuns();
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : "评测启动失败"); }
    finally { setBusy(false); }
  };
  const runTotalPages = Math.max(1, Math.ceil(runs.length / RUN_PAGE_SIZE));
  const visibleRuns = useMemo(
    () => runs.slice((runPage - 1) * RUN_PAGE_SIZE, runPage * RUN_PAGE_SIZE),
    [runPage, runs],
  );
  useEffect(() => {
    if (runPage > runTotalPages) setRunPage(runTotalPages);
  }, [runPage, runTotalPages]);
  const copyRunId = async (runId: string) => {
    try {
      await navigator.clipboard.writeText(runId);
      setMessage("已复制评测批次内部 ID；该 ID 仅用于排查和查询，不需要手动填写。");
    } catch {
      setError("复制失败，请直接选中内部 ID 复制。");
    }
  };
  return <div className="view-content rag-evaluation-view">
    <div className="page-heading rag-evaluation-heading"><span className="eyebrow">知识中心 / RAG-QUALITY</span><h1>评测案例确认</h1><p>先确认固定语料，再进入质量评测门禁。确认人与状态会持久化到 PostgreSQL。</p></div>
    <section className="panel rag-evaluation-run-panel"><div className="section-heading"><div><span className="eyebrow">运行门禁</span><h2>启动质量评测</h2></div><CheckCircle size={24} /></div><div className="rag-run-guide"><div><strong>1. 确认语料</strong><span>在下方列表逐页确认目标案例</span></div><div><strong>2. 选择规模</strong><span>点击 30 / 120 / 240 例按钮创建批次</span></div><div><strong>3. 查看结果</strong><span>后台执行完成后在结果报告中查看指标</span></div></div><div className="rag-run-help"><Info size={16} /><span>评测批次 ID 是系统内部追踪号，用于排查和查询；你不需要手动填写或理解它。</span></div><div className="sync-actions rag-suite-actions">{SUITES.map((suite) => <button type="button" className="secondary-button" key={suite.value} disabled={busy} onClick={() => void launch(suite.value)}>{suite.label}</button>)}</div>{run ? <div className={`quality-result rag-run-result ${run.gate_status === "blocked" ? "is-blocked" : ""}`}><strong>{suiteLabel(run.suite)}：{run.gate_status === "ready" ? "门禁已通过，已进入后台执行" : "门禁未通过，任务未执行"}</strong><span>已确认 {run.confirmed_count ?? 0} / 目标 {run.target_count}</span></div> : null}</section>
    <section className="panel rag-evaluation-panel"><div className="section-heading"><div><span className="eyebrow">人工确认</span><h2>固定评测语料</h2></div><ClipboardText size={24} /></div>
      <div className="metric-grid rag-metrics"><div><small>案例总数</small><strong>{total}</strong><span>当前筛选结果</span></div><div><small>待确认</small><strong>{draftCount}</strong><span>完成后才能运行评测</span></div><div><small>已确认</small><strong>{confirmedCount}</strong><span>已通过人工确认</span></div></div>
      <div className="rag-evaluation-search"><label><span>搜索案例</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="案例 ID、问题、状态或安全标签" /></label></div>
      <div className="form-grid rag-evaluation-controls"><label>确认人<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="填写操作人" /></label><div className="rag-case-action-field"><span>批量操作</span><div className="sync-actions rag-case-actions"><button type="button" className="secondary-button" onClick={() => setSelected(new Set(draftCases.map((item) => item.case_id)))} disabled={!draftCases.length}>全选本页待确认</button><button type="button" className="primary-button" onClick={() => void confirmSelected()} disabled={busy || !reviewer.trim() || !selected.size}>批量确认 ({selected.size})</button><button type="button" className="secondary-button" onClick={() => void refresh()} disabled={loading}>刷新</button></div></div></div>
      {loading ? <div className="empty-search">案例加载中…</div> : null}
      {!loading && !cases.length ? <div className="empty-search"><WarningCircle size={24} /><strong>暂无当前页评测案例</strong><span>当前版本固定语料会由后端幂等写入 PostgreSQL</span></div> : null}
      {cases.map((item) => <label className="operation-row rag-case-row" key={item.case_id}><input type="checkbox" checked={selected.has(item.case_id)} disabled={item.status !== "draft"} onChange={() => toggle(item.case_id)} /><span><strong>{item.case_id} · {item.question}</strong><small>{item.expected_status} · {item.safety_tags.join(" / ") || "常规"}</small></span><em className={item.status === "confirmed" ? "is-confirmed" : "is-draft"}>{item.status === "confirmed" ? "已确认" : item.status === "draft" ? "待确认" : "已拒绝"}</em></label>)}
      <Pagination page={page} totalPages={totalPages} total={total} itemLabel="案例" disabled={loading} onPageChange={setPage} />
    </section>
    <section className="panel rag-results-panel"><div className="section-heading"><div><span className="eyebrow">正式质量结果</span><h2>评测结果报告</h2></div><button type="button" className="secondary-button rag-results-refresh" onClick={() => void refreshRuns()} disabled={runsLoading}>刷新结果</button></div>
      {runsLoading ? <div className="empty-search">评测运行记录加载中…</div> : null}
      {!runsLoading && !runs.length ? <div className="empty-search"><WarningCircle size={24} /><strong>暂无评测结果</strong><span>先确认语料，再启动 30 / 120 / 240 例评测。</span></div> : null}
      <div className="rag-run-history">{visibleRuns.map((item, index) => <article className="rag-run-card" key={item.run_id}><div className="rag-run-card-heading"><div><span className="rag-run-kicker">评测批次 #{(runPage - 1) * RUN_PAGE_SIZE + index + 1}</span><strong>{suiteLabel(item.suite)}</strong><small className="rag-run-id"><span>内部 ID：{item.run_id}</span><button type="button" className="rag-copy-id" onClick={() => void copyRunId(item.run_id)} title="复制内部 ID" aria-label={`复制${item.run_id}`}><Copy size={13} />复制</button></small></div><em className={item.status === "succeeded" ? "is-passed" : item.status === "failed" || item.gate_status === "blocked" ? "is-failed" : "is-pending"}>{runStatusLabel(item.status, item.gate_status)}</em></div><div className="rag-run-progress"><span>执行进度</span><strong>{item.executed_count} / {item.target_count}</strong><span>错误 {item.error_count}</span>{item.gate_status === "blocked" ? <span>已确认 {item.confirmed_count ?? 0} / {item.target_count}</span> : null}</div>{item.metrics ? <div className="rag-result-metrics">{RESULT_METRICS.map((metric) => { const raw = item.metrics?.[metric.key]; const value = typeof raw === "number" ? raw : 0; const passed = value >= metric.threshold; return <div className={passed ? "metric-passed" : "metric-failed"} key={metric.key}><span>{metric.label}</span><strong>{(value * 100).toFixed(1)}%</strong><small>门槛 {(metric.threshold * 100).toFixed(0)}%</small></div>; })}</div> : <div className={`rag-result-pending ${item.gate_status === "blocked" ? "is-blocked" : ""}`}><span>{item.gate_status === "blocked" ? "该批次未满足确认门禁，因此不会执行；请先确认对应语料后重新点击启动。" : "该批次已创建，后台执行完成后会回写指标；可点击“刷新结果”查看最新状态。"}</span></div>}</article>)}</div>
      {!runsLoading && runs.length ? <Pagination page={runPage} totalPages={runTotalPages} total={runs.length} itemLabel="评测批次" disabled={runsLoading} onPageChange={setRunPage} /> : null}
    </section>
    {message ? <p className="form-message">{message}</p> : null}{error ? <p className="form-message">{error}</p> : null}
  </div>;
}
