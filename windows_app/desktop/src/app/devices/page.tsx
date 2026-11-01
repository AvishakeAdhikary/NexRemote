"use client";

import { Trash2, Unplug } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, Empty, PageHeader, timeAgo } from "@/components/ui";
import { useHost } from "@/lib/host";
import type { TrustedDevice } from "@/lib/types";

export default function DevicesPage() {
  const { state, api, refresh } = useHost();
  const [devices, setDevices] = useState<TrustedDevice[]>([]);
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(() => api<TrustedDevice[]>("GET", "/devices").then(setDevices).catch(() => undefined), [api]);
  useEffect(() => {
    void load();
  }, [load, state?.sessions.length]);

  const forget = async (id: string) => {
    await api("DELETE", `/devices/${encodeURIComponent(id)}`);
    setConfirming(null);
    await Promise.all([load(), refresh()]);
  };
  const disconnect = async (id: string) => {
    await api("POST", `/sessions/${encodeURIComponent(id)}/disconnect`);
    await Promise.all([load(), refresh()]);
  };

  return (
    <>
      <PageHeader
        title="Devices"
        description="Phones you have approved. They reconnect without asking again until you remove them here."
      />
      <Card>
        {devices.length === 0 ? (
          <Empty>No approved devices yet. Pair a phone from the Dashboard.</Empty>
        ) : (
          <table className="w-full text-[13px]">
            <thead className="text-left text-xs text-muted">
              <tr>
                <th className="pb-2 font-medium">Device</th>
                <th className="pb-2 font-medium">First paired</th>
                <th className="pb-2 font-medium">Last seen</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {devices.map((d) => (
                <tr key={d.device_id}>
                  <td className="py-3">
                    <div className="font-medium">{d.name || "Unnamed device"}</div>
                    <div className="font-mono text-[11px] text-muted">{d.device_id}</div>
                  </td>
                  <td className="py-3 text-muted">{new Date(d.first_connected).toLocaleDateString()}</td>
                  <td className="py-3 text-muted">{d.connected ? "now" : timeAgo(d.last_connected)}</td>
                  <td className="py-3">
                    <div className="flex gap-1.5">
                      {d.connected ? <Badge tone="ok">Connected</Badge> : <Badge>Offline</Badge>}
                      {!d.has_key && <Badge tone="warn">No pairing key</Badge>}
                    </div>
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {d.connected && (
                        <Button variant="ghost" onClick={() => void disconnect(d.device_id)} title="Disconnect">
                          <Unplug size={15} />
                        </Button>
                      )}
                      {confirming === d.device_id ? (
                        <>
                          <Button onClick={() => setConfirming(null)}>Cancel</Button>
                          <Button variant="danger" onClick={() => void forget(d.device_id)}>Remove</Button>
                        </>
                      ) : (
                        <Button variant="ghost" onClick={() => setConfirming(d.device_id)} title="Remove device">
                          <Trash2 size={15} />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
