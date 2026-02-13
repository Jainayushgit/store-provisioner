export type StoreStatus =
  | "QUEUED"
  | "PROVISIONING"
  | "READY"
  | "FAILED"
  | "DELETING"
  | "DELETED";

export interface Store {
  id: string;
  engine: "woocommerce" | "medusa";
  display_name: string | null;
  namespace: string;
  release_name: string;
  status: StoreStatus;
  url: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface StoreEvent {
  id: number;
  event_type: string;
  message: string;
  created_at: string;
}

export interface StoreDetail extends Store {
  events: StoreEvent[];
}
