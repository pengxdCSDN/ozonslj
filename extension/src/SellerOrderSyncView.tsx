import { useEffect, useState } from "react";

import { listSellerOrderSnapshots, previewSellerOrderSync, saveSellerOrderSync, type SellerOrderSyncPreview } from "./api";

const previewResponse = {
  items: [{
    order_id: "ORDER-1",
    ordered_at: "2026-08-09T10:00:00Z",
    status: "awaiting_packaging",
    total_amount_minor: 129000,
    currency: "RUB",
    item_count: 2,
  }],
  total: 1,
};

export function SellerOrderSyncView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<SellerOrderSyncPreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<SellerOrderSyncPreview[]>([]);

  useEffect(() => {
    void listSellerOrderSnapshots(workspaceId).then(setHistory).catch(() => setHistory([]));
  }, [workspaceId]);

  const preview = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await previewSellerOrderSync(previewResponse));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "订单同步预览失败");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await saveSellerOrderSync(workspaceId, previewResponse));
      setHistory(await listSellerOrderSnapshots(workspaceId));
      setMessage("订单快照已保存到当前工作区");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "订单快照保存失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <p className="eyebrow">Seller 数据 / DAT-011</p>
          <h1>订单同步预览</h1>
          <p>将 Seller API 订单响应映射为官方订单摘要；当前仅执行只读预览。</p>
        </div>
      </section>
      <section className="panel"><div className="section-heading"><h2>最近订单快照</h2><span>{history.length} 条</span></div>{history.length ? history.map((snapshot, index) => <div className="operation-row" key={`${snapshot.next_cursor ?? "end"}-${index}`}><span><strong>{snapshot.source}</strong><small>订单总数：{snapshot.total} · 下一游标：{snapshot.next_cursor ?? "已完成"}</small></span><em>仅展示摘要</em></div>) : <p className="empty-search">暂无历史快照。</p>}</section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">官方私有数据</p>
            <h2>订单窗口</h2>
          </div>
          <div className="button-group">
            <button className="secondary-button" disabled={busy} onClick={() => void preview()}>
              {busy ? "处理中…" : "运行预览"}
            </button>
            <button className="secondary-button" disabled={busy || !result} onClick={() => void save()}>
              保存快照
            </button>
          </div>
        </div>
        {message ? <p className="form-message" role="alert">{message}</p> : null}
        {result ? (
          <>
            <div className="metric-grid">
              <article><span>当前页订单</span><strong>{result.items.length}</strong></article>
              <article><span>总订单数</span><strong>{result.total}</strong></article>
            </div>
            {result.items.map((item) => (
              <div className="operation-row" key={item.order_id}>
                <span>
                  <strong>{item.order_id}</strong>
                  <small>{new Date(item.ordered_at).toLocaleString("zh-CN")} · {item.status}</small>
                </span>
                <b>{item.item_count} 件</b>
                <em>{item.currency} {item.total_amount_minor}</em>
              </div>
            ))}
          </>
        ) : (
          <div className="empty-search">
            <strong>尚未运行 Seller 订单预览</strong>
            <span>真实接口核对完成后，再接入后端凭据与增量 Worker。</span>
          </div>
        )}
      </section>
    </div>
  );
}
