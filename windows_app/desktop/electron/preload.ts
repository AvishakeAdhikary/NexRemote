// The only bridge between the sandboxed renderer and the main process.
import { contextBridge, ipcRenderer } from "electron";

interface Connection {
  baseUrl: string;
  token: string;
}

contextBridge.exposeInMainWorld("nexremote", {
  getConnection: (): Promise<Connection | null> => ipcRenderer.invoke("host:connection"),
  onConnection: (callback: (connection: Connection | null) => void) => {
    const listener = (_event: unknown, connection: Connection | null) => callback(connection);
    ipcRenderer.on("host:connection", listener);
    return () => ipcRenderer.removeListener("host:connection", listener);
  },
  onNavigate: (callback: (route: string) => void) => {
    const listener = (_event: unknown, route: string) => callback(route);
    ipcRenderer.on("app:navigate", listener);
    return () => ipcRenderer.removeListener("app:navigate", listener);
  },
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke("app:open-external", url),
  setTheme: (theme: "system" | "light" | "dark"): Promise<void> => ipcRenderer.invoke("app:set-theme", theme),
  quit: (): Promise<void> => ipcRenderer.invoke("app:quit"),
  appVersion: (): Promise<string> => ipcRenderer.invoke("app:version"),
});
