"use client";

import { Smartphone } from "lucide-react";
import { useEffect, useState } from "react";
import { useHost } from "@/lib/host";
import type { ApprovalRequest } from "@/lib/types";
import { Button } from "./ui";

function Countdown({ request }: { request: ApprovalRequest }) {
  const deadline = new Date(request.requested_at).getTime() + request.timeout_seconds * 1000;
  const [left, setLeft] = useState(() => Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
  useEffect(() => {
    const id = setInterval(() => setLeft(Math.max(0, Math.ceil((deadline - Date.now()) / 1000))), 250);
    return () => clearInterval(id);
  }, [deadline]);
  return <span className="tabular-nums">{left}s</span>;
}

export function ApprovalDialog() {
  const { state, api, refresh } = useHost();
  const request = state?.approvals[0];
  if (!request) return null;

  const answer = async (approved: boolean) => {
    await api("POST", `/approvals/${encodeURIComponent(request.device_id)}`, { approved }).catch(() => undefined);
    await refresh();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <Smartphone size={20} />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Allow this device?</h2>
            <p className="text-[13px] text-muted">
              Expires in <Countdown request={request} />
            </p>
          </div>
        </div>
        <dl className="mt-5 grid grid-cols-[110px_1fr] gap-y-2 text-[13px]">
          <dt className="text-muted">Device</dt>
          <dd className="font-medium">{request.device_name}</dd>
          <dt className="text-muted">Platform</dt>
          <dd>{request.platform || "unknown"}</dd>
          <dt className="text-muted">Address</dt>
          <dd className="font-mono">{request.remote_address.split(":")[0] || "unknown"}</dd>
          <dt className="text-muted">Device ID</dt>
          <dd className="truncate font-mono text-xs">{request.device_id}</dd>
        </dl>
        <p className="mt-4 text-[13px] text-muted">
          Only allow devices you own or manage. Once allowed, this device can control this PC and reconnect without asking
          again until you remove it from Devices.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button onClick={() => void answer(false)}>Deny</Button>
          <Button variant="primary" onClick={() => void answer(true)}>Allow</Button>
        </div>
      </div>
    </div>
  );
}
