import { useState } from "react";
import { fetchWorkspaceSampleScope, type SampleScope } from "./api";

export function SampleScopeView({ workspaceId }: { workspaceId: string }) {
  const [scope, setScope] = useState<SampleScope | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("尚未加载样本范围");

  const show = async () => {
    setBusy(true);
    try {
      setScope(await fetchWorkspaceSampleScope(workspaceId));
      setMessage("样本范围已加载");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "样本范围加载失败");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">公开样本 / RES-008</p><h1>样本范围与可信度</h1><p>公开结论必须显示样本数量、采样时间范围、缺失字段和估算边界。</p></div></section>
    <section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void show()}>{busy ? "计算中…" : "查看范围摘要"}</button><p className="form-message">{message}</p>{scope ? <><div className="metric-grid"><article><span>样本数量</span><strong>{scope.sample_count}</strong></article><article><span>数据性质</span><strong>{scope.estimated ? "采样估算" : "官方事实"}</strong></article><article><span>缺失字段</span><strong>{scope.missing_fields.length}</strong></article></div><div className="quality-result"><strong>采样时间范围</strong><span>{scope.sampled_from ?? "无时间"} 至 {scope.sampled_to ?? "无时间"}</span><small>缺失字段：{scope.missing_fields.join("、") || "无"}</small><small>{scope.caveat}</small></div></> : <div className="empty-search"><strong>尚未加载范围摘要</strong><span>没有样本范围时，不输出精确市场结论。</span></div>}</section>
  </div>;
}
