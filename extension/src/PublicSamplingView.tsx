import { useState } from "react";
import { checkAndRecordPublicSampling, type SamplingResult } from "./api";

export function PublicSamplingView({ workspaceId }: { workspaceId: string }) {
  const [urls, setUrls] = useState("https://example.com/item");
  const [globalLimit, setGlobalLimit] = useState(2);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [results, setResults] = useState<SamplingResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("受控采样默认全局并发 2、单域名串行");

  const run = async () => {
    setBusy(true);
    try {
      const next = await checkAndRecordPublicSampling(
        workspaceId,
        urls.split("\n").map((url) => url.trim()).filter(Boolean),
        globalLimit,
        maxAttempts,
      );
      setResults(next);
      setMessage("采样预览完成，被阻止的请求已记录到质量中心");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "采样失败");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div><p className="eyebrow">公开采样 / RES-006</p><h1>低并发采样预览</h1><p>全局并发最多 2，单域名串行；429/503 按退避策略重试，不绕过访问限制。</p></div></section>
    <section className="panel import-panel public-sampling-panel">
      <label>受控 URL（每行一个）<textarea rows={6} value={urls} onChange={(event) => setUrls(event.target.value)} /></label>
      <div className="form-grid"><label>全局并发上限<input type="number" min={1} max={2} value={globalLimit} onChange={(event) => setGlobalLimit(Number(event.target.value))} /></label><label>最大重试次数<input type="number" min={1} max={5} value={maxAttempts} onChange={(event) => setMaxAttempts(Number(event.target.value))} /></label></div>
      <button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "采样中…" : "执行并记录预览"}</button>
      <p className="form-message">{message}</p>
      {results.map((result) => <div className="operation-row" key={result.url}><span><strong>{result.url}</strong><small>{result.message} · 尝试 {result.attempts} 次</small></span><em>{result.allowed ? `完成 · ${result.status_code ?? "无状态码"}` : "已阻止"}</em></div>)}
      {!results.length ? <div className="empty-search"><strong>尚未执行采样</strong><span>仅允许受控竞品种子进入采样流程。</span></div> : null}
    </section>
  </div>;
}
