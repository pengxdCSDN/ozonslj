import { useState } from "react";
import { inspectPerformanceCredentials, type PerformanceCredentialStatus } from "./api";

export function PerformanceCredentialsView() {
  const [result, setResult] = useState<PerformanceCredentialStatus | null>(null);
  const [message, setMessage] = useState("");
  const inspect = async () => { try { setResult(await inspectPerformanceCredentials({ client_id: "configured", refresh_token: "backend-secret" })); setMessage(""); } catch (error) { setMessage(error instanceof Error ? error.message : "凭据检查失败"); } };
  return <div className="view-content"><PageHeading label="工作区 / WSP-008" title="Performance 凭据" note="与 Seller 凭据隔离，浏览器端不保存令牌正文" compact /><section className="panel"><div className="section-heading"><div><p className="eyebrow">Performance API</p><h2>凭据状态</h2></div><button className="secondary-button" onClick={() => void inspect()}>检查状态</button></div>{message ? <p className="form-message">{message}</p> : null}{result ? <div className="quality-result"><strong>{result.credential_scope} · {result.ready ? "已就绪" : "未就绪"}</strong><span>Client ID：{result.client_id_present ? "已配置" : "未配置"} · Access Token：{result.access_token_present ? "已配置" : "未配置"}</span><span>Refresh Token：{result.refresh_token_present ? "已配置" : "未配置"} · Seller 隔离：{result.isolated_from_seller ? "是" : "否"}</span></div> : <div className="empty-search"><strong>尚未检查 Performance 凭据</strong><span>页面只展示状态，不展示凭据或令牌内容。</span></div>}</section></div>;
}
function PageHeading({ label, title, note, compact }: { label: string; title: string; note: string; compact?: boolean }) { return <section className={`page-heading ${compact ? "compact" : ""}`}><div><p className="eyebrow">{label}</p><h1>{title}</h1><p>{note}</p></div></section>; }
