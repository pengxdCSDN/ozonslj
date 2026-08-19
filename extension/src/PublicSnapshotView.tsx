import { useEffect, useState } from "react";
import { listPublicSnapshotHistory, normalizePublicSnapshot, savePublicSnapshot, type PublicSnapshot } from "./api";

export function PublicSnapshotView({ workspaceId }: { workspaceId: string }) {
  const [url, setUrl] = useState("https://example.com/item");
  const [snapshots, setSnapshots] = useState<PublicSnapshot[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("尚未保存公开快照");

  const load = async () => {
    try {
      setSnapshots(await listPublicSnapshotHistory(workspaceId));
      setMessage("已加载公开快照历史");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "快照历史加载失败");
    }
  };

  useEffect(() => { void load(); }, [workspaceId]);

  const run = async () => {
    setBusy(true);
    try {
      const payload = {
        url, title: "示例商品", price_minor: 1299, currency: "RUB", rating: "4.8",
        review_count: 3, image_url: "https://example.com/image.jpg",
        attributes: { source: "public_sample", material: "sample" }, sample_size: 1,
      };
      await normalizePublicSnapshot(payload);
      await savePublicSnapshot(workspaceId, payload);
      setMessage("公开快照已规范化并保存");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "公开快照保存失败");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">公开样本 / RES-007</p><h1>快照规范化</h1><p>保存标题、价格、评分、评价数、主图、属性、采样时间和样本范围；不保存原始 HTML。</p></div></section>
    <section className="panel import-panel public-snapshot-panel"><label>公开页面 URL<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} /></label><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "规范化中…" : "规范化并保存"}</button><p className="form-message">{message}</p></section>
    <section className="panel"><div className="panel-heading"><h2>最近快照</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{snapshots.length ? snapshots.map((snapshot, index) => <article className="history-item" key={`${snapshot.url}-${snapshot.sampled_at}-${index}`}><strong>{snapshot.title ?? snapshot.url}</strong><span>{snapshot.price_minor ?? "未提供"} {snapshot.currency ?? ""} · 评分 {snapshot.rating ?? "未提供"} · 评价 {snapshot.review_count ?? "未提供"}</span><small>{snapshot.sampled_at} · 样本 {snapshot.sample_size} · {snapshot.estimated ? "采样估算" : "官方事实"} · 属性 {Object.keys(snapshot.attributes).length} 项</small></article>) : <div className="empty-search"><strong>暂无公开快照</strong><span>规范化后的公开字段会保留采样时间和估算标记。</span></div>}</section>
  </div>;
}
