import { useState } from "react";
import { listAuditEvents, saveAuditEvent, type StoredAuditEvent } from "./api";

export function AuditEventsView({ workspaceId }: { workspaceId: string }) {
  const [events, setEvents] = useState<StoredAuditEvent[]>([]);
  const [message, setMessage] = useState("审计覆盖预览、批准、执行、回读和最终结果");
  const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { const event = await saveAuditEvent(workspaceId, { event_type: "readback_verified", subject_id: "price-change-SKU-001-v1", detail: { matched: true } }); setEvents((current) => [event, ...current]); setMessage("审计事件已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "审计事件保存失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setEvents(await listAuditEvents(workspaceId)); setMessage("已加载审计历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "审计历史加载失败"); } finally { setBusy(false); } };
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">受控执行 / REV-010</p><h2>全程审计</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void save()}>记录审计事件</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{events.length ? events.map((item) => <div className="operation-row" key={item.event_id}><span><strong>{item.event.event_type}</strong><small>{item.event.subject_id} · {item.event.occurred_at}</small><small>详情：{Object.entries(item.event.detail).map(([key, value]) => `${key}=${String(value)}`).join("；") || "无"}</small></span><em>已记录</em></div>) : <div className="empty-search"><strong>暂无审计事件</strong><span>每个受控写入阶段都必须留下可追溯事件。</span></div>}</section>;
}
