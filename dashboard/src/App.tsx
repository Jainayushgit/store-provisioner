import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import { AdminCredentialsDialog } from "@/components/admin-credentials-dialog";
import { CreateStoreDialog } from "@/components/create-store-dialog";
import { StoreEventsPanel } from "@/components/store-events-panel";
import { StoresTable } from "@/components/stores-table";
import { Toast } from "@/components/ui/toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Store, StoreAdminCredentials, StoreDetail } from "@/types";

function App() {
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStore, setSelectedStore] = useState<StoreDetail | null>(null);
  const [credentialsOpen, setCredentialsOpen] = useState(false);
  const [credentialsStoreLabel, setCredentialsStoreLabel] = useState("");
  const [credentials, setCredentials] = useState<StoreAdminCredentials | null>(null);
  const [toast, setToast] = useState<{ title: string; message: string; type?: "info" | "error" } | null>(null);

  const counts = useMemo(() => {
    return {
      total: stores.length,
      ready: stores.filter((s) => s.status === "READY").length,
      failed: stores.filter((s) => s.status === "FAILED").length
    };
  }, [stores]);

  const refreshStores = async () => {
    setLoading(true);
    try {
      const next = await api.listStores();
      setStores(next);
    } catch (error) {
      setToast({ title: "Refresh failed", message: String(error), type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const selectStore = async (storeId: string) => {
    try {
      const detail = await api.getStore(storeId);
      setSelectedStore(detail);
    } catch (error) {
      setToast({ title: "Could not fetch store details", message: String(error), type: "error" });
    }
  };

  const createStore = async (payload: { engine: "woocommerce" | "medusa"; display_name?: string }) => {
    try {
      await api.createStore(payload);
      setToast({ title: "Store queued", message: "Provisioning job has been enqueued." });
      await refreshStores();
    } catch (error) {
      setToast({ title: "Create failed", message: String(error), type: "error" });
      throw error;
    }
  };

  const deleteStore = async (store: Store) => {
    try {
      await api.deleteStore(store.id);
      setStores((prev) => prev.map((s) => (s.id === store.id ? { ...s, status: "DELETING" } : s)));
      setToast({ title: "Delete queued", message: `${store.namespace} teardown requested.` });
      if (selectedStore?.id === store.id) {
        const detail = await api.getStore(store.id);
        setSelectedStore(detail);
      }
    } catch (error) {
      setToast({ title: "Delete failed", message: String(error), type: "error" });
    }
  };

  const viewCredentials = async (store: Store) => {
    try {
      const nextCredentials = await api.getStoreAdminCredentials(store.id);
      setCredentials(nextCredentials);
      setCredentialsStoreLabel(store.display_name || store.id.slice(0, 8));
      setCredentialsOpen(true);
    } catch (error) {
      setToast({ title: "Could not fetch credentials", message: String(error), type: "error" });
    }
  };

  useEffect(() => {
    void refreshStores();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let delay = 2500;

    const poll = async () => {
      while (!cancelled) {
        try {
          const next = await api.listStores();
          if (!cancelled) {
            setStores(next);
          }
          delay = 2500;
        } catch {
          delay = Math.min(delay * 2, 15000);
        }
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    };

    void poll();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 md:px-8">
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="font-serif text-3xl font-semibold tracking-tight">Store Provisioning Control Plane</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Kubernetes-native tenant orchestration for WooCommerce (Round 1).
          </p>
        </div>
        <CreateStoreDialog onCreate={createStore} />
      </header>

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Total stores</CardDescription>
            <CardTitle>{counts.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Ready</CardDescription>
            <CardTitle>{counts.ready}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Failed</CardDescription>
            <CardTitle>{counts.failed}</CardTitle>
          </CardHeader>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.7fr,1fr]">
        <StoresTable
          stores={stores}
          loading={loading}
          onRefresh={refreshStores}
          onDelete={deleteStore}
          onSelect={selectStore}
          onViewCredentials={viewCredentials}
        />
        <StoreEventsPanel store={selectedStore} />
      </section>

      <AdminCredentialsDialog
        open={credentialsOpen}
        onOpenChange={setCredentialsOpen}
        credentials={credentials}
        storeLabel={credentialsStoreLabel}
      />

      {toast && <Toast title={toast.title} message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </main>
  );
}

export default App;
