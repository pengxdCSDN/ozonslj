import { useState } from "react";
import { listExternalNotificationConfigs, previewExternalNotification, validateAndSaveExternalNotification, type ExternalNotificationConfig } from "./api";

export function ExternalNotificationsView({ workspaceId }: { workspaceId: string }) {
  const [configs, setConfigs] = useState<ExternalNotificationConfig[]>([]);
  const [message, setMessage] = useState("外部通知默认仅预览，不发送真实消息。");
  const [busy, setBusy] = useState(false);
  const preview = async () => { setBusy(true); try { setMessage(`模板预览：${await previewExternalNotification("{{headline}} · {{summary}}", { headline: "库存提醒", summary: "有 1 个商品需要关注" })}`); } catch { setMessage("模板预览失败。"); } finally { setBusy(false); } };
  const save = async () => { setBusy(true); try { const config = await validateAndSaveExternalNotification(workspaceId, { channel: "feishu", enabled: false, template: "{{headline}}", retry_limit: 2, sensitive_data_allowed: false }); setConfigs((current) => [config, ...current]); setMessage("通知配置已保存。"); } catch { setMessage("保存配置失败。"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setConfigs(await listExternalNotificationConfigs(workspaceId)); setMessage("已加载通知配置历史。"); } catch { setMessage("加载历史失败。"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Reports & Assistant / AI-010</p><h1>外部通知</h1><p>通知默认仅预览，不发送真实消息。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">渠道配置</p><h2>通知安全校验</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void preview()}>预览模板</button><button className="secondary-button" disabled={busy} onClick={() => void save()}>保存配置</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message" role="status">{message}</p>{configs.map((config, index) => <div className="quality-result" key={`${config.channel}-${index}`}><strong>{config.channel} · 仅预览</strong><span>模板：{config.template}</span><small>重试 {config.retry_limit} 次 · 敏感数据：禁止</small></div>)}{!configs.length ? <div className="empty-search"><strong>尚未校验通知配置</strong><span>默认不发送敏感数据，也不连接真实通知渠道。</span></div> : null}</section></div>;
}
