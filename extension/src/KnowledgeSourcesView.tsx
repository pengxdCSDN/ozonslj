import { BookOpen, Plus, UploadSimple } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { createKnowledgeSource, listKnowledgeSources, type KnowledgeSource } from "./api";

export function KnowledgeSourcesView() {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [title, setTitle] = useState("");
  const [locator, setLocator] = useState("");
  const [message, setMessage] = useState("");
  const refresh = () => { void listKnowledgeSources().then(setSources).catch(() => setMessage("知识源加载失败")); };
  useEffect(refresh, []);
  const create = async () => {
    if (!title.trim() || !locator.trim()) return;
    try {
      await createKnowledgeSource({ title: title.trim(), source_type: "markdown", business_domain: "general", source_locator: locator.trim() });
      setTitle(""); setLocator(""); setMessage("知识源已创建，等待版本接入"); refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "知识源创建失败"); }
  };
  return <div className="view-content">
    <div className="page-heading"><span className="eyebrow">知识中心 / 治理</span><h1>知识源管理</h1><p>管理来源、版本和发布状态；只有已发布版本可以参与问答。</p></div>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">接入向导</span><h2>新增知识源</h2></div><UploadSimple size={24} /></div><div className="form-grid"><label>来源名称<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：库存同步 SOP" /></label><label>来源定位<input value={locator} onChange={(event) => setLocator(event.target.value)} placeholder="例如：docs/sop.md" /></label></div><button type="button" className="primary-button" onClick={() => void create()} disabled={!title.trim() || !locator.trim()}><Plus size={17} />创建来源</button>{message ? <p className="form-message">{message}</p> : null}</section>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">目录</span><h2>已接入来源</h2></div><BookOpen size={24} /></div>{sources.length ? sources.map((source) => <article className="operation-row" key={source.id}><span><strong>{source.title}</strong><small>{source.source_locator} · {source.source_type}</small></span><em>{source.status}</em></article>) : <div className="empty-search"><strong>暂无知识源</strong><span>创建来源后再接入 Markdown、PDF 或数据库结构文档</span></div>}</section>
  </div>;
}
