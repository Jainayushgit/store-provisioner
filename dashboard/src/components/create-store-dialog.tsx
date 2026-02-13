import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";

interface CreateStoreDialogProps {
  onCreate: (payload: { engine: "woocommerce" | "medusa"; display_name?: string }) => Promise<void>;
}

export function CreateStoreDialog({ onCreate }: CreateStoreDialogProps) {
  const [open, setOpen] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onCreate({ engine: "woocommerce", display_name: displayName || undefined });
      setOpen(false);
      setDisplayName("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create New Store</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Store</DialogTitle>
          <DialogDescription>WooCommerce is enabled for Round 1. Medusa is stubbed and coming soon.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <label className="block text-sm font-medium">Store Display Name (optional)</label>
          <input
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none ring-ring focus:ring-2"
            placeholder="Acme Electronics"
          />

          <div className="space-y-2 rounded-lg border bg-muted/30 p-3 text-sm">
            <div className="flex items-center justify-between">
              <span>WooCommerce</span>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">Enabled</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Medusa</span>
              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700">Coming soon</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Queueing..." : "Create WooCommerce Store"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
