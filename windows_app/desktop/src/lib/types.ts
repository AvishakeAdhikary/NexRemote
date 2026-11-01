export interface Connection {
  baseUrl: string;
  token: string;
}

export interface FeatureStatus {
  supported: boolean;
  available: boolean;
  reason: string;
  action_required: string;
}

export interface SessionInfo {
  device_id: string;
  device_name: string;
  platform: string;
  secure: boolean;
  crypto: "legacy" | "v2";
  remote_address: string;
  client_version: string;
  phone_screen: boolean;
}

export interface ApprovalRequest {
  device_id: string;
  device_name: string;
  platform: string;
  remote_address: string;
  timeout_seconds: number;
  requested_at: string;
}

export interface PhoneShare {
  device_id: string;
  device_name: string;
  active: boolean;
  codec: string;
  width: number;
  height: number;
  fps: number;
  rotation: number;
  control_available: boolean;
}

export interface AdbStatus {
  tool_available: boolean;
  tool_path: string;
  device_detected: boolean;
  device_authorized: boolean;
  reverse_active: boolean;
  state: string;
  reason: string;
}

export interface HostState {
  version: string;
  running: boolean;
  can_serve: boolean;
  blocked_reason: "" | "legal_not_accepted" | "consent_required" | "remote_access_disabled";
  last_error: string;
  pc_name: string;
  device_id: string;
  ports: { secure: number; insecure: number; discovery: number };
  lan_ip: string;
  lan_ips: { interface: string; address: string }[];
  qr_payload: Record<string, string | number>;
  cert_fingerprint: string;
  legal: { required_version: string; accepted: boolean };
  consent: { remote_control: boolean; background: boolean; camera: boolean };
  sessions: SessionInfo[];
  approvals: ApprovalRequest[];
  capabilities: Record<string, unknown>;
  feature_status: Record<string, FeatureStatus>;
  phone_shares: PhoneShare[];
  adb: AdbStatus;
  startup?: { supported: boolean; enabled: boolean; state: string };
  data_dir: string;
}

export interface HostSettings {
  pc_name: string;
  device_id: string;
  server_port: number;
  server_port_insecure: number;
  discovery_port: number;
  enable_remote_access: boolean;
  max_clients: number;
  require_approval: boolean;
  log_level: string;
  auto_start: boolean;
  minimize_to_tray: boolean;
  show_notifications: boolean;
  theme_preference: "system" | "light" | "dark";
  remote_control_consent_granted: boolean;
  background_consent_granted: boolean;
  camera_access_consent_granted: boolean;
  phone_control_enabled: boolean;
}

export interface TrustedDevice {
  device_id: string;
  name: string;
  platform: string;
  first_connected: string;
  last_connected: string;
  has_key: boolean;
  connected: boolean;
}

export interface HostEvent {
  event: string;
  [key: string]: unknown;
}

export interface NexRemoteBridge {
  getConnection(): Promise<Connection | null>;
  onConnection(callback: (connection: Connection | null) => void): () => void;
  onNavigate(callback: (route: string) => void): () => void;
  openExternal(url: string): Promise<void>;
  setTheme(theme: "system" | "light" | "dark"): Promise<void>;
  quit(): Promise<void>;
  appVersion(): Promise<string>;
}

declare global {
  interface Window {
    nexremote?: NexRemoteBridge;
  }
}
