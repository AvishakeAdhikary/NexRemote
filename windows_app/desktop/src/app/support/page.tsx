"use client";

import { Coffee, ExternalLink, Mail } from "lucide-react";
import { Button, Card, PageHeader } from "@/components/ui";

export default function SupportPage() {
  const open = (url: string) => void window.nexremote?.openExternal(url);
  return (
    <>
      <PageHeader title="Support" description="NexRemote is free, ad-free and has no tracking." />
      <div className="grid gap-5 md:grid-cols-2">
        <Card title="Support the project" description="If NexRemote is useful to you, you can support its development directly.">
          <Button variant="primary" onClick={() => open("https://buymeacoffee.com/avishake69")}>
            <Coffee size={15} /> Buy me a coffee <ExternalLink size={13} />
          </Button>
        </Card>
        <Card title="Get help" description="Questions, bugs or privacy requests.">
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => open("mailto:neural.nex.studios@gmail.com")}>
              <Mail size={15} /> neural.nex.studios@gmail.com
            </Button>
            <Button onClick={() => open("https://avishakeadhikary.github.io/Neural-Nexus-Studios/")}>
              Website <ExternalLink size={13} />
            </Button>
          </div>
        </Card>
      </div>
    </>
  );
}
