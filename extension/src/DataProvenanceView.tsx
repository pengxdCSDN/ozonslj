import { useEffect, useState } from "react";
import { classifyAndSaveDataSource, listDataProvenanceHistory, type DataProvenance } from "./api";

export function DataProvenanceView({ workspaceId }: { workspaceId: string }) {
  const [items, setItems] = useState<DataProvenance[]>([]); const [message, setMessage] = useState("");
  const load = async () => { try { setItems(await listDataProvenanceHistory(workspaceId)); } catch (error) { setMessage(error instanceof Error ? error.message : "加载来源历史失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { try { await classifyAndSaveDataSource(workspaceId, { source: "official_private", observed_at: new Date().toISOString(), explanation: "Seller API 商品事实" }); setMessage("来源标签已保存"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "来源标签保存失败"); } };
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">数据质量 / DQ-001</p><h2>数据来源标签</h2></div><button className="secondary-button" onClick={() => void run()}>校验并保存</button></div>{message ? <p className="form-message">{message}</p> : null}{items.length ? items.map((item, index) => <div className="operation-row" key={`${item.observed_at}-${index}`}><span><strong>{item.source}</strong><small>{item.observed_at} · {item.explanation}</small></span><em>可追溯</em></div>) : <p>官方事实、人工导入、公开样本和推导结果分开标记。</p>}</section>;
}
