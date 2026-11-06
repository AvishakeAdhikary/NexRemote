"use client";

import { useCallback, useEffect, useState } from "react";
import { useHost } from "./host";
import type { HostSettings, Palette } from "./types";

export const PALETTES: { id: Palette; name: string; swatch: [string, string] }[] = [
  { id: "nexus", name: "Nexus red", swatch: ["#e5202e", "#060606"] },
  { id: "ocean", name: "Ocean", swatch: ["#7c95ff", "#0b0d12"] },
  { id: "emerald", name: "Emerald", swatch: ["#2fd08f", "#050807"] },
  { id: "violet", name: "Violet", swatch: ["#a685ff", "#07060b"] },
  { id: "amber", name: "Amber", swatch: ["#ffb020", "#080604"] },
  { id: "graphite", name: "Graphite", swatch: ["#f2f2f2", "#111111"] },
];

let currentTheme: HostSettings["theme_preference"] = "dark";
let mediaListenerAttached = false;

function resolvedMode(theme: HostSettings["theme_preference"]): "light" | "dark" {
  if (theme !== "system") return theme;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Tell Electron the caption-button colours so they match the active palette. */
function syncTitleBar(): void {
  const css = getComputedStyle(document.documentElement);
  const surface = css.getPropertyValue("--surface").trim();
  const text = css.getPropertyValue("--text").trim();
  if (surface && text) void window.nexremote?.setTitleBarColors?.(surface, text);
}

export function applyTheme(theme: HostSettings["theme_preference"]): void {
  currentTheme = theme;
  const root = document.documentElement;
  root.dataset.mode = resolvedMode(theme);
  void window.nexremote?.setTheme(theme);
  if (!mediaListenerAttached) {
    mediaListenerAttached = true;
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (currentTheme === "system") applyTheme("system");
    });
  }
  syncTitleBar();
}

export function applyPalette(palette: Palette | undefined): void {
  document.documentElement.dataset.palette = palette ?? "nexus";
  syncTitleBar();
}

/** Current host settings, kept fresh from `settings_changed` events, plus a patch helper. */
export function useSettings() {
  const { api, connected, subscribeEvents } = useHost();
  const [settings, setSettings] = useState<HostSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!connected) return;
    void api<HostSettings>("GET", "/settings").then(setSettings).catch(() => undefined);
    return subscribeEvents((event) => {
      if (event.event === "settings_changed") {
        const { event: _ignored, ...rest } = event;
        void _ignored;
        setSettings(rest as unknown as HostSettings);
      }
    });
  }, [api, connected, subscribeEvents]);

  const patch = useCallback(
    async (changes: Partial<HostSettings>) => {
      setError(null);
      try {
        const updated = await api<HostSettings>("PATCH", "/settings", changes);
        setSettings(updated);
        if (changes.theme_preference) applyTheme(changes.theme_preference);
        if (changes.color_palette) applyPalette(changes.color_palette);
        return true;
      } catch (err) {
        setError((err as Error).message);
        return false;
      }
    },
    [api],
  );

  return { settings, patch, error };
}
