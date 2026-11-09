// Electron main process: window, tray, app:// protocol for the static Next.js UI, and the Python sidecar.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  nativeImage,
  nativeTheme,
  net,
  Notification,
  protocol,
  shell,
  Tray,
} from "electron";
import { call, type HostSettings, type HostState } from "./api";
import { type Connection, Sidecar } from "./sidecar";

const APP_SCHEME = "app";
const APP_HOST = "nexremote";
const DEV_URL = "http://localhost:3123";
// Unpackaged runs use the Next dev server unless NEXREMOTE_RENDERER=static (test the built ./out via app://).
const isDev = !app.isPackaged && process.env.NEXREMOTE_RENDERER !== "static";
const EXTERNAL_ALLOWLIST = [
  "https://buymeacoffee.com/",
  "https://vigem.org/",
  "https://github.com/",
  "https://play.google.com/",
  "https://avishakeadhikary.github.io/",
  "https://developer.android.com/",
  "mailto:neural.nex.studios@gmail.com",
];
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*",
  "object-src 'none'",
  "base-uri 'none'",
  "frame-ancestors 'none'",
].join("; ");

// Inside the MSIX the package already supplies the AppUserModelID (tile icon, toasts); overriding it
// detaches the window from the package. In unpackaged dev runs an explicit ID with no matching shortcut
// makes the taskbar show electron.exe's icon, so only set it for a packaged non-Store build.
if (app.isPackaged && !process.windowsStore) app.setAppUserModelId("NeuralNexusStudios.NexRemote");
protocol.registerSchemesAsPrivileged([
  { scheme: APP_SCHEME, privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
]);

const sidecar = new Sidecar();
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let quitting = false;
let lastState: HostState | null = null;
let eventsSocket: WebSocket | null = null;

function iconPath(): string {
  return app.isPackaged ? path.join(process.resourcesPath, "icon.ico") : path.join(__dirname, "..", "build", "logo.ico");
}

function rendererRoot(): string {
  return path.join(__dirname, "..", "out");
}

function registerAppProtocol(): void {
  protocol.handle(APP_SCHEME, async (request) => {
    const url = new URL(request.url);
    const root = rendererRoot();
    let relative = decodeURIComponent(url.pathname);
    if (relative.endsWith("/")) relative += "index.html";
    let filePath = path.normalize(path.join(root, relative));
    if (!filePath.startsWith(root)) return new Response("Forbidden", { status: 403 });
    if (!fs.existsSync(filePath) && fs.existsSync(`${filePath}.html`)) filePath = `${filePath}.html`;
    if (!fs.existsSync(filePath) && fs.existsSync(path.join(filePath, "index.html")))
      filePath = path.join(filePath, "index.html");
    if (!fs.existsSync(filePath)) filePath = path.join(root, "404.html");
    const response = await net.fetch(pathToFileURL(filePath).toString());
    const headers = new Headers(response.headers);
    if (filePath.endsWith(".html")) headers.set("Content-Security-Policy", CSP);
    return new Response(response.body, { status: response.status, headers });
  });
}

function startUrl(route = "/"): string {
  return isDev ? `${DEV_URL}${route}` : `${APP_SCHEME}://${APP_HOST}${route}`;
}

// Caption-button colours follow the renderer's --surface/--text tokens (see globals.css).
// Caption-button colours. The renderer reports the active palette's --surface/--text through
// app:set-titlebar-colors; until then use the default Nexus palette.
let overlayColors: { color: string; symbolColor: string } | null = null;
function titleBarOverlay(): Electron.TitleBarOverlayOptions {
  const dark = nativeTheme.shouldUseDarkColors;
  const fallback = { color: dark ? "#111111" : "#ffffff", symbolColor: dark ? "#f2f2f2" : "#121212" };
  return { ...(overlayColors ?? fallback), height: 35 };
}

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1180,
    height: 800,
    minWidth: 900,
    minHeight: 620,
    show: false,
    title: "NexRemote",
    icon: iconPath(),
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#060606" : "#f6f5f5",
    // Frameless look: no system title bar, Windows still draws the caption buttons (and snap layouts).
    titleBarStyle: "hidden",
    titleBarOverlay: titleBarOverlay(),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      spellcheck: false,
    },
  });
  win.setMenu(null);
  win.once("ready-to-show", () => win.show());
  win.webContents.setWindowOpenHandler(({ url }) => {
    openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(startUrl(""))) {
      event.preventDefault();
      openExternal(url);
    }
  });
  win.on("close", (event) => {
    if (quitting) return;
    event.preventDefault();
    void handleClose(win);
  });
  void win.loadURL(startUrl());
  return win;
}

function openExternal(url: string): void {
  if (EXTERNAL_ALLOWLIST.some((prefix) => url.startsWith(prefix))) void shell.openExternal(url);
}

function showWindow(route?: string): void {
  if (!mainWindow || mainWindow.isDestroyed()) mainWindow = createWindow();
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
  if (route) mainWindow.webContents.send("app:navigate", route);
}

async function handleClose(win: BrowserWindow): Promise<void> {
  const conn = sidecar.current;
  let settings: HostSettings | null = null;
  try {
    if (conn) settings = await call<HostSettings>(conn, "GET", "/settings");
  } catch {
    settings = null;
  }
  if (!settings || !settings.minimize_to_tray) {
    await quit();
    return;
  }
  if (!settings.background_consent_granted) {
    const { response } = await dialog.showMessageBox(win, {
      type: "question",
      buttons: ["Keep running in the tray", "Quit NexRemote"],
      defaultId: 0,
      cancelId: 1,
      title: "Keep NexRemote running?",
      message: "Keep NexRemote running in the background?",
      detail:
        "Your phone can only connect while NexRemote is running. When you close the window it will stay in the system tray, and you can quit it from the tray menu at any time. You can change this in Settings.",
    });
    if (response !== 0) {
      await quit();
      return;
    }
    if (conn) await call(conn, "POST", "/consent", { background: true }).catch(() => undefined);
  }
  win.hide();
}

async function refreshTray(): Promise<void> {
  if (!tray) return;
  const conn = sidecar.current;
  if (conn) {
    try {
      lastState = await call<HostState>(conn, "GET", "/state");
    } catch {
      lastState = null;
    }
  }
  const running = lastState?.running ?? false;
  const devices = lastState?.sessions.length ?? 0;
  const status = !conn
    ? "Host starting…"
    : running
      ? `Server running · ${devices} device${devices === 1 ? "" : "s"} connected`
      : "Server stopped";
  tray.setToolTip(`NexRemote — ${status}`);
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Show NexRemote", click: () => showWindow() },
      {
        label: running ? "Stop server" : "Start server",
        enabled: !!conn && (running || (lastState?.can_serve ?? false)),
        click: async () => {
          const c = sidecar.current;
          if (c) await call(c, "POST", running ? "/server/stop" : "/server/start").catch(() => undefined);
          await refreshTray();
        },
      },
      { type: "separator" },
      { label: status, enabled: false },
      { type: "separator" },
      { label: "Quit NexRemote", click: () => void quit() },
    ]),
  );
}

function createTray(): void {
  tray = new Tray(nativeImage.createFromPath(iconPath()));
  tray.on("click", () => showWindow());
  void refreshTray();
}

function subscribeEvents(conn: Connection): void {
  eventsSocket?.close();
  const ws = new WebSocket(`${conn.baseUrl.replace("http", "ws")}/events?token=${conn.token}`);
  ws.binaryType = "arraybuffer";
  eventsSocket = ws;
  ws.onmessage = (message) => {
    if (typeof message.data !== "string") return; // video frames are for the renderer
    let event: { event: string; [key: string]: unknown };
    try {
      event = JSON.parse(message.data);
    } catch {
      return;
    }
    switch (event.event) {
      case "approval_requested":
        notify(
          "New device wants to connect",
          `${String(event.device_name)} is asking to control this PC. Open NexRemote to allow or deny.`,
          "/",
          true,
        );
        break;
      case "phone_screen_started":
        notify("Phone screen shared", `${String(event.device_name)} is sharing its screen.`, "/phone/");
        break;
      case "session_connected":
      case "session_disconnected":
      case "server_state":
        void refreshTray();
        break;
    }
  };
  ws.onclose = () => {
    if (eventsSocket === ws) eventsSocket = null;
    setTimeout(() => {
      const current = sidecar.current;
      if (!quitting && current && !eventsSocket) subscribeEvents(current);
    }, 2000);
  };
}

async function notify(title: string, body: string, route: string, important = false): Promise<void> {
  const conn = sidecar.current;
  if (conn && !important) {
    const settings = await call<HostSettings>(conn, "GET", "/settings").catch(() => null);
    if (settings && !settings.show_notifications) return;
  }
  if (important && mainWindow && !mainWindow.isVisible()) showWindow(route);
  if (!Notification.isSupported()) return;
  const n = new Notification({ title, body, icon: iconPath(), urgency: important ? "critical" : "normal" });
  n.on("click", () => showWindow(route));
  n.show();
  if (important) mainWindow?.flashFrame(true);
}

async function quit(): Promise<void> {
  quitting = true;
  eventsSocket?.close();
  await sidecar.stop();
  tray?.destroy();
  app.quit();
}

function broadcastConnection(conn: Connection | null): void {
  for (const win of BrowserWindow.getAllWindows()) win.webContents.send("host:connection", conn);
}

async function startSidecar(): Promise<void> {
  try {
    const conn = await sidecar.start();
    broadcastConnection(conn);
    subscribeEvents(conn);
    void refreshTray();
    const settings = await call<HostSettings>(conn, "GET", "/settings").catch(() => null);
    if (settings) nativeTheme.themeSource = settings.theme_preference;
  } catch (err) {
    dialog.showErrorBox("NexRemote could not start", `${(err as Error).message}\n\nLogs: ${app.getPath("logs")}`);
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => showWindow());

  ipcMain.handle("host:connection", () => sidecar.current);
  ipcMain.handle("app:open-external", (_event, url: string) => openExternal(url));
  nativeTheme.on("updated", () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.setTitleBarOverlay(titleBarOverlay());
  });
  ipcMain.handle("app:set-titlebar-colors", (_event, color: string, symbolColor: string) => {
    const hex = /^#[0-9a-fA-F]{3,8}$/;
    if (!hex.test(color) || !hex.test(symbolColor)) return;
    overlayColors = { color, symbolColor };
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.setTitleBarOverlay(titleBarOverlay());
  });
  ipcMain.handle("app:set-theme", (_event, theme: "system" | "light" | "dark") => {
    nativeTheme.themeSource = theme;
  });
  ipcMain.handle("app:quit", () => quit());
  ipcMain.handle("app:version", () => app.getVersion());

  sidecar.on("ready", (conn: Connection) => {
    broadcastConnection(conn);
    subscribeEvents(conn);
  });
  sidecar.on("restarting", () => broadcastConnection(null));
  sidecar.on("failed", (err: Error) => {
    dialog.showErrorBox("NexRemote host stopped", `${err.message}\n\nLogs: ${app.getPath("logs")}`);
  });

  app.whenReady().then(async () => {
    registerAppProtocol();
    createTray();
    mainWindow = createWindow();
    await startSidecar();
    setInterval(() => void refreshTray(), 10_000);
  });

  app.on("window-all-closed", () => {
    // Stay alive in the tray; quitting goes through quit().
  });
  app.on("before-quit", (event) => {
    if (!quitting) {
      event.preventDefault();
      void quit();
    }
  });
}
