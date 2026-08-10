import { useEffect, useState } from "react";
import { compareAndSaveParserResults, listParserAlertHistory, type ParserChange } from "./api";

export function ParserAlertsView({ workspaceId }: { workspaceId: string }) {
  const [changes, setChanges] = useState<ParserChange[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("尚未执行解析变化比较");

  const load = async () => {
    try {
      setChanges(await listParserAlertHistory(workspaceId));
      setMessage("已加载解析告警历史");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "解析告警加载失败");
    }
  };

  useEffect(() => { void load(); }, [workspaceId]);

  const compare = async () => {
    setBusy(true);
    try {
      await compareAndSaveParserResults(workspaceId, "https://example.com/item", { title: "旧标题", rating: "4.5", price: "100" }, { title: "新标题", price: "100" });
      setMessage("解析变化告警已保存");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "解析结果比较失败");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">公开采样 / RES-009</p><h1>解析变化告警</h1><p>页面结构或字段解析变化进入质量中心；不保存原始页面内容。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void compare()}>{busy ? "比较并保存中…" : "比较并保存告警"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近告警</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{changes.length ? changes.map((change, index) => <div className="operation-row" key={`${change.field_name}-${index}`}><span><strong>{change.field_name}</strong><small>{change.old_value ?? "缺失"} → {change.new_value ?? "缺失"} · {change.message}</small></span><em>{change.severity === "error" ? "错误" : "警告"}</em></div>) : <div className="empty-search"><strong>暂无解析变化</strong><span>字段消失或内容变化后会保存告警。</span></div>}</section></div>;
}
