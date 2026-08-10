import { useState } from "react";
import { listAdvertisingThresholdVersions, validateAndSaveAdvertisingThresholds, type AdvertisingThresholds } from "./api";

export function AdvertisingThresholdsView({ workspaceId }: { workspaceId: string }) {
  const [versions, setVersions] = useState<AdvertisingThresholds[]>([]);
  const [message, setMessage] = useState("阈值只影响诊断分类，不直接触发广告操作");
  const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { const value = await validateAndSaveAdvertisingThresholds(workspaceId, { version: Date.now(), min_impressions: 100, min_clicks: 10, high_cvr_percent: 8, high_spend_minor: 1000 }); setVersions((current) => [value, ...current]); setMessage("阈值版本已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "阈值保存失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setVersions(await listAdvertisingThresholdVersions(workspaceId)); setMessage("已加载阈值版本历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "阈值历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill / ADS-007</p><h1>诊断阈值配置</h1><p>阈值按版本保存，历史版本不会被覆盖；仅用于关键词诊断分类。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">工作区配置</p><h2>阈值版本</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void save()}>校验并保存</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载版本历史</button></div></div><p className="form-message">{message}</p>{versions.map((value) => <div className="quality-result" key={value.version}><strong>版本 v{value.version}</strong><span>展示 ≥ {value.min_impressions} · 点击 ≥ {value.min_clicks} · 高 CVR ≥ {value.high_cvr_percent}% · 高花费 ≥ {value.high_spend_minor}</span></div>)}{!versions.length ? <div className="empty-search"><strong>尚未加载阈值版本</strong><span>阈值只用于广告关键词诊断，不会自动修改预算或出价。</span></div> : null}</section></div>;
}
