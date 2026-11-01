// Spawns and supervises the Python host (nexremote-server) and exposes its control API address.
import { ChildProcess, spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { EventEmitter } from "node:events";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { app } from "electron";

export interface Connection {
  baseUrl: string;
  token: string;
}

const READY_PREFIX = "NEXREMOTE_READY";
const MAX_RESTARTS_PER_MINUTE = 5;

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => (typeof address === "object" && address ? resolve(address.port) : reject(new Error("no port"))));
    });
  });
}

function serverCommand(port: number, token: string): { command: string; args: string[]; cwd: string } {
  const common = ["--control-port", String(port), "--control-token", token, "--parent-pid", String(process.pid)];
  if (app.isPackaged) {
    const exe = path.join(process.resourcesPath, "server", "nexremote-server.exe");
    return { command: exe, args: common, cwd: path.dirname(exe) };
  }
  // Development: run the uv project directly so Python edits apply on restart.
  const project = path.resolve(__dirname, "..", "..", "server");
  return { command: "uv", args: ["run", "--project", project, "nexremote-server", ...common], cwd: project };
}

export class Sidecar extends EventEmitter {
  private child: ChildProcess | null = null;
  private connection: Connection | null = null;
  private restarts: number[] = [];
  private stopping = false;
  private logStream: fs.WriteStream | null = null;

  get current(): Connection | null {
    return this.connection;
  }

  async start(): Promise<Connection> {
    this.stopping = false;
    const port = await freePort();
    const token = randomBytes(32).toString("hex");
    const { command, args, cwd } = serverCommand(port, token);

    const logDir = app.getPath("logs");
    fs.mkdirSync(logDir, { recursive: true });
    this.logStream ??= fs.createWriteStream(path.join(logDir, "sidecar.log"), { flags: "a" });

    const env: NodeJS.ProcessEnv = { ...process.env, PYTHONUNBUFFERED: "1" };
    delete env.ELECTRON_RUN_AS_NODE;
    const child = spawn(command, args, { cwd, env, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
    this.child = child;

    const ready = new Promise<Connection>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("NexRemote host did not start within 60 s")), 60_000);
      let buffer = "";
      child.stdout?.on("data", (chunk: Buffer) => {
        const text = chunk.toString("utf8");
        this.logStream?.write(text);
        buffer += text;
        if (buffer.includes(READY_PREFIX)) {
          clearTimeout(timer);
          buffer = "";
          resolve({ baseUrl: `http://127.0.0.1:${port}`, token });
        }
      });
      child.stderr?.on("data", (chunk: Buffer) => this.logStream?.write(chunk));
      child.once("error", (err) => {
        clearTimeout(timer);
        reject(err);
      });
      child.once("exit", (code) => {
        clearTimeout(timer);
        reject(new Error(`NexRemote host exited during startup (code ${code})`));
      });
    });

    child.once("exit", (code, signal) => this.onExit(child, code, signal));

    this.connection = await ready;
    this.emit("ready", this.connection);
    return this.connection;
  }

  private onExit(child: ChildProcess, code: number | null, signal: NodeJS.Signals | null): void {
    if (child !== this.child) return;
    this.child = null;
    this.connection = null;
    this.logStream?.write(`\n[sidecar exited code=${code} signal=${signal}]\n`);
    if (this.stopping) return;

    const now = Date.now();
    this.restarts = this.restarts.filter((t) => now - t < 60_000);
    if (this.restarts.length >= MAX_RESTARTS_PER_MINUTE) {
      this.emit("failed", new Error("NexRemote host keeps crashing; see sidecar.log"));
      return;
    }
    this.restarts.push(now);
    this.emit("restarting");
    const delay = 500 * 2 ** (this.restarts.length - 1);
    setTimeout(() => {
      this.start().catch((err) => this.emit("failed", err));
    }, delay);
  }

  async stop(): Promise<void> {
    this.stopping = true;
    const child = this.child;
    const connection = this.connection;
    if (!child) return;
    const exited = new Promise<void>((resolve) => child.once("exit", () => resolve()));
    if (connection) {
      try {
        await fetch(`${connection.baseUrl}/shutdown`, {
          method: "POST",
          headers: { Authorization: `Bearer ${connection.token}` },
          signal: AbortSignal.timeout(2000),
        });
      } catch {
        // fall through to kill
      }
    }
    const timeout = new Promise<"timeout">((resolve) => setTimeout(() => resolve("timeout"), 6000));
    if ((await Promise.race([exited, timeout])) === "timeout") child.kill();
  }
}
