"use client";

import { MonitorSmartphone, Power, ShieldCheck, ShieldOff, Usb } from "lucide-react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, PageHeader, StatusDot, timeAgo } from "@/components/ui";
import { useHost } from "@/lib/host";

interface ConnectionEvent {
  id: number;
  at: string;
  device_name: string;
  event: string;
  detail: string;
}

const BLOCKED: Record<string, string> = {
  remote_access_disabled: "Remote access is turned off in Settings.",
  consent_required: "Remote networking consent is required.",
  legal_not_accepted: "The legal documents need to be accepted.",
};

const EVENT_LABEL: Record<string, string> = {
  connected: "connected",
  disconnected: "disconnected",
  approved: "was approved",
  denied: "was denied or timed out",
  auth_failed: "failed pairing verification",
  connection_rejected: "was rejected",
};

export default function DashboardPage() {
  const { state, api, refresh } = useHost();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activity, setActivity] = useState<ConnectionEvent[]>([]);

  useEffect(() => {
    void api<ConnectionEvent[]>("GET", "/events/log?limit=8").then(setActivity).catch(() => undefined);
  }, [api, state?.sessions.length]);

  if (!state) return null;

  const toggle = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ ok: boolean; reason?: string }>("POST", state.running ? "/server/stop" : "/server/start");
      if (!result.ok && result.reason) setError(BLOCKED[result.reason] ?? result.reason);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Dashboard" description="Pair your phone, see who is connected, and start or stop the host." />

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Card
          title="Server"
          actions={
            <Button variant={state.running ? "secondary" : "primary"} onClick={() => void toggle()} disabled={busy}>
              <Power size={15} /> {state.running ? "Stop server" : "Start server"}
            </Button>
          }
        >
          <div className="flex items-center gap-2.5">
            <StatusDot on={state.running} />
            <span className="text-base font-medium">{state.running ? "Running and discoverable" : "Stopped"}</span>
          </div>
          {!state.running && (state.blocked_reason || state.last_error) && (
            <p className="mt-2 text-[13px] text-warn">{BLOCKED[state.blocked_reason] ?? state.last_error}</p>
          )}
          {error && <p className="mt-2 text-[13px] text-danger">{error}</p>}
          <dl className="mt-5 grid grid-cols-[150px_1fr] gap-y-2.5 text-[13px]">
            <dt className="text-muted">PC name</dt>
            <dd className="font-medium">{state.pc_name}</dd>
            <dt className="text-muted">Addresses</dt>
            <dd className="font-mono">
              {state.lan_ips.length ? state.lan_ips.map((ip) => ip.address).join(", ") : state.lan_ip}
            </dd>
            <dt className="text-muted">Ports</dt>
            <dd className="font-mono">
              {state.ports.secure} secure · {state.ports.insecure} fallback/USB · {state.ports.discovery} discovery
            </dd>
            <dt className="text-muted">Certificate</dt>
            <dd className="truncate font-mono text-xs" title={state.cert_fingerprint}>
              {state.cert_fingerprint.slice(0, 47)}…
            </dd>
            <dt className="text-muted">USB mode</dt>
            <dd className="flex items-center gap-2">
              <Usb size={14} className="text-muted" />
              {state.adb.reverse_active ? "Active" : state.adb.tool_available ? state.adb.reason : "ADB not installed"}
            </dd>
          </dl>
        </Card>

        <Card title="Quick connect" description="In the NexRemote app, tap Scan QR and point it here.">
          <div className="flex justify-center rounded-xl bg-white p-4">
            {state.running ? (
              <QRCodeSVG value={JSON.stringify(state.qr_payload)} size={220} level="M" marginSize={0} />
            ) : (
              <div className="flex h-[220px] items-center px-6 text-center text-[13px] text-neutral-500">
                The QR code appears when the server is running.
              </div>
            )}
          </div>
          <p className="mt-3 text-xs text-muted">
            Or enter <span className="font-mono">{state.lan_ip}</span> manually. Your phone must be on the same network.
          </p>
          <p className="mt-2 text-xs text-muted">
            Don&apos;t have the app yet?{" "}
            <Link href="/get-app/" className="font-medium text-accent hover:underline">
              Get it for Android
            </Link>
          </p>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Connected now" description="Phones currently connected to this PC.">
          {state.sessions.length === 0 ? (
            <Empty>No phones connected.</Empty>
          ) : (
            <ul className="divide-y divide-border">
              {state.sessions.map((s) => (
                <li key={s.device_id} className="flex items-center justify-between py-2.5">
                  <div>
                    <div className="font-medium">{s.device_name}</div>
                    <div className="text-xs text-muted">
                      {s.remote_address.split(":")[0]} · {s.platform || "device"} {s.client_version && `· app ${s.client_version}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {s.phone_screen && (
                      <Link href="/phone/">
                        <Badge tone="accent"><MonitorSmartphone size={12} /> Sharing</Badge>
                      </Link>
                    )}
                    {s.secure ? (
                      <Badge tone="ok"><ShieldCheck size={12} /> {s.crypto === "v2" ? "Encrypted" : "TLS"}</Badge>
                    ) : (
                      <Badge tone="warn"><ShieldOff size={12} /> {s.crypto === "v2" ? "Encrypted (no TLS)" : "Fallback"}</Badge>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent activity" description="Kept on this PC only.">
          {activity.length === 0 ? (
            <Empty>No activity yet.</Empty>
          ) : (
            <ul className="space-y-2 text-[13px]">
              {activity.map((e) => (
                <li key={e.id} className="flex justify-between gap-4">
                  <span>
                    <span className="font-medium">{e.device_name || "A device"}</span>{" "}
                    <span className="text-muted">{EVENT_LABEL[e.event] ?? e.event}</span>
                  </span>
                  <span className="shrink-0 text-xs text-muted">{timeAgo(e.at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
