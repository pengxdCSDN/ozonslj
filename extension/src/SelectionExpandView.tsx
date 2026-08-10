import { useState } from "react";
import { listSelectionExpansions, runAndSaveSelectionExpand, type ExpandResult } from "./api";

const payload = { seed_product: "термос", core_keywords: ["термос", "термос стальной", "термокружка"], related_keywords: ["фляга"], attributes: ["500 мл", "нержавеющая сталь"], scenes: ["поход", "офис"] };

export function SelectionExpandView({ workspaceId }: { workspaceId: string }) {
  const [results, setResults] = useState<ExpandResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Expand 结果需人工确认后进入 Validate");
  const run = async () => { setBusy(true); try { const result = await runAndSaveSelectionExpand(workspaceId, payload); setResults((current) => [result, ...current]); setMessage("Expand 结果已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "Expand 失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setResults(await listSelectionExpansions(workspaceId)); setMessage("已加载 Expand 历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">选品 Skill / SEL-003</p><h1>Expand 关键词扩展</h1><p>从种子商品扩展核心词、属性词、场景词和变体候选，结果不自动上架。</p></div></section><section className="panel import-panel"><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void run()}>生成并保存扩展结果</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div><p className="form-message">{message}</p>{results.map((result, index) => <div className="quality-result" key={`${result.seed_product}-${index}`}><strong>{result.seed_product} · {result.estimated ? "采样估算" : "官方事实"}</strong><span>核心词：{result.core_terms.join("、") || "无"}</span><span>属性词：{result.attribute_terms.join("、") || "无"} · 场景词：{result.scene_terms.join("、") || "无"}</span><small>变体候选：{result.variant_candidates.join("、") || "无"} · 缺失：{result.missing_inputs.join("、") || "无"}</small></div>)}{!results.length ? <div className="empty-search"><strong>尚未生成扩展结果</strong><span>扩展结果需要人工复核后才能进入 Validate。</span></div> : null}</section></div>;
}
