import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ToastProps {
  title: string;
  message: string;
  type?: "info" | "error";
  onClose: () => void;
}

export function Toast({ title, message, type = "info", onClose }: ToastProps) {
  return (
    <div
      className={`fixed bottom-4 right-4 z-50 w-[320px] rounded-lg border p-4 shadow-lg ${
        type === "error" ? "border-red-300 bg-red-50 text-red-900" : "border-border bg-card"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="text-sm opacity-85">{message}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
