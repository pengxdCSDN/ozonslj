import { useState } from "react";
import { isolateAndSaveQualityRecords, type IsolationResult } from "./api";

export function QualityIsolationView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<IsolationResult | null>(null);
  const [message, setMessage] = useState("尚未执行数据隔离");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const next = await isolateAndSaveQualityRecords(workspaceId, {
        records: [{ id: "SKU-001" }, { id: "SKU-002" }],
        invalid_rows: [2],
        reason: "库存数据异常",
      });
      setResult(next);
      setMessage("隔离结果已保存到质量中心");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "隔离失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">数据质量 / DQ-007</p>
          <h2>异常数据隔离区</h2>
        </div>
        <button className="secondary-button" disabled={busy} onClick={() => void run()}>
          {busy ? "处理中…" : "执行并保存隔离"}
        </button>
      </div>
      <p className="form-message">{message}</p>
      {result ? (
        <>
          <div className="quality-result">
            <strong>隔离处理完成</strong>
            <span>可分析 {result.accepted.length} 条 · 已隔离 {result.isolated.length} 条</span>
          </div>
          {result.isolated.map((item) => (
            <div className="operation-row" key={item.row_index}>
              <span>
                <strong>第 {item.row_index} 行</strong>
                <small>{item.reason} · 原始记录已保留</small>
              </span>
              <em>已隔离</em>
            </div>
          ))}
        </>
      ) : (
        <div className="empty-search">
          <strong>尚未执行数据隔离</strong>
          <span>异常数据不会进入运营分析，同时保留原始记录和隔离原因。</span>
        </div>
      )}
    </section>
  );
}
