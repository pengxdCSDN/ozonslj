import { useEffect, useState } from "react";
import { getPerformanceCredentialStatus, PerformanceCredentialStatus, savePerformanceCredentials } from "./api";

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
    try { setStatus(await getPerformanceCredentialStatus(workspaceId)); setMessage(""); }
    catch { setStatus(null); setMessage("尚未保存 Performance 凭据，或当前工作区没有凭据。"); }
    finally { setBusy(false); }
  };

  useEffect(() => { void load(); }, [workspaceId]);

  const save = async () => {
    if (!accessToken || !expiresAt) { setMessage("请填写访问令牌和过期时间。"); return; }
    setBusy(true);
    try {
      const saved = await savePerformanceCredentials(workspaceId, {
        client_id_present: clientIdPresent,
        access_token: accessToken,
        refresh_token: refreshToken || null,
        expires_at: new Date(expiresAt).toISOString(),
      });
      setStatus(saved); setAccessToken(""); setRefreshToken(""); setMessage("凭据已加密保存，页面已清空令牌输入。");
    } catch { setMessage("保存失败，请检查令牌和过期时间后重试。"); }
    finally { setBusy(false); }
  };

  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill</p><h1>Performance OAuth</h1><p>Performance API 使用独立凭据，令牌只在后端加密保存。</p></div></section><section className="panel import-panel"><label>访问令牌<input type="password" value={accessToken} onChange={(event) => setAccessToken(event.target.value)} autoComplete="off" /></label><label>刷新令牌（可选）<input type="password" value={refreshToken} onChange={(event) => setRefreshToken(event.target.value)} autoComplete="off" /></label><label>过期时间<input type="datetime-local" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} /></label><label><input type="checkbox" checked={clientIdPresent} onChange={(event) => setClientIdPresent(event.target.checked)} /> OAuth Client ID 已配置</label><button className="primary-button" disabled={busy} onClick={() => void save()}>{busy ? "处理中…" : "加密保存凭据"}</button>{message ? <p role="status">{message}</p> : null}{status ? <div className="quality-result"><strong>{status.credential_scope} · {status.ready ? "可用" : "需要检查"}</strong><span>过期时间：{status.expires_at ?? "未配置"}</span><small>访问令牌：{status.access_token_present ? "已配置" : "未配置"} · 刷新令牌：{status.refresh_token_present ? "已配置" : "未配置"} · 与 Seller 凭据隔离：{status.isolated_from_seller ? "是" : "否"}</small></div> : null}</section></div>;
}
