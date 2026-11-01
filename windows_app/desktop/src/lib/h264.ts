// Helpers for the phone-screen stream: PSCR packet parsing and H.264 (Annex B) codec strings.

export const PSCR_FLAG_CONFIG = 0x01;
export const PSCR_FLAG_KEYFRAME = 0x02;

export interface PscrPacket {
  index: number;
  flags: number;
  ptsUs: number;
  data: Uint8Array;
}

/** PSCR frame: "PSCR" | index u8 | flags u8 | pts i64 BE (µs) | Annex B access unit. */
export function parsePscr(frame: Uint8Array): PscrPacket | null {
  if (frame.length < 14 || frame[0] !== 0x50 || frame[1] !== 0x53 || frame[2] !== 0x43 || frame[3] !== 0x52) return null;
  const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength);
  return {
    index: frame[4],
    flags: frame[5],
    ptsUs: Number(view.getBigInt64(6, false)),
    data: frame.subarray(14),
  };
}

/** NAL unit payloads (without start codes) from an Annex B byte stream. */
export function splitNals(data: Uint8Array): Uint8Array[] {
  const nals: Uint8Array[] = [];
  let start = -1;
  let i = 0;
  while (i + 2 < data.length) {
    const three = data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 1;
    const four = i + 3 < data.length && data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 0 && data[i + 3] === 1;
    if (three || four) {
      if (start >= 0) nals.push(data.subarray(start, i));
      i += three ? 3 : 4;
      start = i;
    } else {
      i++;
    }
  }
  if (start >= 0 && start < data.length) nals.push(data.subarray(start));
  return nals;
}

const hex = (n: number) => n.toString(16).padStart(2, "0").toUpperCase();

/** WebCodecs codec string ("avc1.PPCCLL") from the SPS in a codec-config packet. */
export function codecFromConfig(config: Uint8Array): string | null {
  const sps = splitNals(config).find((nal) => (nal[0] & 0x1f) === 7);
  if (!sps || sps.length < 4) return null;
  return `avc1.${hex(sps[1])}${hex(sps[2])}${hex(sps[3])}`;
}

export function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}
