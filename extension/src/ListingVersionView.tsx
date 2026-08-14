import { useState } from "react";
import { compareAndSaveListingVersion, listListingVersions, type ListingVersion } from "./api";

export function ListingVersionView({ workspaceId }: { workspaceId: string }) {
  const [versions, setVersions] = useState<ListingVersion[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("版本不会自动发布");
  const save = async () => { setBusy(true); try { const version = await compareAndSaveListingVersion(workspaceId, { version: Date.now(), original_text: "Термос 500 мл", edited_text: "Термос 500 мл для похода", status: "review" }); setVersions((current) => [version, ...current]); setMessage("版本已保存，可继续人工审核"); } catch (error) { setMessage(error instanceof Error ? error.message : "版本保存失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setVersions(await listListingVersions(workspaceId)); setMessage("已加载 Listing 版本历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "版本历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-008</p><h1>Listing 草稿版本管理</h1><p>保存原文、人工修改、差异和审核状态，为受控发布提供可追溯版本。</p></div></section><section className="panel import-panel"><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void save()}>比较并保存版本</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载版本历史</button></div><p className="form-message">{message}</p>{versions.map((version) => <div className="quality-result" key={`${version.version}-${version.status}`}><strong>版本 {version.version} · {version.status}</strong><span>原文：{version.original_text}</span><span>修改后：{version.edited_text}</span><small>{version.diff.join(" | ") || "无差异"}</small></div>)}{!versions.length ? <div className="empty-search"><strong>暂无 Listing 版本</strong><span>保存后可在此回看原文、修改文本和差异。</span></div> : null}</section></div>;
}
