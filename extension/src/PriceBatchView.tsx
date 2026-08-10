import { useState } from "react";
import { validatePriceBatch, type PriceBatchValidation } from "./api";

export function PriceBatchView() {
  const [result, setResult] = useState<PriceBatchValidation | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("价格不得低于利润线，且单批最多 20 个商品、涨跌不超过 10%");
  const run = async () => { setBusy(true); try { const next = await validatePriceBatch([{ sku: "SKU-001", old_price_minor: 250000, new_price_minor: 270000, profit_line_minor: 240000 }]); setResult(next); setMessage(next.valid ? "价格批次校验通过，仍需人工审核后执行" : next.message); } catch (error) { setMessage(error instanceof Error ? error.message : "价格批次校验失败"); } finally { setBusy(false); } };
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">受控执行 / REV-005 / REV-006 / REV-007</p><h2>价格批次与利润线保护</h2></div><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "校验中…" : "校验价格批次"}</button></div><p className="form-message">{message}</p>{result ? <><div className="quality-result"><strong>{result.valid ? "校验通过" : "校验拒绝"}</strong><span>商品数 {result.total_items}/{result.max_items} · 最大涨跌 {result.max_change_percent}%</span></div>{result.items.map((item) => <div className="operation-row" key={item.sku}><span><strong>{item.sku}</strong><small>旧价 {item.old_price_minor} → 新价 {item.new_price_minor} · 利润线 {item.profit_line_minor ?? "未设置"}</small></span><em>{result.valid ? "满足批次规则" : "不得执行"}</em></div>)}</> : <div className="empty-search"><strong>尚未校验价格批次</strong><span>低于利润线、超批量或超涨跌幅的请求不得执行。</span></div>}</section>;
}
