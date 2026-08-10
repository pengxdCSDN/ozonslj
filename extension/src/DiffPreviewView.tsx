import { useState } from "react";
import { buildAndSaveDiffPreview, type DiffPreview } from "./api";

export function DiffPreviewView({ workspaceId }: { workspaceId: string }) {
  const [items, setItems] = useState<DiffPreview[]>([]);
  const [message, setMessage] = useState("预览默认需要人工复核；提交前会校验数据新鲜度。");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    const observedAt = new Date().toISOString();
    try {
      setItems(await buildAndSaveDiffPreview(workspaceId, {
        old_values: { price: "2500", title: "Термос 500 мл" },
        new_values: { price: "2700", title: "Термос 500 мл для поездок" },
        source: "人工编辑",
        impact: "可能影响商品展示与售价",
        observed_at: observedAt,
        max_age_seconds: 600,
      }));
      setMessage("差异预览已保存，等待人工审核。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "差异预览失败，请刷新数据后重试。");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div>
      <p className="eyebrow">审核与受控执行 / REV-001 · REV-002</p>
      <h1>差异预览</h1>
      <p>展示旧值、新值、来源和影响；过期数据不能进入审核材料。</p>
    </div></section>
    <section className="panel">
      <button className="secondary-button" disabled={busy} onClick={() => void run()}>
        {busy ? "生成中…" : "检查新鲜度并保存预览"}
      </button>
      <p className="form-message" role="status">{message}</p>
      {items.length ? items.map((item) => <div className="operation-row" key={item.field}>
        <span><strong>{item.field}</strong><small>旧值：{item.old_value ?? "空"} → 新值：{item.new_value ?? "空"}</small></span>
        <em>{item.source} · {item.impact} · 需要人工复核</em>
      </div>) : <div className="empty-search"><strong>尚未生成差异预览</strong><span>未通过新鲜度和人工审核的差异不得进入执行器。</span></div>}
    </section>
  </div>;
}
