import { useEffect, useState } from "react";
import { generateAndSaveListingTitleDraft, listListingTitleDraftHistory, type ListingTitleDraft } from "./api";

export function ListingTitleDraftView({ workspaceId }: { workspaceId: string }) {
  const [drafts, setDrafts] = useState<ListingTitleDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("标题草稿仅供人工修改，不自动发布到 Ozon");
  const load = async () => { try { setDrafts(await listListingTitleDraftHistory(workspaceId)); setMessage("已加载标题草稿历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "标题历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { setBusy(true); try { await generateAndSaveListingTitleDraft(workspaceId, { category: "термосы", core_terms: ["термос"], attribute_terms: ["500 мл", "нержавеющая сталь"], scene_terms: ["для похода"] }); setMessage("标题草稿已保存"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "标题草稿保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-003</p><h1>俄语标题草稿</h1><p>生成可编辑标题建议，查看关键词覆盖和风险；不会自动发布到 Ozon。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "生成并保存中…" : "生成并保存标题草稿"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近草稿</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{drafts.length ? drafts.map((draft, index) => <article className="history-item" key={`${draft.title}-${index}`}><strong>{draft.title}</strong><span>{draft.category} · {draft.character_count} 字符 · {draft.editable ? "可编辑" : "只读"}</span><small>覆盖：{draft.covered_terms.join("、") || "无"} · 缺失：{draft.missing_terms.join("、") || "无"} · 风险：{draft.risks.join("、") || "暂无"}</small></article>) : <div className="empty-search"><strong>暂无标题草稿</strong><span>标题草稿生成后仍需人工修改和风险检查。</span></div>}</section></div>;
}
