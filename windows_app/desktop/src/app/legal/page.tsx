"use client";

import { useEffect, useState } from "react";
import { Markdown } from "@/components/Markdown";
import { Card, cx, PageHeader } from "@/components/ui";
import { LEGAL_DOCUMENTS, loadLegal } from "@/lib/legal";

export default function LegalPage() {
  const [active, setActive] = useState(LEGAL_DOCUMENTS[0]);
  const [text, setText] = useState("");

  useEffect(() => {
    void loadLegal(active.file).then(setText).catch(() => setText("Could not load this document."));
  }, [active]);

  return (
    <>
      <PageHeader title="Legal" description="The documents you accepted. They are bundled with the app and work offline." />
      <div className="mb-4 flex gap-2">
        {LEGAL_DOCUMENTS.map((doc) => (
          <button
            key={doc.id}
            onClick={() => setActive(doc)}
            className={cx(
              "rounded-lg px-3 py-1.5 text-[13px] font-medium",
              doc.id === active.id ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2",
            )}
          >
            {doc.title}
          </button>
        ))}
      </div>
      <Card>
        <Markdown source={text} />
      </Card>
    </>
  );
}
