"use client";

import { useCallback, useEffect, useState } from "react";
import { useHost } from "./host";
import type { HostSettings } from "./types";

export function applyTheme(theme: HostSettings["theme_preference"]): void {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  void window.nexremote?.setTheme(theme);
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
