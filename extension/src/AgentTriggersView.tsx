import { useState } from "react";
import { listAgentTriggers, validateAndSaveAgentTrigger, type AgentTrigger } from "./api";

export function AgentTriggersView({ workspaceId }: { workspaceId: string }) {
  const [triggers, setTriggers] = useState<AgentTrigger[]>([]);
  const [message, setMessage] = useState("触发配置保持只读边界，不绕过审核链路");
  const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { const trigger = await validateAndSaveAgentTrigger(workspaceId, { trigger_type: "scheduled", target: "summary_agent", schedule: "0 9 * * *", enabled: false }); setTriggers((current) => [trigger, ...current]); setMessage("Agent 触发配置已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "触发配置保存失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setTriggers(await listAgentTriggers(workspaceId)); setMessage("已加载触发配置历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "触发历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">报告与智能助手 / AI-008</p><h1>Agent 触发器</h1><p>支持定时、事件和手动触发，配置始终受只读权限与人工审核边界约束。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">触发配置</p><h2>触发器校验</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void save()}>校验并保存定时触发</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{triggers.length ? triggers.map((result, index) => <div className="quality-result" key={`${result.trigger_type}-${result.target}-${index}`}><strong>{result.trigger_type} · {result.target}</strong><span>{result.schedule ?? result.event_name ?? "手动运行"}</span><small>{result.enabled ? "已启用" : "未启用"} · {result.read_only ? "只读" : "需审核"}</small></div>) : <div className="empty-search"><strong>尚未校验触发配置</strong><span>触发器不会绕过参数化只读工具和人工审核边界。</span></div>}</section></div>;
}
