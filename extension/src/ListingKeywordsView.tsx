import { useEffect, useState } from "react";
import { listListingKeywordHistory, normalizeAndSaveListingKeyword, type ListingKeyword } from "./api";

export function ListingKeywordsView({ workspaceId }: { workspaceId: string }) {
  const [keyword, setKeyword] = useState("");
  const [layer, setLayer] = useState<ListingKeyword["layer"]>("core");
  const [productScope, setProductScope] = useState("当前 SKU");
  const [history, setHistory] = useState<ListingKeyword[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("关键词需保留来源、语言、分层和适用商品范围");
  const load = async () => { try { setHistory(await listListingKeywordHistory(workspaceId)); setMessage("已加载关键词历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "关键词历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const save = async () => { setBusy(true); try { await normalizeAndSaveListingKeyword(workspaceId, { keyword, source: "operator_imported", observed_at: new Date().toISOString(), language: "ru", layer, product_scope: productScope }); setKeyword(""); setMessage("关键词已归档"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "关键词保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-001</p><h1>关键词库</h1><p>保存来源、统计时间、语言、分层和适用商品范围，支持回看历史记录。</p></div></section><section className="panel import-panel"><label>俄语关键词<input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="例如：термос" /></label><div className="form-grid"><label>关键词分层<select value={layer} onChange={(event) => setLayer(event.target.value as ListingKeyword["layer"])}><option value="core">核心词</option><option value="attribute">属性词</option><option value="scene">场景词</option><option value="long_tail">长尾词</option></select></label><label>适用商品范围<input value={productScope} onChange={(event) => setProductScope(event.target.value)} /></label></div><button className="secondary-button" disabled={!keyword.trim() || busy} onClick={() => void save()}>{busy ? "保存中…" : "归档关键词"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近记录</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{history.length ? history.map((item, index) => <article className="history-item" key={`${item.keyword}-${item.observed_at}-${index}`}><strong>{item.keyword}</strong><span>{item.layer} · {item.language} · {item.product_scope}</span><small>{item.source} · {item.observed_at}</small></article>) : <div className="empty-search"><strong>暂无关键词记录</strong><span>关键词归档后可用于 Listing 草稿和 Smart Search 检查。</span></div>}</section></div>;
}
