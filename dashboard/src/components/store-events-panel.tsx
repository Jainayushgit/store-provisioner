import type { StoreDetail } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface StoreEventsPanelProps {
  store: StoreDetail | null;
}

export function StoreEventsPanel({ store }: StoreEventsPanelProps) {
  if (!store) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Store Activity</CardTitle>
          <CardDescription>Select a store to inspect lifecycle events and failure reasons.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity: {store.display_name || store.namespace}</CardTitle>
        <CardDescription>Recent provisioning and teardown events.</CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="space-y-3">
          {store.events.length === 0 && <li className="text-sm text-muted-foreground">No events yet.</li>}
          {store.events.map((event) => (
            <li key={event.id} className="rounded-lg border bg-background p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{event.event_type}</p>
                <p className="text-xs text-muted-foreground">{new Date(event.created_at).toLocaleString()}</p>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{event.message}</p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
