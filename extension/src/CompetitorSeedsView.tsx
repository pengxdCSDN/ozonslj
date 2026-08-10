import { useEffect, useState, type FormEvent } from "react";
import { createCompetitorSeed, fetchCompetitorSeeds, updateCompetitorSeed, type CompetitorSeed } from "./api";

export function CompetitorSeedsView({ workspaceId }: { workspaceId: string }) {
  const [seeds, setSeeds] = useState<CompetitorSeed[]>([]);
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("尚未加载竞品种子");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setSeeds(await fetchCompetitorSeeds(workspaceId));
      setMessage("已加载受控竞品种子");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "竞品种子加载失败");
    }
  };

  useEffect(() => { void load(); }, [workspaceId]);

  const add = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      await createCompetitorSeed(workspaceId, url);
      setUrl("");
      setMessage("竞品种子已保存");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "竞品种子保存失败");
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (seed: CompetitorSeed) => {
    setBusy(true);
    try {
      const status = seed.status === "active" ? "paused" : "active";
      const updated = await updateCompetitorSeed(workspaceId, seed.id, status);
      setSeeds((items) => items.map((item) => item.id === updated.id ? updated : item));
      setMessage(status === "active" ? "竞品种子已启用" : "竞品种子已暂停");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "竞品种子状态更新失败");
    } finally {
      setBusy(false);
    }
  };

  return <div className="view-content">
    <section className="page-heading compact"><div><p className="eyebrow">选品研究 / RES-004</p><h1>竞品种子</h1><p>仅维护受控竞品 HTTPS URL；公开采样必须遵守合规策略，不遍历全站。</p></div></section>
    <section className="panel import-panel"><form onSubmit={(event) => void add(event)}>
      <label>公开 HTTPS 商品页<input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://..." type="url" required /></label>
      <button className="secondary-button" disabled={busy}>{busy ? "保存中…" : "添加竞品"}</button>
    </form><p className="form-message">{message}</p></section>
    <section className="panel"><div className="list-summary"><span>受控竞品种子</span><b>{seeds.length} / 50</b></div>
      {seeds.length ? seeds.map((seed) => <div className="operation-row" key={seed.id}><span><strong>{seed.title ?? seed.url}</strong><small>{seed.url}</small></span><em>{seed.status === "active" ? "启用" : seed.status === "paused" ? "已暂停" : "已阻断"}</em>{seed.status !== "blocked" ? <button className="text-button" disabled={busy} onClick={() => void toggle(seed)}>{seed.status === "active" ? "暂停" : "启用"}</button> : null}</div>) : <div className="empty-search"><strong>尚未维护竞品种子</strong><span>先添加少量公开商品页，再进入公开采样流程。</span></div>}
    </section>
  </div>;
}
