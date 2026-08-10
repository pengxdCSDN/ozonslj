import { useState } from "react";
import { findAndIsolateSourceConflicts, type SourceConflict } from "./api";

export function SourceConflictView({ workspaceId }: { workspaceId: string }) {
  const [conflicts, setConflicts] = useState<SourceConflict[]>([]);
  const [message, setMessage] = useState("尚未检查来源冲突");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const result = await findAndIsolateSourceConflicts(workspaceId, {
        fields: ["price"],
        records: {
          official_private: { price: 100 },
          operator_imported: { price: 120 },
          public_sample: { price: 110 },
        },
      });
      setConflicts(result);
      setMessage(result.length ? `检查完成，发现 ${result.length} 个来源冲突并已隔离` : "检查通过");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "来源冲突检查失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">数据质量 / DQ-006</p>
          <h2>跨来源一致性</h2>
        </div>
        <button className="secondary-button" disabled={busy} onClick={() => void run()}>
          {busy ? "检查中…" : "检查来源冲突"}
        </button>
      </div>
      <p className="form-message">{message}</p>
      {conflicts.length ? (
        conflicts.map((conflict) => (
          <div className="operation-row" key={conflict.field}>
            <span>
              <strong>{conflict.field}</strong>
              <small>{conflict.sources.join(" / ")}</small>
              <small>值：{conflict.values.join(" / ")}</small>
            </span>
            <em>{conflict.message}</em>
          </div>
        ))
      ) : (
        <div className="empty-search">
          <strong>尚未发现来源冲突</strong>
          <span>官方事实、运营导入和公开样本冲突会进入质量中心，不覆盖官方事实。</span>
        </div>
      )}
    </section>
  );
}
