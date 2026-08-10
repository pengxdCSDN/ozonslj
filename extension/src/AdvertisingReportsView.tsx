import { useEffect, useState } from "react";
import { listAdvertisingReports, saveAdvertisingReportSync, type AdvertisingReportRow } from "./api";

interface Props { workspaceId: string; }

export function AdvertisingReportsView({ workspaceId }: Props) {
  const [rows, setRows] = useState<AdvertisingReportRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const load = async () => { setBusy(true); try { setRows(await listAdvertisingReports(workspaceId)); } catch { setMessage("尚无已保存的广告报表快照。"); } finally { setBusy(false); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const sync = async () => { setBusy(true); try { const saved = await saveAdvertisingReportSync(workspaceId, [{ campaign_id: "stub-campaign", report_date: "2026-08-01", impressions: 100, clicks: 20, orders: 3, sales_minor: 50000, spend_minor: 5000, currency: "RUB" }]); setRows(saved); setMessage("广告报表只读快照已保存。"); } catch { setMessage("同步失败，请检查 Performance API 凭据。"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill</p><h1>广告报表同步</h1><p>展示展示、点击、订单、广告销售额和花费，金额使用最小货币单位。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void sync()}>{busy ? "同步中…" : "同步报表快照"}</button>{message ? <p role="status">{message}</p> : null}{rows.map((row) => <div className="operation-row" key={`${row.campaign_id}-${row.report_date}`}><span><strong>{row.report_date} · {row.campaign_id}</strong><small>展示 {row.impressions} · 点击 {row.clicks} · 订单 {row.orders}</small></span><em>{row.sales_minor} 销售额 · {row.spend_minor} 花费 {row.currency}</em></div>)}</section></div>;
}
