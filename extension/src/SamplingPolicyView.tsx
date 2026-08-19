import { useState } from "react";
import { checkAndRecordSamplingPolicy, type SamplingPolicyDecision } from "./api";

export function SamplingPolicyView({ workspaceId }: { workspaceId: string }) {
  const [url, setUrl] = useState("");
  const [robotsAllowed, setRobotsAllowed] = useState(true);
  const [rateLimited, setRateLimited] = useState(false);
  const [stopRequested, setStopRequested] = useState(false);
  const [decision, setDecision] = useState<SamplingPolicyDecision | null>(null);
  const [message, setMessage] = useState("请求发送前必须通过合规策略检查");
  const [busy, setBusy] = useState(false);

  const check = async () => {
    setBusy(true);
    try {
      const next = await checkAndRecordSamplingPolicy(workspaceId, url, robotsAllowed, rateLimited, stopRequested);
      setDecision(next);
      setMessage(next.allowed ? "策略允许，才可进入后续采样流程" : "策略禁止，系统不得发出采样请求");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "策略检查失败");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div><p className="eyebrow">公开采样 / RES-005</p><h1>合规策略检查</h1><p>请求发送前必须检查 HTTPS、robots、限流和停止策略；被禁止时不会发出采样请求。</p></div></section>
    <section className="panel import-panel sampling-policy-panel">
      <label>待检查 URL<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://..." /></label>
      <label className="checkbox-line"><input type="checkbox" checked={robotsAllowed} onChange={(event) => setRobotsAllowed(event.target.checked)} /> robots 允许访问</label>
      <label className="checkbox-line"><input type="checkbox" checked={rateLimited} onChange={(event) => setRateLimited(event.target.checked)} /> 当前域名限流</label>
      <label className="checkbox-line"><input type="checkbox" checked={stopRequested} onChange={(event) => setStopRequested(event.target.checked)} /> 停止采样</label>
      <button className="secondary-button" disabled={!url || busy} onClick={() => void check()}>{busy ? "检查中…" : "检查并记录"}</button>
      <p className="form-message">{message}</p>
      {decision ? <div className="quality-result"><strong>{decision.allowed ? "允许请求" : "禁止请求"}</strong><span>{decision.code} · {decision.message}</span>{decision.normalized_url ? <small>{decision.normalized_url}</small> : null}</div> : null}
    </section>
  </div>;
}
