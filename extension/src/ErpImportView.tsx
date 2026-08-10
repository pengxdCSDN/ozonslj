import { useState } from "react";

import { previewErpCsv, type ErpSupplyRecord } from "./api";

const sample = "external_id,offer_id,record_type,quantity,amount_minor,currency,expected_date\nPO-1,SKU-1,inbound,3,1000,RUB,2026-08-20\n";

export function ErpImportView() {
  const [content, setContent] = useState(sample);
  const [records, setRecords] = useState<ErpSupplyRecord[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const preview = async () => {
    setBusy(true);
    setMessage("");
    try {
      setRecords(await previewErpCsv(content));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ERP CSV 预览失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-content">
      <section className="page-heading compact"><div><p className="eyebrow">DAT-013 / ERP Port</p><h1>ERP 补充数据预览</h1><p>仅规范化采购、成本和在途记录，不接入具体 ERP，也不覆盖 Seller 官方事实。</p></div></section>
      <section className="panel import-panel">
        <textarea value={content} onChange={(event) => setContent(event.target.value)} aria-label="ERP CSV 内容" rows={8} />
        <button className="secondary-button" disabled={busy} onClick={() => void preview()}>{busy ? "解析中…" : "解析预览"}</button>
        {message ? <p className="form-message" role="alert">{message}</p> : null}
        {records.length ? records.map((record) => <div className="operation-row" key={record.external_id}><span><strong>{record.external_id} · {record.offer_id}</strong><small>{record.record_type} · {record.expected_date ?? "无预计日期"}</small></span><b>{record.quantity}</b><em>{record.currency ?? "—"} {record.amount_minor ?? "—"} · {record.source}</em></div>) : <div className="empty-search"><strong>尚未解析 ERP 记录</strong><span>预览结果不会自动保存或触发采购。</span></div>}
      </section>
    </div>
  );
}
