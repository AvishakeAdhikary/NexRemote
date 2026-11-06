/**
 * Plays phone playback audio (PAUD frames) through Web Audio.
 *
 * Frame layout from the relay: "PAUD" (4) + index (1) + pts µs big-endian (8) + PCM16 LE interleaved.
 * Chunks are scheduled back to back on the AudioContext clock with a small jitter buffer; if the
 * schedule falls behind (network hiccup) it resets instead of piling up latency.
 */
const HEADER = 4 + 1 + 8;
const TARGET_LATENCY_S = 0.08;
const MAX_LATENCY_S = 0.35;

export class PcmPlayer {
  private ctx: AudioContext | null = null;
  private gain: GainNode | null = null;
  private nextTime = 0;

  constructor(
    private sampleRate: number,
    private channels: number,
  ) {}

  setFormat(sampleRate: number, channels: number): void {
    if (sampleRate === this.sampleRate && channels === this.channels) return;
    this.sampleRate = sampleRate;
    this.channels = channels;
    this.close();
  }

  setVolume(volume: number): void {
    if (this.gain) this.gain.gain.value = volume;
  }

  push(frame: Uint8Array): void {
    if (frame.length <= HEADER) return;
    if (!this.ctx) {
      this.ctx = new AudioContext({ sampleRate: this.sampleRate, latencyHint: "interactive" });
      this.gain = this.ctx.createGain();
      this.gain.connect(this.ctx.destination);
      this.nextTime = 0;
    }
    const ctx = this.ctx;
    const pcm = frame.subarray(HEADER);
    const channels = Math.max(1, this.channels);
    const samples = Math.floor(pcm.length / 2 / channels);
    if (samples === 0) return;
    const buffer = ctx.createBuffer(channels, samples, this.sampleRate);
    const view = new DataView(pcm.buffer, pcm.byteOffset, samples * channels * 2);
    for (let c = 0; c < channels; c++) {
      const out = buffer.getChannelData(c);
      for (let i = 0; i < samples; i++) out[i] = view.getInt16((i * channels + c) * 2, true) / 32768;
    }
    const now = ctx.currentTime;
    if (this.nextTime < now || this.nextTime - now > MAX_LATENCY_S) this.nextTime = now + TARGET_LATENCY_S;
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gain!);
    source.start(this.nextTime);
    this.nextTime += buffer.duration;
  }

  close(): void {
    void this.ctx?.close().catch(() => undefined);
    this.ctx = null;
    this.gain = null;
  }
}
