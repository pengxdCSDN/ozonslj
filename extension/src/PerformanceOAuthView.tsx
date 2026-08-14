import { useEffect, useState } from "react";
import { getPerformanceCredentialStatus, savePerformanceClientCredentials, requestPerformanceToken, type PerformanceCredentialStatus } from "./api";

interface Props { workspaceId: string; }

export function PerformanceOAuthView({ workspaceId }: Props) {
  const [status, setStatus] = useState<PerformanceCredentialStatus | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = async () => {
    setBusy(true);
    try { setStatus(await getPerformanceCredentialStatus(workspaceId)); setMessage(""); }
    catch { setStatus(null); setMessage("尚未配置 Performance Client ID 和 Client Secret。"); }
    finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, [workspaceId]);

  const save = async () => {
    if (!clientId.trim() || !clientSecret.trim()) { setMessage("请填写 Client ID 和 Client Secret。"); return; }
    setBusy(true);
    try {
      setStatus(await savePerformanceClientCredentials(workspaceId, { client_id: clientId, client_secret: clientSecret }));
      setClientSecret("");
      setMessage("Client ID 和 Client Secret 已加密保存。");
    } catch (error) { setMessage(error instanceof Error ? error.message : "保存失败，请检查字段后重试。"); }
    finally { setBusy(false); }
  };

  const fetchToken = async () => {
    setBusy(true);
    try { setStatus(await requestPerformanceToken(workspaceId)); setMessage("Performance API Token 获取成功，连接已验证。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Token 获取失败，请检查 Client ID 和 Secret。"); }
    finally { setBusy(false); }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div><p className="eyebrow">工作区 / WSP-008</p><h1>Performance 凭据</h1><p>使用 Ozon Performance 服务账号访问广告数据；密钥仅加密保存在后端。</p></div></section>
    <section className="panel credential-panel">
      <div className="section-heading"><div><p className="eyebrow">Client Credentials</p><h2>连接配置</h2></div><button className="secondary-button" disabled={busy} onClick={() => void load()}>检查状态</button></div>
      <div className="credential-form">
        <div className="form-title"><span>01</span><div><h2>Ozon Performance 服务账号</h2><p>从 Ozon Seller 的“分析 → 外部流量 → 服务账号”获取这两个值。</p></div></div>
        <label>Client ID<input value={clientId} onChange={(event) => setClientId(event.target.value)} autoComplete="off" placeholder="粘贴 Performance Client ID" /></label>
        <label>Client Secret<input type="password" value={clientSecret} onChange={(event) => setClientSecret(event.target.value)} autoComplete="new-password" placeholder="粘贴 Performance Client Secret" /></label>
        <div className="credential-actions"><button className="primary-button" disabled={busy} onClick={() => void save()}>加密保存密钥</button><button className="secondary-button" disabled={busy} onClick={() => void fetchToken()}>获取 Token 并测试连接</button></div>
      </div>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </section>
    <section className="panel credential-panel"><div className="section-heading"><div><p className="eyebrow">Performance API</p><h2>连接状态</h2></div></div>{status ? <div className="quality-result"><strong>{status.credential_scope} · {status.ready ? "已就绪" : "未就绪"}</strong><span>Client ID：{status.client_id_present ? "已配置" : "未配置"} · Access Token：{status.access_token_present ? "已获取" : "未获取"}</span><small>Token 过期时间：{status.expires_at ?? "未获取"} · Seller 隔离：{status.isolated_from_seller ? "是" : "否"}</small></div> : <div className="empty-search"><strong>尚未读取 Performance 连接状态</strong><span>保存密钥后点击“获取 Token 并测试连接”。</span></div>}</section>
  </div>;
}
