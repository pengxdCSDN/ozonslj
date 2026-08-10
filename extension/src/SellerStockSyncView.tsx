import { useEffect, useState } from "react";

import { listSellerStockSnapshots, previewSellerStockSync, saveSellerStockSync, type SellerStockSyncPreview } from "./api";

const previewResponse = {
  items: [{ offer_id: "SKU-1", warehouse_id: "WH-1", available_quantity: 8, reserved_quantity: 2 }],
  total: 1,
};

export function SellerStockSyncView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<SellerStockSyncPreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<SellerStockSyncPreview[]>([]);

  useEffect(() => {
    void listSellerStockSnapshots(workspaceId).then(setHistory).catch(() => setHistory([]));
  }, [workspaceId]);

  const preview = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await previewSellerStockSync(previewResponse));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "库存同步预览失败");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await saveSellerStockSync(workspaceId, previewResponse));
      setHistory(await listSellerStockSnapshots(workspaceId));
      setMessage("库存快照已保存到当前工作区");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "库存快照保存失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <p className="eyebrow">Seller 数据 / DAT-010</p>
          <h1>库存同步预览</h1>
          <p>将 Seller API 库存响应映射为仓位快照；当前仅执行只读预览。</p>
        </div>
      </section>
      <section className="panel"><div className="section-heading"><h2>最近库存快照</h2><span>{history.length} 条</span></div>{history.length ? history.map((snapshot, index) => <div className="operation-row" key={`${snapshot.next_cursor ?? "end"}-${index}`}><span><strong>{snapshot.source}</strong><small>仓位总数：{snapshot.total} · 下一游标：{snapshot.next_cursor ?? "已完成"}</small></span><em>仅展示摘要</em></div>) : <p className="empty-search">暂无历史快照。</p>}</section>
      <section className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">官方私有数据</p><h2>库存仓位</h2></div>
          <div className="button-group">
            <button className="secondary-button" disabled={busy} onClick={() => void preview()}>{busy ? "处理中…" : "运行预览"}</button>
            <button className="secondary-button" disabled={busy || !result} onClick={() => void save()}>保存快照</button>
          </div>
        </div>
        {message ? <p className="form-message" role="alert">{message}</p> : null}
        {result ? (
          <>
            <div className="metric-grid">
              <article><span>当前页仓位</span><strong>{result.items.length}</strong></article>
              <article><span>总数量</span><strong>{result.total}</strong></article>
            </div>
            {result.items.map((item) => (
              <div className="operation-row" key={`${item.offer_id}-${item.warehouse_id}`}>
                <span><strong>{item.offer_id}</strong><small>{item.warehouse_id} · {item.source}</small></span>
                <b>{item.available_quantity} 可售</b>
                <em>{item.reserved_quantity} 预留</em>
              </div>
            ))}
          </>
        ) : (
          <div className="empty-search">
            <strong>尚未运行 Seller 库存预览</strong>
            <span>真实接口核对完成后，再接入后端凭据与增量 Worker。</span>
          </div>
        )}
      </section>
    </div>
  );
}
