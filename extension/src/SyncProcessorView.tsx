import { useState } from "react";
import { buildSyncProcessorPlan, type SyncProcessorPlan } from "./api";

export function SyncProcessorView() {
  const [result, setResult] = useState<SyncProcessorPlan | null>(null);
  const [message, setMessage] = useState("");
  const plan = async () => { try { setResult(await buildSyncProcessorPlan({ resource_type: "products", max_pages: 100, max_retries: 3 })); setMessage(""); } catch (error) { setMessage(error instanceof Error ? error.message : "同步计划生成失败"); } };
  return <div className="view-content"><PageHeading label="同步任务 / SYN-009" title="真实同步处理器计划" note="分页、重试和水位策略；当前仅生成干跑计划" compact /><section className="panel"><div className="section-heading"><div><p className="eyebrow">Worker 入口</p><h2>同步策略</h2></div><button className="secondary-button" onClick={() => void plan()}>生成计划</button></div>{message ? <p className="form-message">{message}</p> : null}{result ? <div className="quality-result"><strong>{result.resource_type} · {result.dry_run ? "干跑" : "执行"}</strong><span>最多 {result.max_pages} 页 · 每页最多重试 {result.max_retries} 次</span><span>{result.watermark_policy}</span></div> : <div className="empty-search"><strong>尚未生成同步计划</strong><span>失败任务不推进长期水位，Redis 丢失后由 PostgreSQL 状态恢复。</span></div>}</section></div>;
}
function PageHeading({ label, title, note, compact }: { label: string; title: string; note: string; compact?: boolean }) { return <section className={`page-heading ${compact ? "compact" : ""}`}><div><p className="eyebrow">{label}</p><h1>{title}</h1><p>{note}</p></div></section>; }
