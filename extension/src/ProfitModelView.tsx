import { useEffect, useMemo, useState } from "react";
import {
  calculateSkuProfits,
  previewLogisticsTemplates,
  previewProfitReconciliation,
  listOzonFinanceAccruals,
  listOzonProductCatalog,
  type OzonProductSkuFact,
  type LogisticsTemplatePreview,
  type SkuProfitResult,
  type ProfitReconciliationPreview,
  type FinanceAccrualPage,
} from "./api";

interface SkuDraft {
  skuId: string;
  priceRub: number;
  landedCostRub: number;
  weightG: number;
  lengthMm: number;
  widthMm: number;
  heightMm: number;
}

const initialSku = (index: number): SkuDraft => ({
  skuId: `SKU-${index}`,
  priceRub: 1000,
  landedCostRub: 300,
  weightG: 500,
  lengthMm: 200,
  widthMm: 150,
  heightMm: 100,
});

const rub = (minor: number) => `${(minor / 100).toFixed(2)} ₽`;

const logisticsFieldGuide = [
  ["template_id", "物流模板编号", "必填"],
  ["fulfillment_type", "履约方式，如 FBS", "必填"],
  ["warehouse_id", "仓库编号", "必填"],
  ["route_id", "物流线路编号", "必填"],
  ["region_id", "区域编号", "必填"],
  ["version", "模板版本", "必填"],
  ["effective_from", "生效日期", "必填"],
  ["effective_to", "失效日期，留空表示长期有效", "可选"],
  ["volumetric_divisor_cm3_per_kg", "体积重系数", "必填"],
  ["max_weight_g", "计费重量上限，克", "必填"],
  ["base_fee_minor", "基础费用，最小货币单位", "必填"],
  ["additional_fee_minor", "超重附加费，留空按 0", "可选"],
  ["additional_step_g", "超重计费步长，留空按 0", "可选"],
  ["fee_rate_bps", "比例费率，基点，留空按 0", "可选"],
  ["currency", "币种，如 RUB", "必填"],
  ["source", "来源，如 manual", "必填"],
] as const;

export function ProfitModelView({ workspaceId: _workspaceId }: { workspaceId: string }) {
  const [productName, setProductName] = useState("待测商品");
  const [categoryId, setCategoryId] = useState("category-id");
  const [source, setSource] = useState<"manual" | "ozon">("manual");
  const [offers, setOffers] = useState<OzonProductSkuFact[]>([]);
  const [catalogQuery, setCatalogQuery] = useState("");
  const [selectedOfferIds, setSelectedOfferIds] = useState<string[]>([]);
  const [catalogModalOpen, setCatalogModalOpen] = useState(false);
  const [catalogNextCursor, setCatalogNextCursor] = useState<string | null>(null);
  const [commissionPercent, setCommissionPercent] = useState(15);
  const [commissionSource, setCommissionSource] = useState<"manual" | "ozon" | "missing">("manual");
  const [adPercent, setAdPercent] = useState(5);
  const [returnPercent, setReturnPercent] = useState(2);
  const [paymentPercent, setPaymentPercent] = useState(0);
  const [packagingRub, setPackagingRub] = useState(0);
  const [volumetricDivisor, setVolumetricDivisor] = useState(5000);
  const [logisticsFeesRub, setLogisticsFeesRub] = useState([50, 80, 120, 200]);
  const [skus, setSkus] = useState<SkuDraft[]>([initialSku(1)]);
  const [results, setResults] = useState<SkuProfitResult[]>([]);
  const [csv, setCsv] = useState("");
  const [templatePreview, setTemplatePreview] = useState<LogisticsTemplatePreview | null>(null);
  const [actualFeeCsv, setActualFeeCsv] = useState("");
  const [reconciliation, setReconciliation] = useState<ProfitReconciliationPreview | null>(null);
  const [financeAccruals, setFinanceAccruals] = useState<FinanceAccrualPage | null>(null);
  const [financeDateFrom, setFinanceDateFrom] = useState(() => new Date(Date.now() - 6 * 86400000).toISOString().slice(0, 10));
  const [financeDateTo, setFinanceDateTo] = useState(() => new Date().toISOString().slice(0, 10));
  const [busy, setBusy] = useState<string>("");
  const [message, setMessage] = useState("先确认规则，再运行本次预计利润测算。");

  useEffect(() => {
    let active = true;
    void listOzonProductCatalog(_workspaceId).then((page) => {
      if (active) { setOffers(page.items); setCatalogNextCursor(page.next_cursor); }
    }).catch(() => {
      if (active) setOffers([]);
    });
    return () => { active = false; };
  }, [_workspaceId]);

  const selectOffer = (offer: OzonProductSkuFact) => {
    setSource("ozon");
    setProductName(offer.name);
    if (offer.category_id) setCategoryId(offer.category_id);
    if (offer.commission_rate_bps !== null) {
      setCommissionPercent(offer.commission_rate_bps / 100);
      setCommissionSource("ozon");
    } else {
      setCommissionSource("missing");
    }
    setSkus([{ ...initialSku(1), skuId: offer.offer_id, priceRub: offer.price_minor === null ? 1000 : offer.price_minor / 100, weightG: offer.weight_g ?? initialSku(1).weightG, lengthMm: offer.length_mm ?? initialSku(1).lengthMm, widthMm: offer.width_mm ?? initialSku(1).widthMm, heightMm: offer.height_mm ?? initialSku(1).heightMm }]);
    setMessage(offer.commission_rate_bps === null
      ? `已载入 ${offer.offer_id} 的 Ozon 资料；未读取到当前佣金，请人工确认类目费率。`
      : `已载入 ${offer.offer_id} 的 Ozon 资料，并自动填入 ${offer.commission_rate_bps / 100}% 类目佣金；请确认后再计算。`);
  };

  const filteredOffers = offers.filter((offer) => {
    const query = catalogQuery.trim().toLowerCase();
    return !query || [offer.offer_id, offer.name, offer.category_id ?? ""].some((value) => value.toLowerCase().includes(query));
  });

  const toggleOffer = (offerId: string) => setSelectedOfferIds((current) => current.includes(offerId) ? current.filter((id) => id !== offerId) : [...current, offerId]);

  const importSelectedOffers = () => {
    const selected = offers.filter((offer) => selectedOfferIds.includes(offer.offer_id));
    if (!selected.length) {
      setMessage("请先勾选至少一个 Ozon 商品。");
      return;
    }
    selectOffer(selected[0]);
    setSkus(selected.map((offer, index) => ({
      ...initialSku(index + 1),
      skuId: offer.offer_id,
      priceRub: offer.price_minor === null ? initialSku(index + 1).priceRub : offer.price_minor / 100,
      weightG: offer.weight_g ?? initialSku(index + 1).weightG,
      lengthMm: offer.length_mm ?? initialSku(index + 1).lengthMm,
      widthMm: offer.width_mm ?? initialSku(index + 1).widthMm,
      heightMm: offer.height_mm ?? initialSku(index + 1).heightMm,
    })));
    setCatalogModalOpen(false);
    setMessage(`已导入 ${selected.length} 个商品 SKU；到岸成本和缺失规格仍需确认。`);
  };

  const loadCatalogPage = async (cursor?: string) => {
    const page = await listOzonProductCatalog(_workspaceId, cursor);
    setOffers((current) => cursor ? [...current, ...page.items] : page.items);
    setCatalogNextCursor(page.next_cursor);
    return page;
  };

  const syncCatalog = async () => {
    setCatalogModalOpen(true);
    setBusy("sync");
    try {
      const page = await loadCatalogPage();
      setMessage(`已同步 ${page.items.length} 个 Ozon 商品，可选择商品自动填充 SKU。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ozon 商品同步失败，请先检查 Seller 凭据");
    } finally {
      setBusy("");
    }
  };

  const loadMoreCatalog = async () => {
    if (!catalogNextCursor) return;
    setBusy("sync");
    try {
      const page = await loadCatalogPage(catalogNextCursor);
      setMessage(`已加载更多商品，本次新增 ${page.items.length} 个。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载下一页商品失败");
    } finally {
      setBusy("");
    }
  };

  const summary = useMemo(() => {
    const profitable = results.filter((item) => !item.is_negative).length;
    const totalProfit = results.reduce((total, item) => total + item.contribution_profit_minor, 0);
    const averageMargin = results.length
      ? results.reduce((total, item) => total + (item.contribution_margin_percent ?? 0), 0) / results.length
      : 0;
    return { profitable, totalProfit, averageMargin };
  }, [results]);

  const updateSku = (index: number, field: keyof SkuDraft, value: string) => setSkus((current) =>
    current.map((sku, itemIndex) => itemIndex === index
      ? { ...sku, [field]: field === "skuId" ? value : Number(value) } : sku));

  const run = async () => {
    setBusy("calculate");
    try {
      const effectiveAt = new Date().toISOString();
      setResults(await calculateSkuProfits({
        product_name: productName,
        category_id: categoryId,
        skus: skus.map((sku) => ({
          sku_id: sku.skuId,
          selling_price_minor: Math.round(sku.priceRub * 100),
          landed_cost_minor: Math.round(sku.landedCostRub * 100),
          weight_g: sku.weightG,
          length_mm: sku.lengthMm,
          width_mm: sku.widthMm,
          height_mm: sku.heightMm,
          logistics_template_id: "manual-fbs",
          ad_rate_bps: Math.round(adPercent * 100),
          return_loss_rate_bps: Math.round(returnPercent * 100),
          payment_rate_bps: Math.round(paymentPercent * 100),
          packaging_minor: Math.round(packagingRub * 100),
        })),
        commission_rules: [{
          category_id: categoryId,
          rate_bps: Math.round(commissionPercent * 100),
          trace: { version: `manual-${effectiveAt}`, source: "manual", effective_at: effectiveAt },
        }],
        logistics_templates: [{
          template_id: "manual-fbs",
          volumetric_divisor_cm3_per_kg: volumetricDivisor,
          bands: [1000, 3000, 10000, 30000].map((limit, index) => ({
            max_chargeable_weight_g: limit,
            fee_minor: Math.round((logisticsFeesRub[index] ?? 0) * 100),
          })),
          trace: { version: `manual-${effectiveAt}`, source: "manual", effective_at: effectiveAt },
        }],
      }));
      setMessage(`已完成 ${skus.length} 个 SKU 的预计利润测算，结果保留本次规则版本。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "利润计算失败，请检查输入规则");
    } finally {
      setBusy("");
    }
  };

  const previewCsv = async () => {
    setBusy("preview");
    try {
      setTemplatePreview(await previewLogisticsTemplates(csv));
      setMessage("物流模板已完成预览校验；通过后才可保存为新版本。 ");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "物流模板预览失败");
    } finally {
      setBusy("");
    }
  };

  const loadLogisticsCsvFile = (file: File | undefined) => {
    if (!file) return;
    void file.text().then((content) => {
      setCsv(content);
      setMessage(`已读取 ${file.name}，点击“预览模板”继续校验。`);
    }).catch(() => setMessage("读取物流模板文件失败，请确认文件为 UTF-8 CSV。"));
  };

  const downloadLogisticsSample = () => {
    const sample = "template_id,fulfillment_type,warehouse_id,route_id,region_id,version,effective_from,effective_to,volumetric_divisor_cm3_per_kg,max_weight_g,base_fee_minor,additional_fee_minor,additional_step_g,fee_rate_bps,currency,source\nmanual-fbs,FBS,warehouse-1,route-default,RU,2026-08-21,2026-08-21,,5000,1000,5000,0,0,0,RUB,manual\nmanual-fbs,FBS,warehouse-1,route-default,RU,2026-08-21,2026-08-21,,5000,3000,8000,0,0,0,RUB,manual\nmanual-fbs,FBS,warehouse-1,route-default,RU,2026-08-21,2026-08-21,,5000,10000,12000,0,0,0,RUB,manual";
    const url = URL.createObjectURL(new Blob(["\uFEFF" + sample], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "ozon-logistics-template-sample.csv";
    anchor.click();
    URL.revokeObjectURL(url);
    const guide = "Ozon SLJ 物流模板字段说明\n\n" +
      "必填字段（每行都必须有值）：template_id、fulfillment_type、warehouse_id、route_id、region_id、version、effective_from、volumetric_divisor_cm3_per_kg、max_weight_g、base_fee_minor、currency、source。\n\n可选字段：effective_to、additional_fee_minor、additional_step_g、fee_rate_bps；可选费用字段留空时按 0 处理，effective_to 留空表示长期有效。\n\n字段说明：\ntemplate_id：物流模板编号\nfulfillment_type：履约方式，如 FBS\nwarehouse_id：仓库编号\nroute_id：物流线路编号\nregion_id：区域编号\nversion：模板版本\neffective_from：生效日期\neffective_to：失效日期，可留空\nvolumetric_divisor_cm3_per_kg：体积重系数\nmax_weight_g：计费重量上限，克\nbase_fee_minor：基础费用，最小货币单位，5000 表示 50 RUB\nadditional_fee_minor：超重附加费\nadditional_step_g：超重计费步长\nfee_rate_bps：比例费率，基点\ncurrency：币种，如 RUB\nsource：来源，如 manual\n\n注意：CSV 表头保持英文，才能被系统导入；同一个 template_id 的多行必须使用一致的仓库、线路、区域和版本信息。";
    const guideUrl = URL.createObjectURL(new Blob(["\uFEFF" + guide], { type: "text/plain;charset=utf-8" }));
    const guideAnchor = document.createElement("a");
    guideAnchor.href = guideUrl;
    guideAnchor.download = "ozon-logistics-template-fields-中文说明.txt";
    guideAnchor.click();
    URL.revokeObjectURL(guideUrl);
    setMessage("已下载 CSV 模板和中文字段说明两个文件。CSV 表头保持英文以便导入。 ");
  };

  const previewActualFees = async () => {
    setBusy("reconcile");
    try {
      setReconciliation(await previewProfitReconciliation(actualFeeCsv));
      setMessage("实际费用已完成对账预览；确认后再进入批次保存。 ");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "实际费用对账失败");
    } finally {
      setBusy("");
    }
  };

  const exportReconciliation = () => {
    if (!reconciliation?.rows.length) return;
    const headers = ["order_id", "sku_id", "estimated_profit_minor", "actual_profit_minor", "estimated_logistics_minor", "actual_logistics_minor", "variance_minor", "variance_percent", "source"];
    const rows = reconciliation.rows.map((row) => headers.map((header) => row[header as keyof typeof row] ?? ""));
    const csvContent = [headers, ...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ozon-profit-reconciliation-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const syncFinance = async () => {
    setBusy("reconcile");
    try {
      setFinanceAccruals(await listOzonFinanceAccruals(_workspaceId, financeDateFrom, financeDateTo));
      setMessage("Ozon 财务 начисления已同步；请将已结算明细用于实际利润对账。 ");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ozon 财务同步失败");
    } finally {
      setBusy("");
    }
  };

  const exportResults = () => {
    if (!results.length) return;
    const headers = ["sku_id", "selling_price_minor", "chargeable_weight_g", "commission_minor", "logistics_minor", "contribution_profit_minor", "contribution_margin_percent", "break_even_price_minor", "status"];
    const rows = results.map((item) => [item.sku_id, item.transaction_price_minor, item.chargeable_weight_g, item.commission_minor, item.logistics_minor, item.contribution_profit_minor, item.contribution_margin_percent ?? "", item.break_even_price_minor, item.is_negative ? "negative" : "profitable"]);
    const csvContent = [headers, ...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ozon-profit-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return <div className="view-content profit-workbench">
    <section className="page-heading profit-heading">
      <div><p className="eyebrow">选品研究 / PROFIT-001</p><h1>SKU 利润轨道</h1>
        <p>把 Ozon 规格、你的物流规则和经营假设放在同一条线上，先判断能不能卖，再决定卖多少。</p></div>
        <span className="estimate-pill"><i />预计利润 · 规则驱动</span>
    </section>

    <section className="profit-rail" aria-label="利润测算摘要">
      <div className="profit-rail-intro"><span>本次测算</span><strong>{results.length || skus.length} SKU</strong><small>{source === "manual" ? "手动新品输入" : "Ozon 商品同步"}</small></div>
      <div className="profit-rail-stat"><span>盈利 SKU</span><strong>{results.length ? `${summary.profitable}/${results.length}` : "—"}</strong></div>
      <div className={`profit-rail-stat ${summary.totalProfit < 0 ? "is-risk" : "is-positive"}`}><span>总贡献利润</span><strong>{results.length ? rub(summary.totalProfit) : "—"}</strong></div>
      <div className="profit-rail-stat"><span>平均利润率</span><strong>{results.length ? `${summary.averageMargin.toFixed(1)}%` : "—"}</strong></div>
      <div className="profit-rail-status"><span className="status-dot" />{results.length ? "已完成计算" : "等待输入"}</div>
    </section>

    <div className="profit-layout">
      <div className="profit-main-column">
        <section className="panel profit-panel">
          <div className="profit-panel-heading"><div><p className="eyebrow">01 / 商品上下文</p><h2>先告诉我算哪一款</h2></div><span className="panel-index">INPUT</span></div>
          <div className="source-switch" role="tablist" aria-label="商品来源">
            <button className={source === "manual" ? "is-active" : ""} onClick={() => setSource("manual")} type="button">手动新品</button>
            <button className={source === "ozon" ? "is-active" : ""} disabled={!offers.length} onClick={() => setSource("ozon")} title={offers.length ? "选择已同步商品" : "暂无已同步商品"} type="button">Ozon 商品 <small>{offers.length ? `${offers.length} 个可用` : "等待同步"}</small></button>
            <button className="source-sync-button" disabled={busy !== ""} onClick={() => void syncCatalog()} type="button">{busy === "sync" ? "同步中…" : "同步 Ozon 商品"}</button>
          </div>
          {source === "ozon" && offers.length ? <div className="offer-picker"><label>筛选商品<input value={catalogQuery} onChange={(event) => setCatalogQuery(event.target.value)} placeholder="搜索 SKU、商品名称或类目…" /></label><div className="offer-picker-list">{filteredOffers.map((offer) => <label className="offer-picker-item" key={offer.offer_id}><input type="checkbox" checked={selectedOfferIds.includes(offer.offer_id)} onChange={() => toggleOffer(offer.offer_id)} /><span><strong>{offer.offer_id}</strong><small>{offer.name} · {offer.category_id ?? "类目待确认"}</small></span><b>{offer.price_minor === null ? "价格待确认" : `${(offer.price_minor / 100).toFixed(2)} ${offer.currency}`}</b></label>)}{!filteredOffers.length ? <small>没有匹配的商品，请调整搜索条件。</small> : null}</div><button className="secondary-button offer-import-button" disabled={!selectedOfferIds.length || busy !== ""} onClick={importSelectedOffers} type="button">导入已选商品（{selectedOfferIds.length}）</button><small>已同步 {offers.length} 个商品；规格缺失时会保留为待确认。</small></div> : null}
          <div className="form-grid profit-form-grid">
            <label>产品名称<input value={productName} onChange={(event) => setProductName(event.target.value)} /></label>
            <label>Ozon 类目编号<input value={categoryId} onChange={(event) => setCategoryId(event.target.value)} /></label>
          </div>
          <div className="sku-stack">
            {skus.map((sku, index) => <article className="sku-editor" key={`${sku.skuId}-${index}`}>
              <div className="sku-editor-head"><span className="sku-number">{String(index + 1).padStart(2, "0")}</span><div><strong>{sku.skuId}</strong><small>商品规格 · 包装后数据</small></div><button className="text-button" disabled={skus.length === 1} onClick={() => setSkus((current) => current.filter((_, itemIndex) => itemIndex !== index))} type="button">移除</button></div>
              <div className="form-grid sku-form-grid">
                <label>SKU 编号<input value={sku.skuId} onChange={(event) => updateSku(index, "skuId", event.target.value)} /></label>
                <label>售价（RUB）<input type="number" min="0.01" value={sku.priceRub} onChange={(event) => updateSku(index, "priceRub", event.target.value)} /></label>
                <label>到岸成本（RUB）<input type="number" min="0" value={sku.landedCostRub} onChange={(event) => updateSku(index, "landedCostRub", event.target.value)} /></label>
                <label>实重（g）<input type="number" min="1" value={sku.weightG} onChange={(event) => updateSku(index, "weightG", event.target.value)} /></label>
                <label>长（mm）<input type="number" min="1" value={sku.lengthMm} onChange={(event) => updateSku(index, "lengthMm", event.target.value)} /></label>
                <label>宽（mm）<input type="number" min="1" value={sku.widthMm} onChange={(event) => updateSku(index, "widthMm", event.target.value)} /></label>
                <label>高（mm）<input type="number" min="1" value={sku.heightMm} onChange={(event) => updateSku(index, "heightMm", event.target.value)} /></label>
              </div>
            </article>)}
          </div>
          <div className="profit-panel-actions"><button className="secondary-button" onClick={() => setSkus((current) => [...current, initialSku(current.length + 1)])} type="button">＋ 添加规格</button><button className="primary-button" disabled={busy !== ""} onClick={() => void run()} type="button">{busy === "calculate" ? "正在计算…" : "运行利润测算 →"}</button></div>
        </section>

        <section className="panel profit-panel result-panel">
          <div className="profit-panel-heading"><div><p className="eyebrow">03 / SKU 结果</p><h2>每一件商品，自己的利润答案</h2></div><div className="result-heading-actions"><button className="text-button" disabled={!results.length} onClick={exportResults} type="button">导出 CSV ↓</button><span className="panel-index">OUTPUT</span></div></div>
          {results.length ? <div className="profit-result-list">{results.map((item) => <article className={`profit-result-card ${item.is_negative ? "is-negative" : ""}`} key={item.sku_id}><div className="result-card-top"><div><span className="result-sku">{item.sku_id}</span><strong>{item.is_negative ? "需要调整" : "可以推进"}</strong></div><span className={`result-state ${item.is_negative ? "risk" : "good"}`}>{item.is_negative ? "负利润" : "盈利"}</span></div><div className="result-money"><strong>{rub(item.contribution_profit_minor)}</strong><span>贡献利润</span><b>{item.contribution_margin_percent?.toFixed(1) ?? "—"}%</b></div><div className="result-details"><span>保本价 <b>{rub(item.break_even_price_minor)}</b></span><span>物流 <b>{rub(item.logistics_minor)}</b></span><span>计费重量 <b>{item.chargeable_weight_g}g</b></span></div><div className="result-trace">佣金 {item.commission_trace.source} · 物流 {item.logistics_trace.source} · {item.logistics_trace.version}</div></article>)}</div> : <div className="profit-empty"><div className="empty-orbit"><span /><span /><span /></div><strong>结果会在这里展开</strong><p>填好 SKU 和物流规则后运行测算。系统会按每个规格的计费重量分别计算。</p></div>}
        </section>
      </div>

      <aside className="profit-side-column">
        <section className="panel profit-panel assumptions-panel"><div className="profit-panel-heading"><div><p className="eyebrow">02 / 规则与费用</p><h2>这次按什么算</h2></div><span className="panel-index">RULES</span></div><div className="rule-lock"><span className="rule-lock-icon">◈</span><div><strong>手动规则版本</strong><small>结果会记录本次佣金与物流规则</small></div><span className="rule-check">✓</span></div><div className="form-grid assumption-grid"><label>类目佣金（%）<input type="number" min="0" max="100" step="0.01" value={commissionPercent} onChange={(event) => setCommissionPercent(Number(event.target.value))} /></label><label>广告费率（%）<input type="number" min="0" max="100" step="0.01" value={adPercent} onChange={(event) => setAdPercent(Number(event.target.value))} /></label><label>退货损耗（%）<input type="number" min="0" max="100" step="0.01" value={returnPercent} onChange={(event) => setReturnPercent(Number(event.target.value))} /></label><label>支付费率（%）<input type="number" min="0" max="100" step="0.01" value={paymentPercent} onChange={(event) => setPaymentPercent(Number(event.target.value))} /></label><label>包装费（RUB）<input type="number" min="0" step="0.01" value={packagingRub} onChange={(event) => setPackagingRub(Number(event.target.value))} /></label><label>体积重系数<input type="number" min="1" value={volumetricDivisor} onChange={(event) => setVolumetricDivisor(Number(event.target.value))} /></label></div><div className="band-list"><div className="band-list-head"><span>FBS 物流分档</span><small>计费重量 · RUB</small></div>{logisticsFeesRub.map((fee, index) => <label key={index}><span>≤ {[1, 3, 10, 30][index]} kg</span><input type="number" min="0" step="0.01" value={fee} onChange={(event) => setLogisticsFeesRub((current) => current.map((item, itemIndex) => itemIndex === index ? Number(event.target.value) : item))} /></label>)}</div></section>
        <section className="panel profit-panel csv-panel"><div className="profit-panel-heading"><div><p className="eyebrow">RULE IMPORT</p><h2>导入物流模板</h2></div><span className="panel-index">CSV</span></div><p className="side-copy">Ozon 若能导出费率表，可选择文件；也可以下载样例后填写，或直接粘贴 CSV。</p><div className="template-file-actions"><label className="secondary-button">选择 CSV 文件<input type="file" accept=".csv,text/csv" onChange={(event) => loadLogisticsCsvFile(event.target.files?.[0])} /></label><button className="text-button" onClick={downloadLogisticsSample} type="button">下载模板样例 ↓</button></div><details className="field-guide"><summary>查看中文字段说明</summary><p>CSV 表头必须保持英文；同一 template_id 的多行必须使用一致的仓库、线路、区域和版本信息。</p><div className="field-guide-table">{logisticsFieldGuide.map(([field, meaning, required]) => <div className="field-guide-row" key={field}><code>{field}</code><span>{meaning}</span><small>{required}</small></div>)}</div></details><textarea value={csv} onChange={(event) => setCsv(event.target.value)} placeholder="粘贴物流模板 CSV…" rows={5} aria-label="物流模板 CSV" /><button className="secondary-button" disabled={!csv.trim() || busy !== ""} onClick={() => void previewCsv()} type="button">{busy === "preview" ? "校验中…" : "预览模板"}</button>{templatePreview ? <div className={`csv-preview ${templatePreview.errors.length ? "has-errors" : ""}`}><strong>{templatePreview.errors.length ? `${templatePreview.errors.length} 个问题` : `${templatePreview.templates.length} 个模板已识别`}</strong><small>{templatePreview.row_count} 行 · {templatePreview.errors.length ? templatePreview.errors[0] : "可以继续保存为版本"}</small></div> : null}</section>
        <section className="panel profit-panel csv-panel reconciliation-panel"><div className="profit-panel-heading"><div><p className="eyebrow">ACTUAL COSTS</p><h2>校准实际费用</h2></div><div className="result-heading-actions"><button className="text-button" disabled={!reconciliation?.rows.length} onClick={exportReconciliation} type="button">导出对账 ↓</button><span className="panel-index">RECON</span></div></div><p className="side-copy">优先从 Ozon 财务只读接口同步已产生的 начисления，也支持导入财务 CSV。</p><div className="finance-sync-fields"><label>开始日期<input type="date" value={financeDateFrom} onChange={(event) => setFinanceDateFrom(event.target.value)} /></label><label>结束日期<input type="date" value={financeDateTo} onChange={(event) => setFinanceDateTo(event.target.value)} /></label></div><button className="secondary-button" disabled={busy !== ""} onClick={() => void syncFinance()} type="button">{busy === "reconcile" ? "同步中…" : "从 Ozon 同步财务"}</button>{financeAccruals ? <div className="csv-preview"><strong>{financeAccruals.lines.length} 条 Ozon 财务明细</strong><small>{financeAccruals.dates.length} 天 · 来源 {financeAccruals.source}</small></div> : null}<textarea value={actualFeeCsv} onChange={(event) => setActualFeeCsv(event.target.value)} placeholder="或粘贴实际费用 CSV…" rows={5} aria-label="实际费用 CSV" /><button className="secondary-button" disabled={!actualFeeCsv.trim() || busy !== ""} onClick={() => void previewActualFees()} type="button">{busy === "reconcile" ? "对账中…" : "预览 CSV 对账"}</button>{reconciliation ? <div className={`csv-preview ${reconciliation.errors.length ? "has-errors" : ""}`}><strong>{reconciliation.rows.length} 条对账记录</strong><small>{reconciliation.errors.length ? `${reconciliation.errors.length} 个问题：${reconciliation.errors[0]}` : "预计与实际费用均已标准化"}</small></div> : null}</section>
      </aside>
    </div>
    {catalogModalOpen ? <div className="catalog-modal-backdrop" role="presentation"><section className="catalog-modal" role="dialog" aria-modal="true" aria-labelledby="catalog-modal-title"><div className="catalog-modal-head"><div><p className="eyebrow">OZON CATALOG</p><h2 id="catalog-modal-title">选择要导入的商品</h2></div><button className="text-button" onClick={() => setCatalogModalOpen(false)} type="button">关闭</button></div>{busy === "sync" ? <div className="catalog-modal-empty"><strong>正在读取 Ozon 商品…</strong><span>请稍候，系统正在获取商品、价格和规格。</span></div> : offers.length ? <><label className="catalog-modal-search">搜索商品<input value={catalogQuery} onChange={(event) => setCatalogQuery(event.target.value)} placeholder="SKU、Offer ID、商品名称或类目" /></label><div className="catalog-modal-list">{filteredOffers.map((offer) => <label className="catalog-modal-item" key={offer.offer_id}><input type="checkbox" checked={selectedOfferIds.includes(offer.offer_id)} onChange={() => toggleOffer(offer.offer_id)} /><span><strong>{offer.offer_id}</strong><small>{offer.name} · 类目 {offer.category_id ?? "待确认"} · 商品 ID {offer.ozon_product_id ?? "待确认"}</small><small>{offer.weight_g ?? "—"}g · {offer.length_mm ?? "—"}×{offer.width_mm ?? "—"}×{offer.height_mm ?? "—"}mm · 佣金 {offer.commission_rate_bps === null ? "待确认" : `${(offer.commission_rate_bps / 100).toFixed(2)}%`}</small></span><b>{offer.price_minor === null ? "价格待确认" : `${(offer.price_minor / 100).toFixed(2)} ${offer.currency}`}</b></label>)}</div><div className="catalog-modal-actions"><small>已加载 {offers.length} 个商品 · 已选 {selectedOfferIds.length} 个</small><div><button className="secondary-button" disabled={!catalogNextCursor || busy !== ""} onClick={() => void loadMoreCatalog()} type="button">{busy === "sync" ? "加载中…" : catalogNextCursor ? "加载下一页" : "已加载全部"}</button><button className="primary-button" disabled={!selectedOfferIds.length} onClick={importSelectedOffers} type="button">导入已选商品</button></div></div></> : <div className="catalog-modal-empty"><strong>没有读取到商品</strong><span>接口返回 0 个商品。请确认 Seller 凭据具备商品读取权限，并检查 Ozon 店铺是否已有商品。</span><button className="secondary-button" onClick={() => void syncCatalog()} type="button">重新同步</button></div>}</section></div> : null}
    <p className="form-message profit-message">{message}</p>
  </div>;
}
