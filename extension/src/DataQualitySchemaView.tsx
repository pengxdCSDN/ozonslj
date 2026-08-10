import { useState } from "react";
import { checkAndIsolateQualitySchema, type QualitySchemaResult } from "./api";

const samplePayload = {
  rows: [{ status: "bad" }, { sku: "SKU-2", status: "active" }],
  required_fields: ["sku"],
  enum_fields: { status: ["active", "paused"] },
};

export function DataQualitySchemaView({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<QualitySchemaResult | null>(null);
  const [message, setMessage] = useState("尚未运行字段质量检查");
  const [busy, setBusy] = useState(false);

  const check = async () => {
    setBusy(true);
    try {
      const next = await checkAndIsolateQualitySchema(workspaceId, samplePayload);
      setResult(next);
      setMessage(next.valid ? "检查通过，未发现需要隔离的数据" : "检查完成，异常已保存到质量隔离区");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "质量检查失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <p className="eyebrow">数据质量 / DQ-003</p>
          <h1>缺失字段与未知枚举</h1>
          <p>检查必填字段和枚举值；异常数据进入 PostgreSQL 隔离区，不静默参与运营分析。</p>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Schema 检查</p>
            <h2>质量问题</h2>
          </div>
          <button className="secondary-button" disabled={busy} onClick={() => void check()}>
            {busy ? "检查中…" : "检查并隔离"}
          </button>
        </div>
        <p className="form-message">{message}</p>
        {result ? (
          <>
            <div className="quality-result">
              <strong>{result.valid ? "检查通过" : `发现 ${result.findings.length} 个问题`}</strong>
              <span>
                已检查 {result.checked_rows} 行 · {result.isolated_required ? "已进入隔离区" : "无需隔离"}
              </span>
            </div>
            {result.findings.map((item) => (
              <div className="operation-row" key={`${item.row_index}-${item.field}-${item.rule_code}`}>
                <span>
                  <strong>第 {item.row_index} 行 · {item.field}</strong>
                  <small>{item.rule_code} · {item.severity} · 当前值：{item.value ?? "缺失"}</small>
                </span>
                <em>{item.message}</em>
              </div>
            ))}
          </>
        ) : (
          <div className="empty-search">
            <strong>尚未运行 Schema 检查</strong>
            <span>异常数据会先进入质量隔离区，再由运营人员处理。</span>
          </div>
        )}
      </section>
    </div>
  );
}
