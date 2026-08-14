import { useEffect, useState } from "react";
import { getPerformanceCredentialStatus, savePerformanceCredentials, type PerformanceCredentialStatus } from "./api";

interface Props { workspaceId: string; }

export function PerformanceOAuthView({ workspaceId }: Props) {
  const [status, setStatus] = useState<PerformanceCredentialStatus | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [clientIdPresent, setClientIdPresent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = async () => {
    setBusy(true);
    try {
      setStatus(await getPerformanceCredentialStatus(workspaceId));
      setMessage("");
    } catch {
      setStatus(null);
      setMessage("尚未保存 Performance 凭据，请先填写并保存访问令牌。");
    } finally { setBusy(false); }
  };

  useEffect(() => { void load(); }, [workspaceId]);

  const save = async () => {
    if (!accessToken.trim() || !expiresAt) {
      setMessage("请填写访问令牌和过期时间。");
      return;
    }
    setBusy(true);
    try {
      const saved = await savePerformanceCredentials(workspaceId, {
        client_id_present: clientIdPresent,
        access_token: accessToken,
        refresh_token: refreshToken || null,
        expires_at: new Date(expiresAt).toISOString(),
      });
      setStatus(saved);
      setAccessToken("");
      setRefreshToken("");
      setMessage("凭据已加密保存，令牌输入框已清空。");
    } catch {
      setMessage("保存失败，请检查令牌和过期时间后重试。");
    } finally { setBusy(false); }
  };

  return <div className="view-content">
    <section className="page-heading compact">
      <div><p className="eyebrow">工作区 / WSP-008</p><h1>Performance 凭据</h1><p>配置 Performance API 凭据；令牌仅加密保存在后端，浏览器不会保留明文。</p></div>
    </section>
    <section className="panel credential-panel">
      <div className="section-heading"><div><p className="eyebrow">安全配置</p><h2>凭据配置</h2></div><button className="secondary-button" disabled={busy} onClick={() => void load()}>检查状态</button></div>
      <div className="credential-form">
        <div className="form-title"><span>01</span><div><h2>Performance OAuth</h2><p>填写令牌后保存，保存成功后输入框会自动清空。</p></div></div>
        <label>访问令牌<input type="password" value={accessToken} onChange={(event) => setAccessToken(event.target.value)} autoComplete="off" placeholder="粘贴访问令牌" /></label>
        <label>刷新令牌（可选）<input type="password" value={refreshToken} onChange={(event) => setRefreshToken(event.target.value)} autoComplete="off" placeholder="用于后续刷新访问令牌" /></label>
        <label>过期时间<input type="datetime-local" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} /></label>
        <label className="credential-check"><input type="checkbox" checked={clientIdPresent} onChange={(event) => setClientIdPresent(event.target.checked)} /> OAuth Client ID 已配置</label>
        <button className="primary-button" disabled={busy} onClick={() => void save()}>{busy ? "保存中…" : "加密保存凭据"}</button>
      </div>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </section>
    <section className="panel credential-panel">
      <div className="section-heading"><div><p className="eyebrow">Performance API</p><h2>当前状态</h2></div></div>
      {status ? <div className="quality-result"><strong>{status.credential_scope} · {status.ready ? "已就绪" : "未就绪"}</strong><span>Client ID：{status.client_id_present ? "已配置" : "未配置"} · Access Token：{status.access_token_present ? "已配置" : "未配置"}</span><span>Refresh Token：{status.refresh_token_present ? "已配置" : "未配置"} · Seller 隔离：{status.isolated_from_seller ? "是" : "否"}</span><small>过期时间：{status.expires_at ?? "未配置"}</small></div> : <div className="empty-search"><strong>尚未读取 Performance 凭据状态</strong><span>保存凭据后点击“检查状态”，这里只展示状态，不展示令牌内容。</span></div>}
    </section>
  </div>;
}
