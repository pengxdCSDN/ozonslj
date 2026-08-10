import { useState } from "react";
import { checkAndSaveAdvertisingBoundary, listAdvertisingBoundaryHistory, type AdvertisingReadOnlyDecision } from "./api";

export function AdvertisingReadonlyView({ workspaceId }: { workspaceId: string }) {
  const [results, setResults] = useState<AdvertisingReadOnlyDecision[]>([]);
  const [message, setMessage] = useState("广告建议默认只读，写动作必须进入审核");
  const [busy, setBusy] = useState(false);
  const check = async () => { setBusy(true); try { const actions = ["diagnose", "change_budget", "change_bid", "change_negative_keyword"]; setResults(await Promise.all(actions.map((action) => checkAndSaveAdvertisingBoundary(workspaceId, action)))); setMessage("边界检查已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "边界检查失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setResults(await listAdvertisingBoundaryHistory(workspaceId)); setMessage("已加载边界检查历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "边界历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill / ADS-009</p><h1>广告只读边界</h1><p>预算、出价和否定词写入必须经过独立人工审核链路。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">边界检查</p><h2>动作权限矩阵</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void check()}>检查并保存边界</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{results.length ? results.map((item, index) => <div className="operation-row" key={`${item.action}-${index}`}><span><strong>{item.action}</strong><small>{item.audit_required ? "需要审核" : "只读分析"}</small></span><b>{item.allowed ? "允许" : "拒绝"}</b><em>{item.reason}</em></div>) : <div className="empty-search"><strong>尚未执行边界检查</strong><span>广告诊断不会自动修改预算、出价或否定词。</span></div>}</section></div>;
}
