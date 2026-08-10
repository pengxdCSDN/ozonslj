import { useEffect, useState } from "react";
import { getActiveModelAdapter, inspectAndSaveModelAdapter, listModelAdapterConfigs, type ModelAdapterConfig } from "./api";

export function ModelAdapterView({ workspaceId }: { workspaceId: string }) {
  const [active, setActive] = useState<ModelAdapterConfig | null>(null);
  const [configs, setConfigs] = useState<ModelAdapterConfig[]>([]);
  const [message, setMessage] = useState("模型适配器按配置切换，不绑定具体厂商；密钥不在浏览器保存。");
  const [busy, setBusy] = useState(false);
  const load = async () => { setBusy(true); try { const [current, history] = await Promise.all([getActiveModelAdapter(workspaceId), listModelAdapterConfigs(workspaceId)]); setActive(current); setConfigs(history); setMessage(current ? "已加载当前启用适配器和历史配置。" : "当前没有启用的适配器。"); } catch { setMessage("加载适配器配置失败。"); } finally { setBusy(false); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const inspect = async () => { setBusy(true); try { const config = await inspectAndSaveModelAdapter(workspaceId, { adapter: "generic", provider: "Local Stub", model: "stub", enabled: false, credential_configured: false }); setConfigs((current) => [config, ...current]); setMessage("模型适配器配置已保存。"); } catch { setMessage("检查适配器配置失败。"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Reports & Assistant / AI-001</p><h1>模型适配器</h1><p>根据配置切换模型厂商，凭据只在后端使用。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">当前配置</p><h2>启用适配器</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void inspect()}>保存 Stub 配置</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div></div><p className="form-message" role="status">{message}</p>{active ? <div className="quality-result"><strong>{active.adapter} · {active.provider}</strong><span>模型：{active.model} · 状态：已启用</span><small>凭据：{active.credential_configured ? "后端已配置" : "未配置"} · 页面不展示 API Key</small></div> : <div className="empty-search"><strong>当前没有启用适配器</strong><span>保存并启用适配器后，智能助手才可按配置选择模型。</span></div>}{configs.length ? <><h2>配置历史</h2>{configs.map((result, index) => <div className="operation-row" key={`${result.adapter}-${result.model}-${index}`}><span><strong>{result.adapter} · {result.provider}</strong><small>{result.model} · {result.enabled ? "已启用" : "未启用"}</small></span><em>{result.credential_configured ? "凭据已配置" : "未配置凭据"}</em></div>)}</> : null}</section></div>;
}
