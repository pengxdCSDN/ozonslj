import { useEffect, useState } from "react";
import { listAdvertisingCampaigns, saveAdvertisingCampaignSync, type AdvertisingCampaign } from "./api";

interface Props { workspaceId: string; }

export function AdvertisingCampaignsView({ workspaceId }: Props) {
  const [campaigns, setCampaigns] = useState<AdvertisingCampaign[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const load = async () => { setBusy(true); try { setCampaigns(await listAdvertisingCampaigns(workspaceId)); } catch { setMessage("尚无已保存的广告活动快照。"); } finally { setBusy(false); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const sync = async () => { setBusy(true); try { const saved = await saveAdvertisingCampaignSync(workspaceId, [{ campaign_id: "stub-campaign", name: "开发模式广告活动", campaign_type: "search", status: "active", keywords: [{ keyword: "товары", bid_minor: 100, negative: false }] }]); setCampaigns(saved); setMessage("广告活动只读快照已保存。"); } catch { setMessage("同步失败，请检查 Performance API 凭据。"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Advertising Skill</p><h1>广告活动同步</h1><p>保存活动、关键词和否定词的只读快照，不执行预算或出价修改。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void sync()}>{busy ? "同步中…" : "同步活动快照"}</button>{message ? <p role="status">{message}</p> : null}{campaigns.map((campaign) => <div className="operation-row" key={campaign.campaign_id}><span><strong>{campaign.name}</strong><small>{campaign.campaign_type} · {campaign.keywords.length} 个关键词</small></span><em>{campaign.status} · {campaign.source}</em></div>)}</section></div>;
}
