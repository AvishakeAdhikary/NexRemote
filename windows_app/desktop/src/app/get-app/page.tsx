"use client";

import { ExternalLink, Info } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Button, Card, PageHeader } from "@/components/ui";

const PLAY_URL = "https://play.google.com/store/apps/details?id=com.neuralnexusstudios.nex_remote";
const RELEASE_URL = "https://github.com/AvishakeAdhikary/NexRemote/releases/latest";
const APK_URL = `${RELEASE_URL}/download/NexRemote-android-release.apk`;

function PhoneQr({ value, label }: { value: string; label: string }) {
  return (
    <div className="mt-4 flex items-center gap-4">
      <div className="shrink-0 rounded-xl bg-white p-3">
        <QRCodeSVG value={value} size={132} level="M" marginSize={0} title={label} />
      </div>
      <p className="text-[13px] text-muted">{label}</p>
    </div>
  );
}

export default function GetAppPage() {
  const open = (url: string) => void window.nexremote?.openExternal(url);

  return (
    <>
      <PageHeader
        title="Get the Android app"
        description="NexRemote runs on your PC and your phone. Install the free app on your phone, then pair it from the Dashboard."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="Google Play"
          description="Updates install automatically. NexRemote is in closed testing on Google Play, so this page only opens for invited testers for now."
        >
          <Button variant="primary" onClick={() => open(PLAY_URL)}>
            Open Google Play <ExternalLink size={13} />
          </Button>
          <PhoneQr value={PLAY_URL} label="Scan with your phone's camera to open the listing in Google Play." />
        </Card>

        <Card
          title="Direct download (APK)"
          description="The latest release on GitHub, for anyone. Needs Android 8.0 or later."
        >
          <Button variant="primary" onClick={() => open(RELEASE_URL)}>
            Open latest GitHub release <ExternalLink size={13} />
          </Button>
          <PhoneQr
            value={APK_URL}
            label="Scan with your phone's camera to download the APK, then open it. Android may ask you to allow installs from your browser."
          />
        </Card>
      </div>

      <p className="mt-5 flex items-start gap-2 text-[13px] text-muted">
        <Info size={15} className="mt-0.5 shrink-0" />
        <span>
          Google Play and GitHub builds are signed differently, so Android won&apos;t install one over the other. To
          switch, uninstall NexRemote from your phone first.
        </span>
      </p>
    </>
  );
}
