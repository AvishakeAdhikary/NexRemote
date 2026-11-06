"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Connection, HostEvent, HostState } from "./types";

// Fallback for running the renderer in a plain browser against `uv run nexremote-server --dev`.
const DEV_CONNECTION: Connection = { baseUrl: "http://127.0.0.1:51888", token: "" };

export type VideoListener = (packet: Uint8Array) => void;

interface HostContextValue {
  connection: Connection | null;
  state: HostState | null;
  connected: boolean;
  refresh: () => Promise<void>;
  api: <T = unknown>(method: string, route: string, body?: unknown) => Promise<T>;
  subscribeEvents: (listener: (event: HostEvent) => void) => () => void;
  subscribeVideo: (deviceId: string, listener: VideoListener) => () => void;
  /** PAUD frames (phone playback audio) for one phone: tag+index+8-byte pts+PCM16 LE. */
  subscribeAudio: (deviceId: string, listener: VideoListener) => () => void;
}

const HostContext = createContext<HostContextValue | null>(null);

export function useHost(): HostContextValue {
  const value = useContext(HostContext);
  if (!value) throw new Error("useHost must be used inside <HostProvider>");
  return value;
}

/** Split a relay frame: [1 byte n][n bytes device id][PSCR frame]. */
function splitRelayFrame(data: ArrayBuffer): { deviceId: string; frame: Uint8Array } | null {
  const bytes = new Uint8Array(data);
  if (bytes.length < 2) return null;
  const n = bytes[0];
  if (bytes.length < 1 + n + 5) return null;
  return { deviceId: new TextDecoder().decode(bytes.subarray(1, 1 + n)), frame: bytes.subarray(1 + n) };
}

export function HostProvider({ children }: { children: ReactNode }) {
  // Outside Electron (renderer opened in a browser for development) talk to the dev server directly.
  const [connection, setConnection] = useState<Connection | null>(() =>
    typeof window !== "undefined" && !window.nexremote ? DEV_CONNECTION : null,
  );
  const [state, setState] = useState<HostState | null>(null);
  const [socketOpen, setSocketOpen] = useState(false);
  const connected = connection !== null && socketOpen;
  const eventListeners = useRef(new Set<(event: HostEvent) => void>());
  const videoListeners = useRef(new Map<string, Set<VideoListener>>());
  const audioListeners = useRef(new Map<string, Set<VideoListener>>());
  // Phones send SPS/PPS once per encoder start; keep the latest so viewers opened later can decode.
  const lastConfig = useRef(new Map<string, Uint8Array>());
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const bridge = window.nexremote;
    if (!bridge) return;
    void bridge.getConnection().then(setConnection);
    return bridge.onConnection(setConnection);
  }, []);

  const api = useCallback(
    async <T,>(method: string, route: string, body?: unknown): Promise<T> => {
      if (!connection) throw new Error("NexRemote host is not running yet");
      const response = await fetch(`${connection.baseUrl}${route}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(connection.token ? { Authorization: `Bearer ${connection.token}` } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (!response.ok) {
        let detail = `${response.status}`;
        try {
          detail = (await response.json()).detail ?? detail;
        } catch {
          // keep status code
        }
        throw new Error(String(detail));
      }
      return (await response.json()) as T;
    },
    [connection],
  );

  const refresh = useCallback(async () => {
    try {
      setState(await api<HostState>("GET", "/state"));
    } catch {
      // the event socket reports connectivity
    }
  }, [api]);

  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) return;
    refreshTimer.current = setTimeout(() => {
      refreshTimer.current = null;
      void refresh();
    }, 150);
  }, [refresh]);

  useEffect(() => {
    if (!connection) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const open = () => {
      const url = `${connection.baseUrl.replace(/^http/, "ws")}/events${connection.token ? `?token=${connection.token}` : ""}`;
      ws = new WebSocket(url);
      ws.binaryType = "arraybuffer";
      ws.onopen = () => setSocketOpen(true);
      ws.onmessage = (message) => {
        if (message.data instanceof ArrayBuffer) {
          const split = splitRelayFrame(message.data);
          if (!split) return;
          const f = split.frame;
          // "PAUD" = phone audio; everything else from a phone is "PSCR" video.
          if (f[0] === 0x50 && f[1] === 0x41 && f[2] === 0x55 && f[3] === 0x44) {
            audioListeners.current.get(split.deviceId)?.forEach((listener) => listener(f));
            return;
          }
          if (f.length > 5 && f[5] & 0x01) lastConfig.current.set(split.deviceId, f.slice());
          videoListeners.current.get(split.deviceId)?.forEach((listener) => listener(f));
          return;
        }
        const event = JSON.parse(message.data as string) as HostEvent;
        if (event.event === "hello") setState(event.state as HostState);
        else scheduleRefresh();
        eventListeners.current.forEach((listener) => listener(event));
      };
      ws.onclose = () => {
        setSocketOpen(false);
        if (!closed) retry = setTimeout(open, 1500);
      };
    };
    open();
    const poll = setInterval(() => void refresh(), 5000);
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      clearInterval(poll);
      ws?.close();
    };
  }, [connection, refresh, scheduleRefresh]);

  const subscribeEvents = useCallback((listener: (event: HostEvent) => void) => {
    eventListeners.current.add(listener);
    return () => void eventListeners.current.delete(listener);
  }, []);

  const subscribeVideo = useCallback((deviceId: string, listener: VideoListener) => {
    const map = videoListeners.current;
    if (!map.has(deviceId)) map.set(deviceId, new Set());
    map.get(deviceId)!.add(listener);
    const config = lastConfig.current.get(deviceId);
    if (config) queueMicrotask(() => listener(config));
    return () => {
      map.get(deviceId)?.delete(listener);
    };
  }, []);

  const subscribeAudio = useCallback((deviceId: string, listener: VideoListener) => {
    const map = audioListeners.current;
    if (!map.has(deviceId)) map.set(deviceId, new Set());
    map.get(deviceId)!.add(listener);
    return () => {
      map.get(deviceId)?.delete(listener);
    };
  }, []);

  const value = useMemo(
    () => ({ connection, state, connected, refresh, api, subscribeEvents, subscribeVideo, subscribeAudio }),
    [connection, state, connected, refresh, api, subscribeEvents, subscribeVideo, subscribeAudio],
  );
  return <HostContext.Provider value={value}>{children}</HostContext.Provider>;
}
