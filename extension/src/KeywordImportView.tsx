import { useState, type ChangeEvent } from "react";
import {
  commitKeywordImport,
  listKeywordImportHistory,
  previewMappedKeywordImport,
  previewMappedKeywordXlsx,
  type KeywordImportBatch,
  type KeywordImportPreview,
} from "./api";

const SAMPLE_KEYWORD_CSV = `term,volume,rate
wireless earbuds,18400,3.8
phone case,12600,2.6
laptop stand,8300,4.1
usb c cable,7200,3.2
kitchen organizer,5100,5.4`;

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

  const loadSample = () => {
    setFile(null);
    setPreview(null);
    setCsv(SAMPLE_KEYWORD_CSV);
    setMessage("已加载示例数据，请先映射并预览");
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
      <section className="panel import-panel keyword-import-panel">
        <div className="keyword-import-guide"><div><p className="eyebrow">使用说明</p><h2>把搜索词报告变成可分析数据</h2><p>先告诉系统每一列代表什么，再上传或粘贴报告；预览通过后才会保存批次，重复文件会自动复用。</p><p className="keyword-import-business-note">跨境电商用途：统一关键词、搜索量和转化率，支持选品判断、Listing 关键词优化和广告预算分析。</p></div><ol><li><strong>映射字段</strong><span>对应关键词、搜索量和转化率列名</span></li><li><strong>导入数据</strong><span>选择 XLSX，或粘贴 CSV（二选一）</span></li><li><strong>预览提交</strong><span>确认行数和样本后写入导入历史</span></li></ol></div>
        <div className="keyword-import-workflow">
          <section className="import-step-card"><div className="import-step-heading"><span className="eyebrow">步骤 1</span><h2>字段映射</h2><p>填写报告表头的原始列名。示例文件使用下面三个列名。</p></div><div className="form-grid keyword-mapping-grid"><label>关键词列<input value={mapping.term} onChange={(event) => setMapping({ ...mapping, term: event.target.value })} /></label><label>搜索量列<input value={mapping.volume} onChange={(event) => setMapping({ ...mapping, volume: event.target.value })} /></label><label>转化率列<input value={mapping.rate} onChange={(event) => setMapping({ ...mapping, rate: event.target.value })} /></label></div></section>
          <section className="import-step-card import-input-block"><div className="import-step-heading"><span className="eyebrow">步骤 2</span><h2>导入数据</h2><p>可选 XLSX 文件，或直接粘贴 CSV 内容；选中文件后文本框会锁定。</p></div><label className="file-input-field">选择 XLSX 文件（可选）<input type="file" accept=".xlsx" onChange={chooseFile} /><small>{file ? `已选择：${file.name}` : "未选择文件"}</small></label><textarea value={csv} disabled={Boolean(file)} onChange={(event) => setCsv(event.target.value)} aria-label="CSV 内容" rows={7} /><button className="text-button sample-data-button" type="button" disabled={busy} onClick={loadSample}>加载示例 CSV</button></section>
        </div>
        <div className="keyword-import-actions"><div><span className="eyebrow">步骤 3</span><strong>预览与提交</strong><small>预览成功后再保存，避免错误数据进入分析。</small></div><div className="sync-actions import-actions"><button className="secondary-button" disabled={busy} onClick={() => void previewImport()}>映射并预览</button><button className="primary-button" disabled={busy || !preview} onClick={() => void commit()}>提交导入</button><button className="text-button" disabled={busy} onClick={() => void loadHistory()}>加载历史</button></div></div>
        <p className="form-message import-status" role="status">{message}</p>
        {preview ? <div className="quality-result">
          <strong>{preview.total} 行 · 指纹 {preview.fingerprint.slice(0, 12)}…</strong>
          {preview.rows.slice(0, 5).map((row) => <div className="operation-row" key={row.source_row}><span><strong>{row.keyword}</strong><small>第 {row.source_row} 行 · 转化率 {row.conversion_rate ?? "无"}</small></span><em>{row.search_count ?? "无搜索量"}</em></div>)}
        </div> : null}
      </section>
      <section className="panel import-history-panel">
        <div className="panel-heading"><h2>导入批次历史</h2></div>
        {history.length ? history.map((batch) => <div className="operation-row" key={batch.id}><span><strong>{batch.row_count} 行</strong><small>{batch.created_at} · {batch.fingerprint.slice(0, 12)}…</small></span><em>{batch.reused ? "已复用" : "新批次"}</em></div>) : <div className="empty-search"><strong>暂无导入历史</strong><span>相同文件指纹不会重复生成事实批次。</span></div>}
      </section>
    </div>
  );
}
