// Regenerates every raster icon (MSIX tiles, .ico, logo.png) from build/logo.svg.
// Run after changing the logo: `node scripts/gen-icons.mjs`.
import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const root = path.resolve(import.meta.dirname, "..");
const build = path.join(root, "build");
const appx = path.join(build, "appx");
const svg = fs.readFileSync(path.join(build, "logo.svg"), "utf8");
const mono = fs.readFileSync(path.join(build, "logo_monochrome.svg"), "utf8");

// The mark is a circle of radius 180 centred in a 500 viewBox. Crop to it with a hair of padding.
const tight = (src) => src.replace(/viewBox="[^"]*"/, 'viewBox="66 66 368 368"').replace(/ width="\d+" height="\d+"/, "");
// Monochrome for badges/lock screen: white strokes on transparent.
const monoWhite = tight(mono).replaceAll("#000000", "#ffffff");

async function mark(src, size) {
  return sharp(Buffer.from(src), { density: Math.max(72, (size / 368) * 72 * 4) })
    .resize(size, size)
    .png()
    .toBuffer();
}

// Place the mark at `fraction` of the shorter side, centred on a transparent canvas.
async function tile(file, w, h, fraction, src = tight(svg)) {
  const size = Math.max(1, Math.round(Math.min(w, h) * fraction));
  const img = await mark(src, size);
  await sharp({ create: { width: w, height: h, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: img, left: Math.round((w - size) / 2), top: Math.round((h - size) / 2) }])
    .png()
    .toFile(path.join(appx, file));
}

const scales = [100, 125, 150, 200, 400];
const jobs = [];
for (const s of scales) {
  const k = s / 100;
  const r = (n) => Math.round(n * k);
  jobs.push(tile(`Square150x150Logo.scale-${s}.png`, r(150), r(150), 0.66));
  jobs.push(tile(`Wide310x150Logo.scale-${s}.png`, r(310), r(150), 0.66));
  jobs.push(tile(`SmallTile.scale-${s}.png`, r(71), r(71), 0.72));
  jobs.push(tile(`LargeTile.scale-${s}.png`, r(310), r(310), 0.6));
  jobs.push(tile(`SplashScreen.scale-${s}.png`, r(620), r(300), 0.7));
  jobs.push(tile(`StoreLogo.scale-${s}.png`, r(50), r(50), 1));
  jobs.push(tile(`Square44x44Logo.scale-${s}.png`, r(44), r(44), 1));
  jobs.push(tile(`BadgeLogo.scale-${s}.png`, r(24), r(24), 1, monoWhite));
}
for (const t of [16, 24, 32, 48, 256]) {
  jobs.push(tile(`Square44x44Logo.targetsize-${t}.png`, t, t, 1));
  jobs.push(tile(`Square44x44Logo.altform-unplated_targetsize-${t}.png`, t, t, 1));
  jobs.push(tile(`Square44x44Logo.altform-lightunplated_targetsize-${t}.png`, t, t, 1));
}
jobs.push(tile("Square44x44Logo.targetsize-24_altform-unplated.png", 24, 24, 1));
jobs.push(tile("LockScreenLogo.scale-200.png", 48, 48, 1, monoWhite));
await Promise.all(jobs);

// logo.png (1024) and a multi-size PNG-in-ICO.
await sharp(await mark(tight(svg), 1024)).toFile(path.join(build, "logo.png"));
const icoSizes = [16, 20, 24, 32, 40, 48, 64, 128, 256];
// Windows only reliably decodes PNG for the 256 px entry; smaller entries must be classic DIBs,
// or the shell falls back to the exe's own icon (the Electron logo) in the taskbar and tray.
async function dib(size) {
  const { data } = await sharp(await mark(tight(svg), size)).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const maskRow = Math.ceil(size / 32) * 4;
  const out = Buffer.alloc(40 + size * size * 4 + maskRow * size);
  out.writeUInt32LE(40, 0);
  out.writeInt32LE(size, 4);
  out.writeInt32LE(size * 2, 8); // colour + mask
  out.writeUInt16LE(1, 12);
  out.writeUInt16LE(32, 14);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const src = (y * size + x) * 4;
      const dst = 40 + ((size - 1 - y) * size + x) * 4; // bottom-up BGRA
      out[dst] = data[src + 2];
      out[dst + 1] = data[src + 1];
      out[dst + 2] = data[src];
      out[dst + 3] = data[src + 3];
    }
  }
  return out; // AND mask left zero: alpha channel decides transparency
}
const pngs = await Promise.all(icoSizes.map((s) => (s >= 256 ? mark(tight(svg), s) : dib(s))));
const header = Buffer.alloc(6 + 16 * pngs.length);
header.writeUInt16LE(0, 0);
header.writeUInt16LE(1, 2);
header.writeUInt16LE(pngs.length, 4);
let offset = header.length;
pngs.forEach((png, i) => {
  const e = 6 + i * 16;
  const s = icoSizes[i];
  header.writeUInt8(s >= 256 ? 0 : s, e);
  header.writeUInt8(s >= 256 ? 0 : s, e + 1);
  header.writeUInt16LE(1, e + 4);
  header.writeUInt16LE(32, e + 6);
  header.writeUInt32LE(png.length, e + 8);
  header.writeUInt32LE(offset, e + 12);
  offset += png.length;
});
fs.writeFileSync(path.join(build, "logo.ico"), Buffer.concat([header, ...pngs]));
console.log(`wrote ${jobs.length} tiles, logo.png, logo.ico`);
