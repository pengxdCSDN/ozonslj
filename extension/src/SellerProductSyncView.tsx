import { useEffect, useState } from "react";

import { listSellerProductSnapshots, previewSellerProductSync, saveSellerProductSync, type SellerProductSyncPreview } from "./api";

const previewResponse = {
  items: [{
    offer_id: "SKU-1",
    ozon_product_id: "123",
    name: "Demo Seller Product",
    price_minor: 129000,
    currency: "RUB",
    available_stock: 7,
  }],
  total: 1,
};

export function SellerProductSyncView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<SellerProductSyncPreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<SellerProductSyncPreview[]>([]);

  useEffect(() => {
    void listSellerProductSnapshots(workspaceId).then(setHistory).catch(() => setHistory([]));
  }, [workspaceId]);

  const preview = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await previewSellerProductSync(previewResponse));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "商品同步预览失败");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      setResult(await saveSellerProductSync(workspaceId, previewResponse));
      setHistory(await listSellerProductSnapshots(workspaceId));
      setMessage("商品快照已保存到当前工作区");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "商品快照保存失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <p className="eyebrow">Seller 数据 / DAT-009</p>
          <h1>商品同步预览</h1>
          <p>将 Seller API 商品响应映射为内部商品模型；当前不访问真实账号。</p>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">官方私有数据</p><h2>商品同步结果</h2></div>
          <div className="button-group">
            <button className="secondary-button" disabled={busy} onClick={() => void preview()}>{busy ? "处理中…" : "运行预览"}</button>
            <button className="secondary-button" disabled={busy || !result} onClick={() => void save()}>保存快照</button>
          </div>
        </div>
        {message ? <p className="form-message" role="alert">{message}</p> : null}
        {result ? (
          <>
            <div className="metric-grid">
              <article><span>当前页商品</span><strong>{result.items.length}</strong></article>
              <article><span>商品总数</span><strong>{result.total}</strong></article>
            </div>
            {result.items.map((item) => (
              <div className="operation-row" key={item.offer_id}>
                <span><strong>{item.name}</strong><small>{item.offer_id} · {item.source}</small></span>
                <b>{item.available_stock} 件</b>
                <em>{item.currency} {item.price_minor}</em>
              </div>
            ))}
          </>
        ) : (
          <div className="empty-search">
            <strong>尚未运行 Seller 商品预览</strong>
            <span>真实接口路径和权限核对完成后，再接入后端凭据与增量 Worker。</span>
          </div>
        )}
      </section>
      <section className="panel"><div className="section-heading"><h2>最近商品快照</h2><span>{history.length} 条</span></div>{history.length ? history.map((snapshot, index) => <div className="operation-row" key={`${snapshot.next_cursor ?? "end"}-${index}`}><span><strong>{snapshot.source}</strong><small>商品总数：{snapshot.total} · 下一游标：{snapshot.next_cursor ?? "已完成"}</small></span><em>仅展示摘要</em></div>) : <p className="empty-search">暂无历史快照。</p>}</section>
    </div>
  );
}
