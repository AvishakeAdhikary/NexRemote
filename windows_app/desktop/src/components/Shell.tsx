"use client";

import {
  Download,
  Gauge,
  Heart,
  LoaderCircle,
  MonitorSmartphone,
  Puzzle,
  Scale,
  Settings as SettingsIcon,
  Smartphone,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useHost } from "@/lib/host";
import { applyPalette, applyTheme, useSettings } from "@/lib/settings";
import { ApprovalDialog } from "./ApprovalDialog";
import { ConsentGate, LegalGate } from "./Gates";
import { cx, StatusDot } from "./ui";

const NAV = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/devices/", label: "Devices", icon: Smartphone },
  { href: "/phone/", label: "Phone screen", icon: MonitorSmartphone },
  { href: "/get-app/", label: "Get the app", icon: Download },
  { href: "/compatibility/", label: "Compatibility", icon: Puzzle },
  { href: "/settings/", label: "Settings", icon: SettingsIcon },
  { href: "/legal/", label: "Legal", icon: Scale },
  { href: "/support/", label: "Support", icon: Heart },
];

export function Shell({ children }: { children: ReactNode }) {
  const { state, connected } = useHost();
  const { settings } = useSettings();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!settings) return;
    applyPalette(settings.color_palette);
    applyTheme(settings.theme_preference);
  }, [settings?.theme_preference, settings?.color_palette]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => window.nexremote?.onNavigate((route) => router.push(route)), [router]);

  if (!state) {
    return (
      <div className="flex h-[calc(100vh-var(--titlebar-h))] flex-col items-center justify-center gap-3 text-muted">
        <LoaderCircle className="animate-spin" />
        <span>Starting NexRemote host…</span>
      </div>
    );
  }
  if (!state.legal.accepted) return <LegalGate />;
  if (!state.consent.remote_control) return <ConsentGate />;

  const shares = state.phone_shares.length;
  return (
    <div className="flex h-[calc(100vh-var(--titlebar-h))]">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
        <div className="flex items-center gap-2.5 px-5 pb-4 pt-5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" className="h-8 w-8" />
          <div>
            <div className="font-semibold leading-tight">NexRemote</div>
            <div className="text-xs text-muted">Windows host</div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname?.startsWith(href.replace(/\/$/, ""));
            return (
              <Link
                key={href}
                href={href}
                className={cx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium",
                  active ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-text",
                )}
              >
                <Icon size={17} />
                <span className="flex-1">{label}</span>
                {href === "/phone/" && shares > 0 && (
                  <span className="rounded-full bg-accent px-1.5 text-[11px] text-accent-fg">{shares}</span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-border px-5 py-4 text-xs text-muted">
          <div className="flex items-center gap-2">
            <StatusDot on={state.running} />
            <span>{state.running ? "Server running" : "Server stopped"}</span>
          </div>
          <div className="mt-1">
            {state.sessions.length} connected · v{state.version}
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        {!connected && (
          <div className="bg-warn-soft px-6 py-2 text-[13px] text-warn">Reconnecting to the NexRemote host…</div>
        )}
        <div className="mx-auto max-w-5xl px-8 py-8">{children}</div>
      </main>
      <ApprovalDialog />
    </div>
  );
}
