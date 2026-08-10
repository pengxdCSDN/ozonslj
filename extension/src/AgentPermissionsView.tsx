import { useState } from "react";
import { checkAndSaveAgentPermissions, listAgentPermissionHistory, type AgentPermissionDecision } from "./api";

export function AgentPermissionsView({ workspaceId }: { workspaceId: string }) {
  const [decisions, setDecisions] = useState<AgentPermissionDecision[]>([]);
  const [message, setMessage] = useState("Agent 永久只读，不持有 SQL、凭据或外部写入能力");
  const [busy, setBusy] = useState(false);
  const check = async () => { setBusy(true); try { const result = await checkAndSaveAgentPermissions(workspaceId, "summary_agent", ["read_sales", "read_inventory", "create_report", "execute_sql", "write_price"]); setDecisions((current) => [result, ...current]); setMessage("Agent 权限判定已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "权限检查失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setDecisions(await listAgentPermissionHistory(workspaceId)); setMessage("已加载权限判定历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "权限历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">报告与智能助手 / AI-009</p><h1>Agent 永久只读权限</h1><p>提示词不能改变权限边界，SQL、凭据和外部写入能力始终被拒绝。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">权限边界</p><h2>能力检查</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void check()}>检查并保存权限</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{decisions.map((result, index) => <div className="quality-result" key={`${result.agent}-${index}`}><strong>{result.agent} · 永久只读</strong><span>SQL：拒绝 · 凭据：拒绝 · 外部写入：拒绝</span><span>允许：{result.allowed_capabilities.join("、") || "无"}</span><small>拒绝：{result.denied_capabilities.join("、") || "无"} · read_only={String(result.read_only)}</small></div>)}{!decisions.length ? <div className="empty-search"><strong>尚未检查 Agent 权限</strong><span>权限检查会拒绝 SQL、凭据和所有外部写入能力。</span></div> : null}</section></div>;
}
