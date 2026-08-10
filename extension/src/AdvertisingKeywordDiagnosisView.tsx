import { useState } from "react";
import { diagnoseAndSaveAdvertisingKeywords, listAdvertisingKeywordReports, type AdvertisingKeywordDiagnosis } from "./api";

const sampleRows = [{ keyword: "термос", impressions: 500, clicks: 50, orders: 5, spend_minor: 500, sales_minor: 5000 }, { keyword: "термос стальной", impressions: 200, clicks: 20, orders: 0, spend_minor: 2000, sales_minor: 0 }];
const labels: Record<AdvertisingKeywordDiagnosis["category"], string> = { star: "明星词", high_cvr: "高 CVR 词", potential: "潜力词", high_spend_no_conversion: "高费无转化词" };

export function AdvertisingKeywordDiagnosisView({ workspaceId }: { workspaceId: string }) {
  const [items, setItems] = useState<AdvertisingKeywordDiagnosis[]>([]);
  const [message, setMessage] = useState("诊断结果只读，不会修改广告配置");
  const [busy, setBusy] = useState(false);
  const diagnose = async () => { setBusy(true); try { setItems(await diagnoseAndSaveAdvertisingKeywords(workspaceId, { rows: sampleRows })); setMessage("诊断报告已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "诊断失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { const reports = await listAdvertisingKeywordReports(workspaceId); setItems(reports[0] ?? []); setMessage(reports.length ? "已加载最近诊断报告" : "暂无诊断历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "诊断历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill / ADS-006</p><h1>关键词诊断</h1><p>识别明星词、高 CVR、潜力词和高费无转化词，仅生成只读建议。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">只读建议</p><h2>按指标分类</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void diagnose()}>运行并保存诊断</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载诊断历史</button></div></div><p className="form-message">{message}</p>{items.length ? items.map((item) => <div className="operation-row" key={item.keyword}><span><strong>{item.keyword}</strong><small>{labels[item.category]} · CTR {item.ctr_percent?.toFixed(2) ?? "无"}% · CVR {item.cvr_percent?.toFixed(2) ?? "无"}% · ACOS {item.acos_percent?.toFixed(2) ?? "无"}%</small></span><b>{item.orders} 订单</b><em>{item.reason}</em></div>) : <div className="empty-search"><strong>尚未运行关键词诊断</strong><span>诊断不会自动修改预算、出价或否定词。</span></div>}</section></div>;
}
