export interface ProductOffer {
  offer_id: string;
  ozon_product_id: string | null;
  name: string;
  price: string;
  currency: string;
  available_stock: number;
}

export interface ProductOfferPage {
  items: ProductOffer[];
  total: number;
  next_cursor: string | null;
  source: string;
}

const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchProductOffers(signal?: AbortSignal): Promise<ProductOfferPage> {
  const response = await fetch(
    `${API_BASE_URL}/v1/store-workspaces/local/product-offers?limit=20`,
    {
      headers: { "X-Request-Id": crypto.randomUUID() },
      signal
    }
  );

  if (!response.ok) {
    throw new Error(`商品数据请求失败，状态码 ${response.status}`);
  }

  return (await response.json()) as ProductOfferPage;
}
