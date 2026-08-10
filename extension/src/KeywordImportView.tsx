import { useState, type ChangeEvent } from "react";
import {
  commitKeywordImport,
  listKeywordImportHistory,
  previewMappedKeywordImport,
  previewMappedKeywordXlsx,
  type KeywordImportBatch,
  type KeywordImportPreview,
} from "./api";

export function KeywordImportView({ workspaceId }: { workspaceId: string }) {
  const [mapping, setMapping] = useState({ term: "term", volume: "volume", rate: "rate" });
  const [csv, setCsv] = useState("term,volume,rate\n");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<KeywordImportPreview | null>(null);
  const [history, setHistory] = useState<KeywordImportBatch[]>([]);
  const [message, setMessage] = useState("请先映射列并预览导入");
  const [busy, setBusy] = useState(false);

  const columnMapping = () => ({
    [mapping.term]: "keyword",
    [mapping.volume]: "search_count",
    [mapping.rate]: "conversion_rate",
  });

  const previewImport = async () => {
    setBusy(true);
    try {
      if (file) {
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        bytes.forEach((value) => { binary += String.fromCharCode(value); });
        setPreview(await previewMappedKeywordXlsx(workspaceId, btoa(binary), columnMapping()));
      } else {
        setPreview(await previewMappedKeywordImport(workspaceId, csv, columnMapping()));
      }
      setMessage("预览成功，请确认后提交导入");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导入预览失败");
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    if (!preview) return;
    setBusy(true);
    try {
      const batch = await commitKeywordImport(workspaceId, preview.fingerprint, preview.rows);
      setMessage(batch.reused ? "检测到相同指纹，已复用已有导入批次" : "导入批次已保存");
      setHistory((current) => [batch, ...current.filter((item) => item.id !== batch.id)]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导入批次保存失败");
    } finally {
      setBusy(false);
    }
  };

  const loadHistory = async () => {
    setBusy(true);
    try {
      setHistory(await listKeywordImportHistory(workspaceId));
      setMessage("已加载导入历史");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导入历史加载失败");
    } finally {
      setBusy(false);
    }
  };

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
    setPreview(null);
  };

  return (
    <div className="view-content">
      <section className="page-heading compact">
        <div>
          <p className="eyebrow">数据导入 / RES-001 / RES-002 / RES-003</p>
          <h1>搜索词报告导入</h1>
          <p>支持 CSV 和 XLSX；先映射列并预览校验，再按文件指纹幂等提交导入批次。</p>
        </div>
      </section>
      <section className="panel import-panel">
        <div className="form-grid">
          <label>关键词列<input value={mapping.term} onChange={(event) => setMapping({ ...mapping, term: event.target.value })} /></label>
          <label>搜索量列<input value={mapping.volume} onChange={(event) => setMapping({ ...mapping, volume: event.target.value })} /></label>
          <label>转化率列<input value={mapping.rate} onChange={(event) => setMapping({ ...mapping, rate: event.target.value })} /></label>
        </div>
        <label>选择 XLSX 文件（可选）<input type="file" accept=".xlsx" onChange={chooseFile} /></label>
        <textarea value={csv} disabled={Boolean(file)} onChange={(event) => setCsv(event.target.value)} aria-label="CSV 内容" rows={8} />
        <div className="sync-actions">
          <button className="secondary-button" disabled={busy} onClick={() => void previewImport()}>映射并预览</button>
          <button className="secondary-button" disabled={busy || !preview} onClick={() => void commit()}>提交导入</button>
          <button className="secondary-button" disabled={busy} onClick={() => void loadHistory()}>加载历史</button>
        </div>
        <p className="form-message" role="status">{message}</p>
        {preview ? <div className="quality-result">
          <strong>{preview.total} 行 · 指纹 {preview.fingerprint.slice(0, 12)}…</strong>
          {preview.rows.slice(0, 5).map((row) => <div className="operation-row" key={row.source_row}><span><strong>{row.keyword}</strong><small>第 {row.source_row} 行 · 转化率 {row.conversion_rate ?? "无"}</small></span><em>{row.search_count ?? "无搜索量"}</em></div>)}
        </div> : null}
      </section>
      <section className="panel">
        <div className="panel-heading"><h2>导入批次历史</h2></div>
        {history.length ? history.map((batch) => <div className="operation-row" key={batch.id}><span><strong>{batch.row_count} 行</strong><small>{batch.created_at} · {batch.fingerprint.slice(0, 12)}…</small></span><em>{batch.reused ? "已复用" : "新批次"}</em></div>) : <div className="empty-search"><strong>暂无导入历史</strong><span>相同文件指纹不会重复生成事实批次。</span></div>}
      </section>
    </div>
  );
}
