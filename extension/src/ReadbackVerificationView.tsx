import { useState } from "react";
import {
  listReadbackVerifications,
  saveReadbackVerification,
  type StoredReadbackVerification,
} from "./api";

const expected = { price_minor: 270000, title: "商品标题" };
const actual = { price_minor: 270000, title: "商品标题" };

export function ReadbackVerificationView({ workspaceId }: { workspaceId: string }) {
  const [records, setRecords] = useState<StoredReadbackVerification[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("等待回读核对");

  const save = async () => {
    setBusy(true);
    try {
      const record = await saveReadbackVerification(workspaceId, expected, actual);
      setRecords((current) => [record, ...current]);
      setMessage(record.verification.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败");
    } finally {
      setBusy(false);
    }
  };

  const load = async () => {
    setBusy(true);
    try {
      setRecords(await listReadbackVerifications(workspaceId));
      setMessage("已加载回读历史");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">受控执行 / REV-009</p>
          <h2>回读核对</h2>
        </div>
        <div className="button-row">
          <button className="secondary-button" disabled={busy} onClick={() => void save()}>
            保存回读结果
          </button>
          <button className="secondary-button" disabled={busy} onClick={() => void load()}>
            加载历史
          </button>
        </div>
      </div>
      <p className="form-message">{message}</p>
      {records.map((record) => (
        <div className="quality-result" key={record.verification_id}>
          <strong>{record.verification.matched ? "核对一致" : "发现差异"}</strong>
          <small>{record.created_at} · {record.verification_id}</small>
          {record.verification.fields.map((field) => (
            <div className="operation-row" key={`${record.verification_id}-${field.field}`}>
              <span>
                <strong>{field.field}</strong>
                <small>预期：{field.expected ?? "无"} · 实际：{field.actual ?? "无"}</small>
              </span>
              <em>{field.matched ? "一致" : "差异"}</em>
            </div>
          ))}
        </div>
      ))}
      {!records.length ? <p>保存后将在此显示逐字段核对结果，差异记录不会被成功状态覆盖。</p> : null}
    </section>
  );
}
