import { useEffect, useState } from "react";
import { classifyAndSaveListingKeywords, listListingLayerHistory, type LayeredKeyword } from "./api";

export function ListingLayeringView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<LayeredKeyword[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("分层结果需要人工复核");
  const load = async () => { try { setResult(await listListingLayerHistory(workspaceId)); setMessage("已加载分层历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "分层历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { setBusy(true); try { await classifyAndSaveListingKeywords(workspaceId, { keywords: ["термос", "500 мл", "термос для похода"], core_terms: ["термос"], attribute_terms: ["500 мл"], scene_terms: ["для похода"] }); setMessage("关键词分层结果已保存"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "关键词分层失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-002</p><h1>关键词分层</h1><p>展示人工词表优先级、自动规则原因和人工确认状态。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "分层并保存中…" : "执行分层并保存"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近分层结果</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{result.length ? result.map((item, index) => <article className="history-item" key={`${item.keyword}-${index}`}><strong>{item.keyword}</strong><span>{item.layer} · {item.manually_confirmed ? "已确认" : "待确认"}</span><small>{item.reason}</small></article>) : <div className="empty-search"><strong>暂无分层历史</strong><span>关键词分层后可用于标题和 Search Attributes 草稿。</span></div>}</section></div>;
}
