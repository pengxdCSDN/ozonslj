import { useEffect, useState } from "react";
import { checkAndSaveDataFreshness, listDataFreshnessHistory, type DataFreshnessDecision } from "./api";

export function DataFreshnessView({ workspaceId }: { workspaceId: string }) {
  const [items, setItems] = useState<DataFreshnessDecision[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true);
    try { setItems(await listDataFreshnessHistory(workspaceId)); }
    catch { setMessage("加载新鲜度历史失败。"); }
    finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, [workspaceId]);

  const run = async () => {
    setBusy(true);
    try {
      const now = new Date();
      await checkAndSaveDataFreshness(workspaceId, {
        data_domain: "seller_product", observed_at: new Date(now.getTime() - 90 * 60 * 1000).toISOString(),
        max_age_seconds: 3600, now: now.toISOString(), last_success_at: now.toISOString(),
        window: "last_sync", latency_seconds: 18, record_count: 3, error_summary: null,
      });
      setMessage("新鲜度判定已保存。");
      await load();
    } catch { setMessage("新鲜度校验失败。"); }
    finally { setBusy(false); }
  };

  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Data Quality / REV-002</p><h1>数据新鲜度校验</h1><p>统一查看最后成功时间、统计窗口、延迟、记录数和错误摘要。</p></div></section><section className="panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>检查并保存新鲜度</button>{message ? <p className="form-message" role="status">{message}</p> : null}</section><section className="panel"><div className="panel-heading"><h2>最近判定</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{items.length ? items.map((item, index) => <article className="history-item" key={`${item.data_domain}-${item.observed_at}-${index}`}><strong>{item.data_domain} · {item.fresh ? "数据新鲜" : "数据已过期"}</strong><span>年龄：{item.age_seconds} 秒 · 窗口：{item.window ?? "-"} · 记录数：{item.record_count ?? "-"}</span><small>最后成功：{item.last_success_at ?? "-"} · 延迟：{item.latency_seconds ?? "-"} 秒 · 错误：{item.error_summary ?? "无"}</small></article>) : <p className="empty-state">暂无新鲜度判定。</p>}</section></div>;
}
