import { ChatCircleText, Paperclip, ShieldCheck } from "@phosphor-icons/react";
import { useState } from "react";
import { queryKnowledge, submitKnowledgeFeedback, type KnowledgeAnswer } from "./api";

export function KnowledgeQueryView() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<KnowledgeAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const submit = async () => {
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    try { setResult(await queryKnowledge(question.trim())); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "知识检索失败，请稍后重试"); }
    finally { setBusy(false); }
  };
  const sendFeedback = async (reason: string) => {
    if (!result) return;
    try { await submitKnowledgeFeedback(result.answer_id, reason); setFeedback("反馈已记录"); }
    catch (reasonError) { setFeedback(reasonError instanceof Error ? reasonError.message : "反馈提交失败"); }
  };
  return <div className="view-content">
    <div className="page-heading"><span className="eyebrow">知识中心 / RAG</span><h1>知识问答</h1><p>只基于已发布知识片段回答，并展示可追溯引用。</p></div>
    <section className="panel">
      <div className="section-heading"><div><span className="eyebrow">混合检索</span><h2>向知识库提问</h2></div><ShieldCheck size={24} /></div>
      <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：如何使用 RAG？" rows={4} aria-label="知识问题" />
      <div className="sync-actions"><button type="button" className="primary-button" onClick={() => void submit()} disabled={busy || !question.trim()}><ChatCircleText size={17} />{busy ? "检索中…" : "开始检索"}</button><span className="muted-note"><Paperclip size={14} />回答会附带来源和片段引用</span></div>
      {error ? <p className="form-message">{error}</p> : null}
      {result ? <div className="quality-result"><strong>{result.status === "answered" ? "已找到证据" : "需要进一步处理"}</strong>{result.segments.map((segment) => <article className="operation-row" key={`${segment.text}-${segment.intent}`}><span><strong>{segment.answer}</strong><small>{segment.status} · {segment.normalized_query}</small>{segment.reason ? <small>{segment.reason}</small> : null}</span><em>{segment.citations.length ? `${segment.citations.length} 条引用` : "无引用"}</em></article>)}<small>{result.message} · 追踪 {result.trace_id.slice(0, 8)}</small><div className="sync-actions"><button type="button" className="secondary-button" onClick={() => void sendFeedback("helpful")}>有帮助</button><button type="button" className="secondary-button" onClick={() => void sendFeedback("incorrect")}>需要纠正</button>{feedback ? <span className="muted-note">{feedback}</span> : null}</div></div> : null}
    </section>
  </div>;
}
