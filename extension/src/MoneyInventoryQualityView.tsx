import { useState } from "react";
import { checkAndIsolateMoneyInventory, type MoneyInventoryFinding } from "./api";

export function MoneyInventoryQualityView({ workspaceId }: { workspaceId: string }) {
  const [findings, setFindings] = useState<MoneyInventoryFinding[]>([]);
  const [message, setMessage] = useState("尚未运行金额与库存检查");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const result = await checkAndIsolateMoneyInventory(workspaceId, {
        record: { currency: "RUB", price_minor: 129900, cost_minor: 70000, available_stock: 12 },
      });
      setFindings(result);
      setMessage(result.length ? `检查完成，发现 ${result.length} 个问题并已隔离` : "检查通过");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "检查失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">数据质量 / DQ-005</p>
          <h2>金额与库存检查</h2>
        </div>
        <button className="secondary-button" disabled={busy} onClick={() => void run()}>
          {busy ? "检查中…" : "运行检查并隔离"}
        </button>
      </div>
      <p className="form-message">{message}</p>
      {findings.length ? (
        findings.map((finding) => (
          <div className="operation-row" key={`${finding.field}-${finding.rule_code}`}>
            <span>
              <strong>{finding.field}</strong>
              <small>{finding.rule_code}</small>
            </span>
            <em>{finding.message}</em>
          </div>
        ))
      ) : (
        <div className="empty-search">
          <strong>尚未发现问题</strong>
          <span>检查币种、金额正数约束和负库存，异常不会进入运营指标。</span>
        </div>
      )}
    </section>
  );
}
