"use client";

import { Check, FileText, ShieldCheck, Wifi } from "lucide-react";
import { useState } from "react";
import { useHost } from "@/lib/host";
import { LEGAL_DOCUMENTS, loadLegal, type LegalDocument } from "@/lib/legal";
import { Markdown } from "./Markdown";
import { Button, cx } from "./ui";

function Frame({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-6">
      <div className="w-full max-w-xl rounded-2xl border border-border bg-surface p-8 shadow-sm">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">{icon}</div>
          <h1 className="text-xl font-semibold">{title}</h1>
        </div>
        {children}
      </div>
    </div>
  );
}

export function LegalGate() {
  const { api, refresh } = useHost();
  const [opened, setOpened] = useState<Set<LegalDocument["id"]>>(new Set());
  const [reading, setReading] = useState<{ doc: LegalDocument; text: string } | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const allOpened = LEGAL_DOCUMENTS.every((d) => opened.has(d.id));

  const open = async (doc: LegalDocument) => {
    setReading({ doc, text: await loadLegal(doc.file) });
    setOpened((prev) => new Set(prev).add(doc.id));
  };

  if (reading) {
    return (
      <div className="flex h-screen flex-col bg-bg">
        <div className="flex items-center justify-between border-b border-border bg-surface px-6 py-3">
          <span className="font-semibold">{reading.doc.title}</span>
          <Button variant="primary" onClick={() => setReading(null)}>Done reading</Button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-3xl"><Markdown source={reading.text} /></div>
        </div>
      </div>
    );
  }

  return (
    <Frame icon={<FileText size={20} />} title="Before you start">
      <p className="text-muted">
        NexRemote lets your own phone control this PC over your local network. Please read each document below,
        then confirm you agree. Nothing is sent to Neural Nexus Studios: there are no accounts, ads or analytics.
      </p>
      <div className="mt-5 space-y-2">
        {LEGAL_DOCUMENTS.map((doc) => (
          <button
            key={doc.id}
            onClick={() => void open(doc)}
            className="flex w-full items-center justify-between rounded-lg border border-border px-4 py-3 text-left hover:bg-surface-2"
          >
            <span className="font-medium">{doc.title}</span>
            {opened.has(doc.id) ? (
              <span className="flex items-center gap-1 text-xs text-ok"><Check size={14} /> Read</span>
            ) : (
              <span className="text-xs text-accent">Open</span>
            )}
          </button>
        ))}
      </div>
      <label className={cx("mt-5 flex items-start gap-3", !allOpened && "opacity-50")}>
        <input
          type="checkbox"
          className="mt-0.5 h-4 w-4 accent-[var(--accent)]"
          disabled={!allOpened}
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
        />
        <span>I have read and agree to the Terms of Service, the Terms and Conditions and the Privacy Policy.</span>
      </label>
      {!allOpened && <p className="mt-2 text-xs text-muted">Open each document to enable this checkbox.</p>}
      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={() => void window.nexremote?.quit()}>Quit</Button>
        <Button
          variant="primary"
          disabled={!agreed || busy}
          onClick={async () => {
            setBusy(true);
            await api("POST", "/legal/accept").catch(() => undefined);
            await refresh();
            setBusy(false);
          }}
        >
          Accept and continue
        </Button>
      </div>
    </Frame>
  );
}

export function ConsentGate() {
  const { api, refresh } = useHost();
  const [busy, setBusy] = useState(false);
  return (
    <Frame icon={<Wifi size={20} />} title="Allow remote networking">
      <p className="text-muted">To let your phone connect, NexRemote will:</p>
      <ul className="mt-3 space-y-2">
        {[
          "Listen on your local network (ports 8765, 8766 and 37020) so paired phones can find and reach this PC.",
          "Let approved phones move the mouse, type, control media, browse files, manage processes and view this screen.",
          "Show phones that share their screen with this PC, and let you control them when the phone allows it.",
        ].map((item) => (
          <li key={item} className="flex gap-2.5">
            <ShieldCheck size={16} className="mt-0.5 shrink-0 text-accent" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[13px] text-muted">
        New phones need your approval on this PC before they can connect. You can turn remote access off at any time in
        Settings.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={() => void window.nexremote?.quit()}>Not now</Button>
        <Button
          variant="primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            await api("POST", "/consent", { remote_control: true }).catch(() => undefined);
            await refresh();
            setBusy(false);
          }}
        >
          Allow
        </Button>
      </div>
    </Frame>
  );
}
