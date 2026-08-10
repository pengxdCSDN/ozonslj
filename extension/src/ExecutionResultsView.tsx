import { useState } from "react";
import { listExecutionResults, saveExecutionResult, type StoredExecutionResult } from "./api";

const sampleItems = [{ item_id: "SKU-001", success: true, message: "价格已回读" }, { item_id: "SKU-002", success: false, message: "接口拒绝，需要人工复核" }];

export function ExecutionResultsView({ workspaceId }: { workspaceId: string }) {
  const [records, setRecords] = useState<StoredExecutionResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("等待保存执行结果");
  const load = async () => { setBusy(true); try { setRecords(await listExecutionResults(workspaceId)); setMessage("已加载工作区执行历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "执行历史加载失败"); } finally { setBusy(false); } };
  const save = async () => { setBusy(true); try { const record = await saveExecutionResult(workspaceId, sampleItems); setRecords((current) => [record, ...current]); setMessage("执行结果已保存，可继续追踪部分失败项"); } catch (error) { setMessage(error instanceof Error ? error.message : "执行结果保存失败"); } finally { setBusy(false); } };
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">受控执行 / REV-008</p><h2>分项执行结果</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void save()}>保存 Stub 结果</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{records.length ? records.map((record) => <div className="quality-result" key={record.result_id}><strong>{record.result.status} · 成功 {record.result.succeeded} · 失败 {record.result.failed}</strong><small>{record.created_at} · {record.result_id}</small>{record.result.items.map((item) => <div className="operation-row" key={`${record.result_id}-${item.item_id}`}><span><strong>{item.item_id}</strong><small>{item.message}</small></span><em>{item.success ? "成功" : "失败"}</em></div>)}</div>) : <div className="empty-search"><strong>暂无执行结果</strong><span>批量操作会保留每项成功、失败和失败原因。</span></div>}</section>;
}
