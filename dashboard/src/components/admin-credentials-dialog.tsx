import { useEffect, useState } from "react";
import { Copy, ExternalLink, KeyRound, UserRound } from "lucide-react";

import type { StoreAdminCredentials } from "@/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";

interface AdminCredentialsDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  credentials: StoreAdminCredentials | null;
  storeLabel: string;
}

export function AdminCredentialsDialog({ open, onOpenChange, credentials, storeLabel }: AdminCredentialsDialogProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (open) {
      setCopyState("idle");
    }
  }, [open, credentials?.store_id]);

  const copyValue = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  };

  const helperText =
    copyState === "copied"
      ? "Copied to clipboard."
      : copyState === "failed"
        ? "Could not access clipboard. Please copy manually."
        : "Use these credentials to sign into Woo admin.";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Admin Credentials</DialogTitle>
          <DialogDescription>{storeLabel}</DialogDescription>
        </DialogHeader>

        {!credentials ? (
          <p className="text-sm text-muted-foreground">Credentials are unavailable.</p>
        ) : (
          <div className="space-y-4 py-2">
            <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Username</p>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 font-mono text-sm">
                  <UserRound className="h-4 w-4 text-muted-foreground" />
                  <span>{credentials.username}</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => void copyValue(credentials.username)}>
                  <Copy className="h-3.5 w-3.5" /> Copy
                </Button>
              </div>
            </div>

            <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Password</p>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 font-mono text-sm">
                  <KeyRound className="h-4 w-4 text-muted-foreground" />
                  <span>{credentials.password}</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => void copyValue(credentials.password)}>
                  <Copy className="h-3.5 w-3.5" /> Copy
                </Button>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">{helperText}</p>
          </div>
        )}

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {credentials && (
            <Button asChild>
              <a href={credentials.admin_url} target="_blank" rel="noreferrer">
                <ExternalLink className="h-3.5 w-3.5" /> Open Admin
              </a>
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
