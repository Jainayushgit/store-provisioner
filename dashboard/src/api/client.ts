import type { Store, StoreAdminCredentials, StoreDetail } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  listStores: () => request<Store[]>("/stores"),
  getStore: (storeId: string) => request<StoreDetail>(`/stores/${storeId}`),
  getStoreAdminCredentials: (storeId: string) =>
    request<StoreAdminCredentials>(`/stores/${storeId}/admin-credentials`),
  createStore: (payload: { engine: "woocommerce" | "medusa"; display_name?: string }) =>
    request<{ store_id: string }>("/stores", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  deleteStore: (storeId: string) => request<{ store_id: string }>(`/stores/${storeId}`, { method: "DELETE" })
};
