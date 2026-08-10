import { useEffect, useState } from "react";
import { approveManualApproval, createManualApproval, listPendingManualApprovals, type ManualApproval } from "./api";

export function ManualApprovalView({ workspaceId }: { workspaceId: string }) {
  const [items, setItems] = useState<ManualApproval[]>([]);
  const [message, setMessage] = useState("审批与外部写入执行器分离，未批准请求不会进入执行链路。");
  const [busy, setBusy] = useState(false);
  const load = async () => { setBusy(true); try { setItems(await listPendingManualApprovals(workspaceId)); } catch { setMessage("加载审批队列失败。"); } finally { setBusy(false); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const create = async () => { setBusy(true); try { await createManualApproval(workspaceId, { command_type: "price_change", idempotency_key: `price-change-${Date.now()}`, payload: { sku: "SKU-001", old_price_minor: 250000, new_price_minor: 270000 } }); setMessage("审批请求已创建。"); await load(); } catch { setMessage("创建审批请求失败。"); } finally { setBusy(false); } };
  const approve = async (item: ManualApproval) => { setBusy(true); try { await approveManualApproval(item.approval_id, "运营人员"); setMessage("人工批准已记录，后续仍需独立执行器处理。"); await load(); } catch { setMessage("批准失败。"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Review / REV-003</p><h1>人工批准</h1><p>查看待审批请求，批准后才允许进入独立执行器。</p></div></section><section className="panel"><button className="secondary-button" disabled={busy} onClick={() => void create()}>创建价格变更审批</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新队列</button><p className="form-message" role="status">{message}</p>{items.length ? items.map((item) => <div className="operation-row" key={item.approval_id}><span><strong>{item.command_type}</strong><small>{item.approval_id} · 幂等键 {item.idempotency_key}</small></span><em>{item.status}</em><button className="text-button" disabled={busy} onClick={() => void approve(item)}>人工批准</button></div>) : <div className="empty-search"><strong>暂无待审批请求</strong><span>未批准请求不会进入执行器。</span></div>}</section></div>;
}
