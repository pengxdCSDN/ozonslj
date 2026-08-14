import { useState } from "react";
import { buildAndSaveAdvertisingCalendar, listAdvertisingCalendarHistory, type AdvertisingCalendarDay } from "./api";

const labels: Record<AdvertisingCalendarDay["phase"], string> = { testing: "测试", filtering: "积累与筛选", scaling: "放量评估", optimizing: "优化" };

export function AdvertisingCalendarView({ workspaceId }: { workspaceId: string }) {
  const [days, setDays] = useState<AdvertisingCalendarDay[]>([]);
  const [message, setMessage] = useState("日历只提供运营建议，不自动修改广告配置");
  const [busy, setBusy] = useState(false);
  const build = async () => { setBusy(true); try { setDays(await buildAndSaveAdvertisingCalendar(workspaceId, new Date().toISOString().slice(0, 10))); setMessage("30 天建议日历已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "日历生成失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { const history = await listAdvertisingCalendarHistory(workspaceId); setDays(history[0] ?? []); setMessage(history.length ? "已加载最近建议日历" : "暂无日历历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "日历历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill / ADS-008</p><h1>新品前 30 天建议日历</h1><p>按测试、筛选、放量和优化阶段生成只读建议。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">建议计划</p><h2>30 天运营节奏</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void build()}>生成并保存日历</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{days.length ? days.map((item) => <div className="operation-row" key={item.day}><span><strong>第 {item.day} 天 · {labels[item.phase]}</strong><small>{item.date} · {item.read_only ? "只读建议" : "需复核"}</small></span><em>{item.recommendation}</em></div>) : <div className="empty-search"><strong>尚未生成建议日历</strong><span>日历不会自动执行预算、出价或否定词变更。</span></div>}</section></div>;
}
