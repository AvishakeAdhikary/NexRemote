"use client";

import { useEffect, useState } from "react";
import { Button, Card, PageHeader, SettingRow, Switch, TextInput } from "@/components/ui";
import { useHost } from "@/lib/host";
import { PALETTES, useSettings } from "@/lib/settings";

interface StartupState {
  supported: boolean;
  enabled: boolean;
  state: string;
}

// Callers pass key={value} so the draft resets when the saved value changes.
function NumberSetting({ value, onSave, min, max }: { value: number; onSave: (v: number) => void; min: number; max: number }) {
  const [draft, setDraft] = useState(String(value));
  const parsed = Number(draft);
  const valid = Number.isInteger(parsed) && parsed >= min && parsed <= max;
  return (
    <TextInput
      className="w-24 text-right font-mono"
      inputMode="numeric"
      value={draft}
      aria-invalid={!valid}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => (valid && parsed !== value ? onSave(parsed) : setDraft(String(value)))}
    />
  );
}

function PcNameField({ value, onSave }: { value: string; onSave: (name: string) => void }) {
  const [name, setName] = useState(value);
  return (
    <div className="flex gap-2">
      <TextInput value={name} maxLength={64} onChange={(e) => setName(e.target.value)} className="w-56" />
      <Button disabled={!name.trim() || name === value} onClick={() => onSave(name.trim())}>
        Save
      </Button>
    </div>
  );
}

export default function SettingsPage() {
  const { api, refresh, state } = useHost();
  const { settings, patch, error } = useSettings();
  const [startup, setStartup] = useState<StartupState | null>(null);

  useEffect(() => {
    void api<StartupState>("GET", "/startup").then(setStartup).catch(() => undefined);
  }, [api]);

  if (!settings) return null;

  const consent = async (body: Record<string, boolean>) => {
    await api("POST", "/consent", body);
    await refresh();
  };

  return (
    <>
      <PageHeader title="Settings" />
      {error && <p className="mb-4 rounded-lg bg-danger-soft px-4 py-2 text-[13px] text-danger">{error}</p>}

      <div className="space-y-5">
        <Card title="General">
          <SettingRow title="PC name" description="Shown on your phone when it finds this PC.">
            <PcNameField key={settings.pc_name} value={settings.pc_name} onSave={(n) => void patch({ pc_name: n })} />
          </SettingRow>
          <SettingRow title="Theme">
            <select
              className="h-9 rounded-lg border border-border bg-surface px-3 text-[13px]"
              value={settings.theme_preference}
              onChange={(e) => void patch({ theme_preference: e.target.value as typeof settings.theme_preference })}
            >
              <option value="system">Match Windows</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </SettingRow>
          <SettingRow title="Color palette" description="Accent colours for the whole app. Nexus red matches the Android app.">
            <div className="flex flex-wrap justify-end gap-2" role="radiogroup" aria-label="Color palette">
              {PALETTES.map((p) => {
                const selected = (settings.color_palette ?? "nexus") === p.id;
                return (
                  <button
                    key={p.id}
                    role="radio"
                    aria-checked={selected}
                    title={p.name}
                    onClick={() => void patch({ color_palette: p.id })}
                    className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-[12px] ${
                      selected ? "border-accent bg-accent-soft text-accent" : "border-border text-muted hover:bg-surface-2"
                    }`}
                  >
                    <span
                      className="h-3.5 w-3.5 rounded-full ring-1 ring-black/10"
                      style={{ background: `linear-gradient(135deg, ${p.swatch[0]} 50%, ${p.swatch[1]} 50%)` }}
                    />
                    {p.name}
                  </button>
                );
              })}
            </div>
          </SettingRow>
          <SettingRow
            title="Start with Windows"
            description={
              startup?.state === "disabled_by_user"
                ? "Turned off in Task Manager › Startup apps. Turn it back on there."
                : startup && !startup.supported
                  ? "Available in the installed app."
                  : "Start NexRemote in the background when you sign in."
            }
          >
            <Switch
              label="Start with Windows"
              checked={startup?.enabled ?? false}
              disabled={!startup?.supported || startup.state === "disabled_by_user" || startup.state.endsWith("policy")}
              onChange={async (v) => setStartup(await api<StartupState>("POST", "/startup", { enabled: v }))}
            />
          </SettingRow>
          <SettingRow title="Keep running in the tray" description="Closing the window keeps the host running so phones can connect.">
            <Switch label="Minimize to tray" checked={settings.minimize_to_tray} onChange={(v) => void patch({ minimize_to_tray: v })} />
          </SettingRow>
          <SettingRow title="Notifications" description="Connections and phone screen shares. Approval requests always notify.">
            <Switch label="Notifications" checked={settings.show_notifications} onChange={(v) => void patch({ show_notifications: v })} />
          </SettingRow>
        </Card>

        <Card title="Connections">
          <SettingRow title="Allow local network connections" description="Turn off to stop the server and refuse all phones.">
            <Switch
              label="Remote access"
              checked={settings.enable_remote_access}
              onChange={async (v) => {
                await patch({ enable_remote_access: v });
                await refresh();
              }}
            />
          </SettingRow>
          <SettingRow title="Ask before new devices connect" description="Recommended. Approved devices reconnect without asking.">
            <Switch label="Require approval" checked={settings.require_approval} onChange={(v) => void patch({ require_approval: v })} />
          </SettingRow>
          <SettingRow title="Maximum connected devices" description="0 means no limit.">
            <NumberSetting key={settings.max_clients} value={settings.max_clients} min={0} max={50} onSave={(v) => void patch({ max_clients: v })} />
          </SettingRow>
          <SettingRow title="Secure port" description="Encrypted (TLS) connections. Changing ports restarts the server.">
            <NumberSetting key={settings.server_port} value={settings.server_port} min={1024} max={65535} onSave={(v) => void patch({ server_port: v })} />
          </SettingRow>
          <SettingRow title="Fallback port" description="Used by older phones and USB connections.">
            <NumberSetting key={settings.server_port_insecure} value={settings.server_port_insecure} min={1024} max={65535} onSave={(v) => void patch({ server_port_insecure: v })} />
          </SettingRow>
          <SettingRow title="Discovery port" description="UDP port phones use to find this PC.">
            <NumberSetting key={settings.discovery_port} value={settings.discovery_port} min={1024} max={65535} onSave={(v) => void patch({ discovery_port: v })} />
          </SettingRow>
        </Card>

        <Card title="Privacy and permissions">
          <SettingRow title="Let phones use this PC's webcam" description="Phones can view the webcam only while this is on.">
            <Switch label="Webcam" checked={settings.camera_access_consent_granted} onChange={(v) => void consent({ camera: v })} />
          </SettingRow>
          <SettingRow
            title="Control shared phone screens"
            description="When a phone shares its screen and allows it, you can tap and swipe on it from this PC."
          >
            <Switch label="Phone control" checked={settings.phone_control_enabled} onChange={(v) => void patch({ phone_control_enabled: v })} />
          </SettingRow>
          <SettingRow title="Remote networking consent" description="Withdrawing consent stops the server until you allow it again.">
            <Button variant="danger" onClick={() => void consent({ remote_control: false })}>
              Withdraw
            </Button>
          </SettingRow>
        </Card>

        <Card title="About">
          <dl className="grid grid-cols-[150px_1fr] gap-y-2 text-[13px]">
            <dt className="text-muted">Version</dt>
            <dd>{state?.version}</dd>
            <dt className="text-muted">PC identifier</dt>
            <dd className="font-mono text-xs">{settings.device_id}</dd>
            <dt className="text-muted">Data folder</dt>
            <dd className="break-all font-mono text-xs">{state?.data_dir}</dd>
          </dl>
        </Card>
      </div>
    </>
  );
}
