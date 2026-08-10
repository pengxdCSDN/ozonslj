import { useState } from "react";
import { labelDataSource, type DataSourceLabel } from "./api";

export function DataSourceLabelsView() {
  const [items, setItems] = useState<DataSourceLabel[]>([]);
  const [message, setMessage] = useState("");
  const load = async () => { try { setItems(await Promise.all(["official_private", "operator_imported", "public_sample", "derived_estimate"].map(labelDataSource))); setMessage(""); } catch (error) { setMessage(error instanceof Error ? error.message : "来源标签加载失败"); } };
  return <div className="view-content"><PageHeading label="数据质量 / DQ-001" title="数据来源标签" note="区分官方私有、运营导入、公开样本和推导估算" compact /><section className="panel"><div className="section-heading"><div><p className="eyebrow">可信度基础</p><h2>来源分类</h2></div><button className="secondary-button" onClick={() => void load()}>加载标签</button></div>{message ? <p className="form-message">{message}</p> : null}{items.length ? items.map((item) => <div className="operation-row" key={item.source}><span><strong>{item.label}</strong><small>{item.source}</small></span><b>{item.estimated ? "估算" : "事实"}</b><em>{item.description}</em></div>) : <div className="empty-search"><strong>尚未加载来源标签</strong><span>所有分析结果都应携带来源和估算标记。</span></div>}</section></div>;
}
function PageHeading({ label, title, note, compact }: { label: string; title: string; note: string; compact?: boolean }) { return <section className={`page-heading ${compact ? "compact" : ""}`}><div><p className="eyebrow">{label}</p><h1>{title}</h1><p>{note}</p></div></section>; }
