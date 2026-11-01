"use client";

import { MonitorSmartphone } from "lucide-react";
import { useState } from "react";
import { PhoneViewer } from "@/components/PhoneViewer";
import { cx, Empty, PageHeader } from "@/components/ui";
import { useHost } from "@/lib/host";
import { useSettings } from "@/lib/settings";

export default function PhonePage() {
  const { state } = useHost();
  const { settings } = useSettings();
  const shares = state?.phone_shares ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const active = shares.find((s) => s.device_id === selected) ?? shares[0];

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <PageHeader
        title="Phone screen"
        description="See a connected phone's screen here. Start sharing from the NexRemote app on the phone (Share my screen)."
      />
      {shares.length > 1 && (
        <div className="mb-3 flex gap-2">
          {shares.map((s) => (
            <button
              key={s.device_id}
              onClick={() => setSelected(s.device_id)}
              className={cx(
                "rounded-lg px-3 py-1.5 text-[13px] font-medium",
                s.device_id === active?.device_id ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2",
              )}
            >
              {s.device_name}
            </button>
          ))}
        </div>
      )}
      {active ? (
        <div className="min-h-0 flex-1">
          <PhoneViewer key={active.device_id} share={active} controlEnabledOnPc={settings?.phone_control_enabled ?? false} />
        </div>
      ) : (
        <Empty>
          <div className="flex flex-col items-center gap-3">
            <MonitorSmartphone size={28} />
            <div>No phone is sharing its screen.</div>
            <div className="max-w-md text-[13px]">
              On your phone, open NexRemote, connect to this PC and choose <b>Share my screen</b>. To control the phone
              from here, also turn on <b>Allow PC control</b> in the app.
            </div>
          </div>
        </Empty>
      )}
    </div>
  );
}
