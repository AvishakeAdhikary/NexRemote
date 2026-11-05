"use client";

// Custom title strip for the frameless window. The native caption buttons (minimize, maximize, close,
// snap layouts) are drawn by Windows on the right through Electron's titleBarOverlay, so this strip
// spans the full width underneath them (so the bottom border is continuous) and provides the drag region.
export function TitleBar() {
  return (
    <header
      className="app-drag fixed inset-x-0 top-0 z-50 flex h-[var(--titlebar-h)] items-center gap-2 border-b border-border bg-surface pl-3 text-[12px] text-muted"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo.svg" alt="" className="h-[18px] w-[18px]" draggable={false} />
      <span className="font-medium text-text">NexRemote</span>
    </header>
  );
}
