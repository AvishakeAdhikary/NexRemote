// Small typed client for the control API, used by the main process (tray, close handling, notifications).
import type { Connection } from "./sidecar";

export interface HostState {
  running: boolean;
  can_serve: boolean;
  blocked_reason: string;
  pc_name: string;
  sessions: { device_id: string; device_name: string }[];
  legal: { accepted: boolean };
  consent: { remote_control: boolean; background: boolean; camera: boolean };
}

export interface HostSettings {
  minimize_to_tray: boolean;
  show_notifications: boolean;
  background_consent_granted: boolean;
  theme_preference: "system" | "light" | "dark";
  color_palette?: string;
}

export async function call<T>(conn: Connection, method: string, route: string, body?: unknown): Promise<T> {
  const response = await fetch(`${conn.baseUrl}${route}`, {
    method,
    headers: { Authorization: `Bearer ${conn.token}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) throw new Error(`${method} ${route} -> ${response.status}`);
  return (await response.json()) as T;
}
