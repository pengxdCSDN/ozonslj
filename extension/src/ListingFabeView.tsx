import { useEffect, useState } from "react";
import { generateAndSaveFabeDraft, listFabeDraftHistory, type ListingFabeDraft } from "./api";

export function ListingFabeView({ workspaceId }: { workspaceId: string }) {
  const [drafts, setDrafts] = useState<ListingFabeDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("FABE 草稿保留证据缺失提示，不自动发布");
  const load = async () => { try { setDrafts(await listFabeDraftHistory(workspaceId)); setMessage("已加载 FABE 历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "FABE 历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { setBusy(true); try { await generateAndSaveFabeDraft(workspaceId, { product_name: "термос", points: [{ feature: "500 мл", advantage: "нержавеющая сталь", benefit: "сохраняет температуру", evidence: "паспорт материала", copy: "Термос 500 мл из нержавеющей стали для ежедневного использования." }] }); setMessage("FABE 草稿已保存"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "FABE 草稿保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-005</p><h1>FABE 与长描述</h1><p>生成卖点、长描述和主图文案建议，保留证据缺失提示。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "生成并保存中…" : "生成并保存 FABE 草稿"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近草稿</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{drafts.length ? drafts.map((draft, index) => <article className="history-item" key={`${draft.long_description}-${index}`}><strong>{draft.bullets.length} 个卖点 · {draft.editable ? "可编辑" : "只读"}</strong><span>{draft.long_description}</span><small>主图建议：{draft.image_copy_suggestions.join("；") || "无"} · 缺失证据：{draft.missing_evidence.join("、") || "无"}</small></article>) : <div className="empty-search"><strong>暂无 FABE 草稿</strong><span>草稿仍需人工修改和风险检查。</span></div>}</section></div>;
}
