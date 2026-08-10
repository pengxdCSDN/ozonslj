import { useState } from "react";
import { checkAndIsolateRelationshipQuality, type RelationshipFinding } from "./api";

export function RelationshipQualityView({ workspaceId }: { workspaceId: string }) {
  const [findings, setFindings] = useState<RelationshipFinding[]>([]);
  const [message, setMessage] = useState("尚未运行关系与时间检查");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const result = await checkAndIsolateRelationshipQuality(workspaceId, {
        parent_ids: ["p-1"],
        rows: [
          { id: "sku-1", parent_id: "p-1" },
          { id: "sku-1", parent_id: "missing" },
        ],
      });
      setFindings(result);
      setMessage(result.length ? `检查完成，发现 ${result.length} 个质量问题` : "检查通过");
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
          <p className="eyebrow">数据质量 / DQ-004</p>
          <h2>关系与时间检查</h2>
        </div>
        <button className="secondary-button" disabled={busy} onClick={() => void run()}>
          {busy ? "检查中…" : "运行检查并隔离"}
        </button>
      </div>
      <p className="form-message">{message}</p>
      {findings.length ? (
        findings.map((finding) => (
          <div className="operation-row" key={`${finding.row_index}-${finding.rule_code}`}>
            <span>
              <strong>{finding.rule_code}</strong>
              <small>第 {finding.row_index} 行 · {finding.message}</small>
            </span>
            <em>{finding.severity}</em>
          </div>
        ))
      ) : (
        <div className="empty-search">
          <strong>尚未发现问题</strong>
          <span>检查会识别孤儿关系、重复事实和时间倒退。</span>
        </div>
      )}
    </section>
  );
}
