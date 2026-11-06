"use client";

import {
  ArrowLeft,
  Circle,
  LoaderCircle,
  Maximize,
  Minimize,
  MousePointerClick,
  Square,
  StopCircle,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useHost } from "@/lib/host";
import { codecFromConfig, concat, parsePscr, PSCR_FLAG_CONFIG, PSCR_FLAG_KEYFRAME } from "@/lib/h264";
import { PcmPlayer } from "@/lib/pcm-player";
import type { PhoneShare } from "@/lib/types";
import { Badge, Button, cx } from "./ui";

const TAP_SLOP = 0.012; // normalized distance below which a press counts as a tap
const LONG_PRESS_MS = 450;
const KEYFRAME_REQUEST_INTERVAL_MS = 1000;

interface Press {
  x: number;
  y: number;
  t: number;
}

interface Props {
  share: PhoneShare;
  controlEnabledOnPc: boolean;
  /** Grid tile: smaller chrome, click the title to focus. */
  compact?: boolean;
  onFocus?: () => void;
}

export function PhoneViewer({ share, controlEnabledOnPc, compact = false, onFocus }: Props) {
  const { subscribeVideo, subscribeAudio, api } = useHost();
  const rootRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const press = useRef<Press | null>(null);
  // Only rendered client-side (the page needs live host state), so VideoDecoder is checkable here.
  const [status, setStatus] = useState<"waiting" | "playing" | "unsupported" | "error">(() =>
    typeof VideoDecoder === "undefined" ? "unsupported" : "waiting",
  );
  const [size, setSize] = useState({ width: share.width || 1080, height: share.height || 2400 });
  const [lastError, setLastError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [audioWanted, setAudioWanted] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const canControl = share.control_available && controlEnabledOnPc;
  const id = encodeURIComponent(share.device_id);

  const requestKeyframe = useRef<() => void>(() => undefined);
  useEffect(() => {
    let last = 0;
    requestKeyframe.current = () => {
      const now = Date.now();
      if (now - last < KEYFRAME_REQUEST_INTERVAL_MS) return;
      last = now;
      void api("POST", `/phone/${id}/keyframe`).catch(() => undefined);
    };
  }, [api, id]);

  // ---- video -----------------------------------------------------------------------------
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

  // ---- audio -----------------------------------------------------------------------------
  const sampleRate = share.sample_rate || 48000;
  const channels = share.channels || 2;
  useEffect(() => {
    if (!audioWanted || !share.audio_active) return;
    const player = new PcmPlayer(sampleRate, channels);
    const unsubscribe = subscribeAudio(share.device_id, (frame) => player.push(frame));
    return () => {
      unsubscribe();
      player.close();
    };
  }, [audioWanted, share.audio_active, share.device_id, sampleRate, channels, subscribeAudio]);

  const toggleAudio = async () => {
    const enable = !audioWanted;
    setAudioError(null);
    setAudioWanted(enable);
    try {
      const result = await api<{ ok: boolean; error: string | null }>("POST", `/phone/${id}/audio`, { enabled: enable });
      if (!result.ok) {
        setAudioWanted(false);
        setAudioError(result.error === "audio_not_available_on_phone" ? "This phone can't share audio" : result.error);
      }
    } catch (err) {
      setAudioWanted(false);
      setAudioError((err as Error).message);
    }
  };

  // Stop the phone's audio stream when this viewer goes away.
  const audioWantedRef = useRef(audioWanted);
  useEffect(() => {
    audioWantedRef.current = audioWanted;
  }, [audioWanted]);
  useEffect(
    () => () => {
      if (audioWantedRef.current) void api("POST", `/phone/${id}/audio`, { enabled: false }).catch(() => undefined);
    },
    [api, id],
  );

  // ---- full screen -----------------------------------------------------------------------
  useEffect(() => {
    const onChange = () => setFullscreen(document.fullscreenElement === rootRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void rootRef.current?.requestFullscreen({ navigationUI: "hide" });
  };

  // ---- input -----------------------------------------------------------------------------
  const send = useCallback(
    (event: Record<string, unknown>) => void api("POST", `/phone/${id}/input`, event).catch(() => undefined),
    [api, id],
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

  // Keyboard shortcuts while the viewer has focus: Backspace = Back, Home = Home.
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!canControl) return;
    if (e.key === "Backspace") key("back");
    else if (e.key === "Home") key("home");
    else return;
    e.preventDefault();
  };

  const audioPlaying = audioWanted && share.audio_active;
  const audioButton = (
    <Button
      variant="ghost"
      onClick={() => void toggleAudio()}
      disabled={!share.audio_available}
      title={
        !share.audio_available
          ? "This phone can't share audio (needs Android 10+ and NexRemote 1.2 or newer)"
          : audioWanted
            ? "Mute this phone"
            : "Play this phone's audio on this PC"
      }
    >
      {audioPlaying ? <Volume2 size={15} /> : <VolumeX size={15} />}
      {!compact && (audioWanted ? (share.audio_active ? "Audio on" : "Starting audio…") : "Audio off")}
    </Button>
  );

  return (
    <div
      ref={rootRef}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      className={cx("flex h-full flex-col gap-3 outline-none", fullscreen && "bg-black p-0")}
    >
      {!fullscreen && (
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <button
              className={cx("truncate font-medium", onFocus && "hover:text-accent")}
              onClick={onFocus}
              disabled={!onFocus}
              title={onFocus ? "Open this phone" : undefined}
            >
              {share.device_name}
            </button>
            <Badge tone={status === "playing" ? "ok" : "neutral"}>
              {status === "playing" ? "Live" : status === "waiting" ? "Connecting…" : status === "unsupported" ? "Not supported" : "Recovering"}
            </Badge>
            {!compact &&
              (canControl ? (
                <Badge tone="accent">
                  <MousePointerClick size={12} /> Control on
                </Badge>
              ) : (
                <Badge>{share.control_available ? "Control off on this PC" : "View only (phone)"}</Badge>
              ))}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {audioButton}
            <Button variant="ghost" onClick={toggleFullscreen} title="Full screen (Esc to exit)">
              <Maximize size={15} />
              {!compact && "Full screen"}
            </Button>
            {!compact && (
              <Button variant="ghost" onClick={() => void api("POST", `/phone/${id}/stop`).catch(() => undefined)}>
                <StopCircle size={15} /> Ask phone to stop
              </Button>
            )}
          </div>
        </div>
      )}
      {audioError && !fullscreen && <p className="text-[12px] text-danger">{audioError}</p>}

      <div
        className={cx(
          "group relative flex min-h-0 flex-1 items-center justify-center bg-black",
          fullscreen ? "h-full w-full" : "rounded-xl p-3",
        )}
      >
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
          className={cx("max-h-full max-w-full", !fullscreen && "rounded-lg", canControl ? "cursor-pointer" : "cursor-default")}
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
        {fullscreen && (
          // Floating controls; fade in when the mouse moves over the top/bottom of the screen.
          <>
            <div className="absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/70 to-transparent px-5 py-4 text-white opacity-0 transition-opacity group-hover:opacity-100">
              <span className="font-medium">{share.device_name}</span>
              <div className="flex items-center gap-2">
                {audioButton}
                <Button variant="ghost" onClick={toggleFullscreen} title="Exit full screen (Esc)">
                  <Minimize size={15} /> Exit
                </Button>
              </div>
            </div>
            {canControl && (
              <div className="absolute inset-x-0 bottom-0 flex justify-center gap-2 bg-gradient-to-t from-black/70 to-transparent py-5 opacity-0 transition-opacity group-hover:opacity-100">
                <Button onClick={() => key("back")}><ArrowLeft size={15} /> Back</Button>
                <Button onClick={() => key("home")}><Circle size={15} /> Home</Button>
                <Button onClick={() => key("recents")}><Square size={14} /> Recents</Button>
              </div>
            )}
          </>
        )}
      </div>

      {canControl && !fullscreen && (
        <div className="flex items-center justify-center gap-2">
          <Button onClick={() => key("back")} title="Back (Backspace or right-click)"><ArrowLeft size={15} />{!compact && " Back"}</Button>
          <Button onClick={() => key("home")} title="Home"><Circle size={15} />{!compact && " Home"}</Button>
          <Button onClick={() => key("recents")} title="Recents"><Square size={14} />{!compact && " Recents"}</Button>
        </div>
      )}
    </div>
  );
}
