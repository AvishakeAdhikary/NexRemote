"use client";

import { LayoutGrid, MonitorSmartphone, RectangleVertical } from "lucide-react";
import { useState } from "react";
import { PhoneViewer } from "@/components/PhoneViewer";
import { cx, Empty, PageHeader } from "@/components/ui";
import { useHost } from "@/lib/host";
import { useSettings } from "@/lib/settings";

type Layout = "grid" | "focus";

export default function PhonePage() {
  const { state } = useHost();
  const { settings } = useSettings();
  const shares = state?.phone_shares ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const [layout, setLayout] = useState<Layout>("grid");
  const active = shares.find((s) => s.device_id === selected) ?? shares[0];
  const control = settings?.phone_control_enabled ?? false;
  const showGrid = layout === "grid" && shares.length > 1;

  const focus = (deviceId: string) => {
    setSelected(deviceId);
    setLayout("focus");
  };

  return (
    <div className="flex h-[calc(100vh-4rem-var(--titlebar-h))] flex-col">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Phone screen"
          description="See and control the phones sharing their screen with this PC. Start sharing from the NexRemote app (Share my screen)."
        />
        {shares.length > 1 && (
          <div className="flex shrink-0 rounded-lg border border-border bg-surface p-1">
            {(
              [
                ["grid", LayoutGrid, "All phones"],
                ["focus", RectangleVertical, "One phone"],
              ] as const
            ).map(([value, Icon, label]) => (
              <button
                key={value}
                onClick={() => setLayout(value)}
                className={cx(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium",
                  layout === value ? "bg-accent-soft text-accent" : "text-muted hover:text-text",
                )}
              >
                <Icon size={15} /> {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {shares.length === 0 ? (
        <Empty>
          <div className="flex flex-col items-center gap-3">
            <MonitorSmartphone size={28} />
            <div>No phone is sharing its screen.</div>
            <div className="max-w-md text-[13px]">
              On your phone, open NexRemote, connect to this PC and choose <b>Share my screen</b>. To control the phone
              from here, also turn on <b>Allow PC control</b> in the app. Several phones can share at once.
            </div>
          </div>
        </Empty>
      ) : showGrid ? (
        <div
          className="grid min-h-0 flex-1 gap-4"
          style={{ gridTemplateColumns: `repeat(${Math.min(shares.length, 4)}, minmax(0, 1fr))` }}
        >
          {shares.map((share) => (
            <div key={share.device_id} className="min-h-0 rounded-xl border border-border bg-surface p-3">
              <PhoneViewer share={share} controlEnabledOnPc={control} compact onFocus={() => focus(share.device_id)} />
            </div>
          ))}
        </div>
      ) : (
        <>
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
          {active && (
            <div className="min-h-0 flex-1">
              <PhoneViewer key={active.device_id} share={active} controlEnabledOnPc={control} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
