import { ExternalLink, KeyRound, RefreshCcw, ShieldUser, Trash2 } from "lucide-react";

import type { Store, StoreStatus } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface StoresTableProps {
  stores: Store[];
  loading: boolean;
  onRefresh: () => Promise<void>;
  onDelete: (store: Store) => Promise<void>;
  onSelect: (storeId: string) => Promise<void>;
  onViewCredentials: (store: Store) => Promise<void>;
}

function statusVariant(status: StoreStatus): "success" | "warning" | "danger" | "info" | "default" {
  if (status === "READY") return "success";
  if (status === "FAILED") return "danger";
  if (status === "PROVISIONING" || status === "DELETING") return "warning";
  if (status === "QUEUED") return "info";
  return "default";
}

export function StoresTable({ stores, loading, onRefresh, onDelete, onSelect, onViewCredentials }: StoresTableProps) {
  const adminUrl = (storeUrl: string) => `${storeUrl.replace(/\/$/, "")}/wp-admin`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-xl font-semibold">Stores</h2>
          <p className="text-sm text-muted-foreground">Provisioning lifecycle and tenant endpoints.</p>
        </div>
        <Button variant="secondary" onClick={onRefresh} disabled={loading}>
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="rounded-xl border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Namespace</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Failure</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stores.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No stores yet. Create one to start provisioning.
                </TableCell>
              </TableRow>
            )}
            {stores.map((store) => (
              <TableRow key={store.id} onClick={() => void onSelect(store.id)} className="cursor-pointer">
                <TableCell>
                  <div>
                    <p className="font-medium">{store.display_name || store.id.slice(0, 8)}</p>
                    <p className="text-xs text-muted-foreground">{store.engine}</p>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={statusVariant(store.status)}>{store.status}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{store.namespace}</TableCell>
                <TableCell>{new Date(store.created_at).toLocaleString()}</TableCell>
                <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">
                  {store.last_error || "-"}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-2">
                    {store.url && (
                      <Button asChild size="sm" variant="outline">
                        <a href={store.url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>
                          <ExternalLink className="h-3.5 w-3.5" /> Open
                        </a>
                      </Button>
                    )}
                    {store.url && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(event) => {
                          event.stopPropagation();
                          void onViewCredentials(store);
                        }}
                      >
                        <KeyRound className="h-3.5 w-3.5" /> Creds
                      </Button>
                    )}
                    {store.url && (
                      <Button asChild size="sm" variant="outline">
                        <a
                          href={adminUrl(store.url)}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <ShieldUser className="h-3.5 w-3.5" /> Admin
                        </a>
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={(event) => {
                        event.stopPropagation();
                        void onDelete(store);
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
