import { useState } from "react";
import { executeWorkspaceListingPublish, listListingPublishes, type PublishCommand } from "./api";

export function ListingPublishView({ workspaceId }: { workspaceId: string }) {
  const [commands, setCommands] = useState<PublishCommand[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("只有审核通过的版本才能创建受控命令");
  const execute = async () => { setBusy(true); try { const command = await executeWorkspaceListingPublish(workspaceId, { idempotency_key: `cmd-${Date.now()}`, version: 2, status: "approved", requested_text: "Термос 500 мл для похода", readback_text: "Термос 500 мл для похода" }); setCommands((current) => [command, ...current]); setMessage("受控 Stub 命令已记录，真实 Ozon 写入需独立执行器"); } catch (error) { setMessage(error instanceof Error ? error.message : "发布失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setCommands(await listListingPublishes(workspaceId)); setMessage("已加载受控发布历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "发布历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-009</p><h1>受控发布与回读</h1><p>审核、幂等、执行结果和回读状态均可追溯；真实 Ozon 写入由独立执行器负责。</p></div></section><section className="panel import-panel"><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void execute()}>执行受控 Stub 发布</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载发布历史</button></div><p className="form-message">{message}</p>{commands.map((command) => <div className="quality-result" key={command.idempotency_key}><strong>{command.status} · {command.matched ? "回读一致" : "需要复核"}</strong><span>{command.message}</span><span>请求内容：{command.requested_text}</span><small>幂等键：{command.idempotency_key} · 版本 {command.version} · 回读：{command.readback_text ?? "未回读"}</small></div>)}{!commands.length ? <div className="empty-search"><strong>暂无受控发布记录</strong><span>执行后会保留每次发布命令和回读结果。</span></div> : null}</section></div>;
}
