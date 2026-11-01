"use client";

import { ArrowLeft, Circle, LoaderCircle, MousePointerClick, Square, StopCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useHost } from "@/lib/host";
import { codecFromConfig, concat, parsePscr, PSCR_FLAG_CONFIG, PSCR_FLAG_KEYFRAME } from "@/lib/h264";
import type { PhoneShare } from "@/lib/types";
import { Badge, Button } from "./ui";

const TAP_SLOP = 0.012; // normalized distance below which a press counts as a tap
const LONG_PRESS_MS = 450;
const KEYFRAME_REQUEST_INTERVAL_MS = 1000;

interface Press {
  x: number;
  y: number;
  t: number;
}

export function PhoneViewer({ share, controlEnabledOnPc }: { share: PhoneShare; controlEnabledOnPc: boolean }) {
  const { subscribeVideo, api } = useHost();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const press = useRef<Press | null>(null);
  // Only rendered client-side (the page needs live host state), so VideoDecoder is checkable here.
  const [status, setStatus] = useState<"waiting" | "playing" | "unsupported" | "error">(() =>
    typeof VideoDecoder === "undefined" ? "unsupported" : "waiting",
  );
  const [size, setSize] = useState({ width: share.width || 1080, height: share.height || 2400 });
  const [lastError, setLastError] = useState<string | null>(null);
  const canControl = share.control_available && controlEnabledOnPc;

  const requestKeyframe = useRef<() => void>(() => undefined);
  useEffect(() => {
    let last = 0;
    requestKeyframe.current = () => {
      const now = Date.now();
      if (now - last < KEYFRAME_REQUEST_INTERVAL_MS) return;
      last = now;
      void api("POST", `/phone/${encodeURIComponent(share.device_id)}/keyframe`).catch(() => undefined);
    };
  }, [api, share.device_id]);

  useEffect(() => {
    if (typeof VideoDecoder === "undefined") return;
    let config: Uint8Array | null = null;
    let codec: string | null = null;
    let needKey = true;
    let decoder: VideoDecoder | null = null;

    const makeDecoder = () =>
      new VideoDecoder({
        output: (frame) => {
          const canvas = canvasRef.current;
          if (canvas) {
            if (canvas.width !== frame.displayWidth || canvas.height !== frame.displayHeight) {
              canvas.width = frame.displayWidth;
              canvas.height = frame.displayHeight;
              setSize({ width: frame.displayWidth, height: frame.displayHeight });
            }
            canvas.getContext("2d")?.drawImage(frame, 0, 0);
          }
          frame.close();
          setStatus("playing");
        },
        error: (err) => {
          setLastError(err.message);
          setStatus("error");
          decoder = null;
          needKey = true;
          requestKeyframe.current();
        },
      });

    const configure = () => {
      if (!codec) return;
      if (!decoder || decoder.state === "closed") decoder = makeDecoder();
      decoder.configure({ codec, optimizeForLatency: true, hardwareAcceleration: "prefer-hardware" });
      needKey = true;
    };

    const unsubscribe = subscribeVideo(share.device_id, (frame) => {
      const packet = parsePscr(frame);
      if (!packet) return;
      if (packet.flags & PSCR_FLAG_CONFIG) {
        const next = codecFromConfig(packet.data);
        config = packet.data.slice();
        if (next && next !== codec) {
          codec = next;
          configure();
        } else if (!decoder || decoder.state !== "configured") {
          configure();
        }
        return;
      }
      if (!decoder || decoder.state !== "configured" || !config) {
        requestKeyframe.current();
        return;
      }
      const isKey = (packet.flags & PSCR_FLAG_KEYFRAME) !== 0;
      if (needKey && !isKey) {
        requestKeyframe.current();
        return;
      }
      // Drop delta frames when the decoder falls behind; resume at the next keyframe.
      if (!isKey && decoder.decodeQueueSize > 4) {
        needKey = true;
        requestKeyframe.current();
        return;
      }
      needKey = false;
      try {
        decoder.decode(
          new EncodedVideoChunk({
            type: isKey ? "key" : "delta",
            timestamp: packet.ptsUs,
            data: isKey ? concat(config, packet.data) : packet.data,
          }),
        );
      } catch (err) {
        setLastError((err as Error).message);
        needKey = true;
        requestKeyframe.current();
      }
    });
    requestKeyframe.current();
    return () => {
      unsubscribe();
      if (decoder && decoder.state !== "closed") decoder.close();
    };
  }, [share.device_id, subscribeVideo]);

  const send = useCallback(
    (event: Record<string, unknown>) =>
      void api("POST", `/phone/${encodeURIComponent(share.device_id)}/input`, event).catch(() => undefined),
    [api, share.device_id],
  );

  const normalized = (e: React.PointerEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height)),
    };
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (!canControl || e.button !== 0) return;
    (e.target as Element).setPointerCapture(e.pointerId);
    const p = normalized(e);
    press.current = { ...p, t: performance.now() };
  };

  const onPointerUp = (e: React.PointerEvent) => {
    const start = press.current;
    press.current = null;
    if (!canControl || !start) return;
    const end = normalized(e);
    const duration = Math.round(performance.now() - start.t);
    const moved = Math.hypot(end.x - start.x, end.y - start.y);
    if (moved < TAP_SLOP) {
      send({
        input_action: duration >= LONG_PRESS_MS ? "long_press" : "tap",
        normalized_x: start.x,
        normalized_y: start.y,
        duration_ms: duration >= LONG_PRESS_MS ? duration : 50,
      });
    } else {
      send({
        input_action: "swipe",
        normalized_x: start.x,
        normalized_y: start.y,
        end_x: end.x,
        end_y: end.y,
        duration_ms: Math.min(2000, Math.max(80, duration)),
      });
    }
  };

  const onWheel = (e: React.WheelEvent) => {
    if (!canControl) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const delta = Math.sign(e.deltaY) * 0.25;
    send({ input_action: "swipe", normalized_x: x, normalized_y: y, end_x: x, end_y: Math.min(1, Math.max(0, y - delta)), duration_ms: 150 });
  };

  const key = (name: "back" | "home" | "recents") => send({ input_action: "key", key: name });

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-medium">{share.device_name}</span>
          <Badge tone={status === "playing" ? "ok" : "neutral"}>
            {status === "playing" ? "Live" : status === "waiting" ? "Connecting…" : status === "unsupported" ? "Not supported" : "Recovering"}
          </Badge>
          {canControl ? (
            <Badge tone="accent"><MousePointerClick size={12} /> Control on</Badge>
          ) : (
            <Badge>{share.control_available ? "Control off on this PC" : "View only (phone)"}</Badge>
          )}
        </div>
        <Button
          variant="ghost"
          onClick={() => void api("POST", `/phone/${encodeURIComponent(share.device_id)}/stop`).catch(() => undefined)}
        >
          <StopCircle size={15} /> Ask phone to stop
        </Button>
      </div>

      <div className="relative flex min-h-0 flex-1 items-center justify-center rounded-xl bg-black p-3">
        <canvas
          ref={canvasRef}
          width={size.width}
          height={size.height}
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
          onPointerCancel={() => (press.current = null)}
          onContextMenu={(e) => {
            e.preventDefault();
            if (canControl) key("back");
          }}
          onWheel={onWheel}
          style={{ aspectRatio: `${size.width} / ${size.height}` }}
          className={`max-h-full max-w-full rounded-lg ${canControl ? "cursor-pointer" : "cursor-default"}`}
        />
        {status !== "playing" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-white/70">
            {status === "unsupported" ? (
              <span>This Windows build can&apos;t decode H.264 video.</span>
            ) : (
              <>
                <LoaderCircle className="animate-spin" />
                <span>{status === "error" ? `Recovering video${lastError ? ` (${lastError})` : ""}…` : "Waiting for video…"}</span>
              </>
            )}
          </div>
        )}
      </div>

      {canControl && (
        <div className="flex items-center justify-center gap-2">
          <Button onClick={() => key("back")} title="Back (or right-click)"><ArrowLeft size={15} /> Back</Button>
          <Button onClick={() => key("home")}><Circle size={15} /> Home</Button>
          <Button onClick={() => key("recents")}><Square size={14} /> Recents</Button>
        </div>
      )}
    </div>
  );
}
