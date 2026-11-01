"use client";

import { CircleCheck, CircleAlert, ExternalLink } from "lucide-react";
import { Badge, Button, Card, PageHeader } from "@/components/ui";
import { useHost } from "@/lib/host";

const LABELS: Record<string, string> = {
  touchpad: "Touchpad, keyboard and mouse",
  media_control: "Media and volume",
  screen_share: "Share this PC's screen",
  screen_audio: "PC audio while sharing",
  file_explorer: "File explorer",
  task_manager: "Task manager",
  clipboard: "Clipboard",
  camera: "PC webcam",
  gamepad: "Virtual gamepad",
  usb_bridge: "USB connection (adb)",
  phone_screen: "Phone screen on this PC",
};

export default function CompatibilityPage() {
  const { state, api, refresh } = useHost();
  if (!state) return null;

  const action = (code: string) => {
    switch (code) {
      case "grant_camera_consent":
        return (
          <Button
            variant="primary"
            onClick={async () => {
              await api("POST", "/consent", { camera: true });
              await refresh();
            }}
          >
            Allow webcam streaming
          </Button>
        );
      case "install_vigem":
        return (
          <Button onClick={() => void window.nexremote?.openExternal("https://vigem.org/projects/ViGEm/How-to-Install/")}>
            Install ViGEmBus <ExternalLink size={14} />
          </Button>
        );
      case "install_platform_tools":
        return (
          <Button
            onClick={() =>
              void window.nexremote?.openExternal("https://developer.android.com/tools/releases/platform-tools")
            }
          >
            Get platform-tools <ExternalLink size={14} />
          </Button>
        );
      case "restart_server":
        return (
          <Button
            onClick={async () => {
              await api("POST", "/server/restart");
              await refresh();
            }}
          >
            Restart server
          </Button>
        );
      default:
        return null;
    }
  };

  return (
    <>
      <PageHeader
        title="Compatibility"
        description="What this PC can offer your phone right now. Phones see the same list and explain unavailable features."
      />
      <Card>
        <ul className="divide-y divide-border">
          {Object.entries(state.feature_status).map(([key, status]) => (
            <li key={key} className="flex items-center justify-between gap-6 py-3.5 first:pt-0 last:pb-0">
              <div className="flex min-w-0 items-start gap-3">
                {status.available ? (
                  <CircleCheck size={18} className="mt-0.5 shrink-0 text-ok" />
                ) : (
                  <CircleAlert size={18} className="mt-0.5 shrink-0 text-warn" />
                )}
                <div className="min-w-0">
                  <div className="font-medium">{LABELS[key] ?? key}</div>
                  <div className="text-[13px] text-muted">{status.reason}</div>
                </div>
              </div>
              <div className="shrink-0">
                {status.available ? <Badge tone="ok">Ready</Badge> : action(status.action_required) ?? <Badge tone="warn">Unavailable</Badge>}
              </div>
            </li>
          ))}
        </ul>
      </Card>
      <Card className="mt-5" title="USB connection" description="Connect over a cable when Wi-Fi is unavailable.">
        <ol className="list-decimal space-y-1.5 pl-5 text-[13px] text-muted">
          <li>Install Android platform-tools on this PC, or put adb.exe in <span className="font-mono">{state.data_dir}\tools\platform-tools</span>.</li>
          <li>On the phone, turn on Developer options › USB debugging and connect the cable.</li>
          <li>Accept the &ldquo;Allow USB debugging&rdquo; prompt on the phone.</li>
          <li>In the NexRemote app, choose Connect › USB.</li>
        </ol>
        <p className="mt-3 text-[13px]">
          Status: <span className="font-medium">{state.adb.reason}</span>
        </p>
      </Card>
    </>
  );
}
