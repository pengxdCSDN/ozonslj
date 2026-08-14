import { useState } from "react";
import { calculateAndSaveAdvertisingMetrics, type AdvertisingMetrics } from "./api";

const samplePayload = { impressions: 1000, clicks: 100, orders: 10, ad_sales_minor: 50000, total_sales_minor: 100000, spend_minor: 10000, currency: "RUB", window: "2026-08-01/2026-08-07" };

interface Props { workspaceId: string; }

export function AdvertisingMetricsView({ workspaceId }: Props) {
  const [result, setResult] = useState<AdvertisingMetrics | null>(null);
  const [message, setMessage] = useState("");
  const calculate = async () => {
    try { setResult(await calculateAndSaveAdvertisingMetrics(workspaceId, samplePayload)); setMessage(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "指标计算失败"); }
  };
  const format = (value: number | null, suffix = "%") => value === null ? "—" : `${value.toFixed(2)}${suffix}`;
  return <div className="view-content"><PageHeading label="广告 Skill / ADS-004" title="广告指标计算" note="按统计窗口展示公式、币种与数据完整度" compact />
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">只读计算</p><h2>Performance 指标口径</h2></div><button className="secondary-button" onClick={() => void calculate()}>计算示例</button></div>
      {message ? <p className="form-message">{message}</p> : null}{result ? <><div className="metric-grid"><article><span>ACOS</span><strong>{format(result.acos_percent)}</strong></article><article><span>TACOS</span><strong>{format(result.tacos_percent)}</strong></article><article><span>CPC</span><strong>{format(result.cpc_minor, ` ${result.currency}`)}</strong></article><article><span>CTR</span><strong>{format(result.ctr_percent)}</strong></article><article><span>CVR</span><strong>{format(result.cvr_percent)}</strong></article><article><span>ROI</span><strong>{format(result.roi_percent)}</strong></article></div><div className="quality-result"><strong>{result.complete ? "数据完整" : "数据不完整"}</strong><span>窗口：{result.window} · 币种：{result.currency}</span></div><div className="operation-row"><span><strong>指标口径</strong><small>所有比率按后端返回公式计算</small></span><em>{Object.entries(result.formulas).map(([name, formula]) => `${name}: ${formula}`).join("；")}</em></div></> : <div className="empty-search"><strong>尚未计算广告指标</strong><span>指标仅用于诊断和报表，不会自动修改广告活动。</span></div>}
    </section></div>;
}

function PageHeading({ label, title, note, compact }: { label: string; title: string; note: string; compact?: boolean }) { return <section className={`page-heading ${compact ? "compact" : ""}`}><div><p className="eyebrow">{label}</p><h1>{title}</h1><p>{note}</p></div></section>; }
