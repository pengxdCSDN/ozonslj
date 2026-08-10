import { useEffect, useState } from "react";

import { listSellerFulfillmentSnapshots, previewSellerFulfillmentSync, saveSellerFulfillmentSync, type SellerFulfillmentSyncPreview } from "./api";

const previewResponse = {
  items: [
    { posting_id: "P-1", fulfillment_type: "FBO", status: "awaiting", shipment_date: "2026-08-09", item_count: 1, total_quantity: 2 },
    { posting_id: "P-2", fulfillment_type: "FBS", status: "shipped", shipment_date: null, item_count: 2, total_quantity: 3 },
  ],
  total: 2,
};

export function SellerFulfillmentSyncView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<SellerFulfillmentSyncPreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<SellerFulfillmentSyncPreview[]>([]);

  useEffect(() => {
    void listSellerFulfillmentSnapshots(workspaceId).then(setHistory).catch(() => setHistory([]));
  }, [workspaceId]);

  const preview = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await previewSellerFulfillmentSync(previewResponse));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "履约同步预览失败");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await saveSellerFulfillmentSync(workspaceId, previewResponse));
      setHistory(await listSellerFulfillmentSnapshots(workspaceId));
      setMessage("履约快照已保存到当前工作区");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "履约快照保存失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <p className="eyebrow">Seller 数据 / DAT-012</p>
          <h1>FBO/FBS 履约同步</h1>
          <p>将 Seller API 履约响应映射为只读 posting 摘要；当前不执行外部写入。</p>
        </div>
      </section>
      <section className="panel"><div className="section-heading"><h2>最近履约快照</h2><span>{history.length} 条</span></div>{history.length ? history.map((snapshot, index) => <div className="operation-row" key={`${snapshot.next_cursor ?? "end"}-${index}`}><span><strong>{snapshot.source}</strong><small>Posting 总数：{snapshot.total} · 下一游标：{snapshot.next_cursor ?? "已完成"}</small></span><em>仅展示摘要</em></div>) : <p className="empty-search">暂无历史快照。</p>}</section>
      <section className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">官方私有数据</p><h2>履约单</h2></div>
          <div className="button-group">
            <button className="secondary-button" disabled={busy} onClick={() => void preview()}>{busy ? "处理中…" : "运行预览"}</button>
            <button className="secondary-button" disabled={busy || !result} onClick={() => void save()}>保存快照</button>
          </div>
        </div>
        {message ? <p className="form-message" role="alert">{message}</p> : null}
        {result ? (
          <>
            <div className="metric-grid">
              <article><span>当前页履约单</span><strong>{result.items.length}</strong></article>
              <article><span>总履约单数</span><strong>{result.total}</strong></article>
            </div>
            {result.items.map((item) => (
              <div className="operation-row" key={item.posting_id}>
                <span><strong>{item.posting_id} · {item.fulfillment_type}</strong><small>{item.shipment_date ?? "待排期"} · {item.status}</small></span>
                <b>{item.total_quantity} 件</b>
                <em>{item.source}</em>
              </div>
            ))}
          </>
        ) : (
          <div className="empty-search">
            <strong>尚未运行 Seller 履约预览</strong>
            <span>真实接口核对完成后，再接入后端凭据与增量 Worker。</span>
          </div>
        )}
      </section>
    </div>
  );
}
