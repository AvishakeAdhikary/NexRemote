import type { Metadata } from "next";
import { Shell } from "@/components/Shell";
import { HostProvider } from "@/lib/host";
import "./globals.css";

export const metadata: Metadata = {
  title: "NexRemote",
  description: "NexRemote Windows host",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <HostProvider>
          <Shell>{children}</Shell>
        </HostProvider>
      </body>
    </html>
  );
}
