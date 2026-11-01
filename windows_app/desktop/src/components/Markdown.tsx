"use client";

import { Fragment, type ReactNode } from "react";

// Minimal Markdown for the bundled legal documents: headings, paragraphs, bullet lists,
// **bold**, and bare https:// / mailto links. Anything else renders as text.

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|https:\/\/[^\s)]+|[\w.+-]+@[\w-]+\.[\w.]+)/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(text.slice(last, index));
    const token = match[0];
    if (token.startsWith("**")) parts.push(<strong key={index}>{token.slice(2, -2)}</strong>);
    else if (token.includes("@") && !token.startsWith("http"))
      parts.push(<a key={index} href={`mailto:${token}`}>{token}</a>);
    else parts.push(<a key={index} href={token} target="_blank" rel="noreferrer">{token}</a>);
    last = index + token.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export function Markdown({ source }: { source: string }) {
  const blocks: ReactNode[] = [];
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];

  const flush = () => {
    if (paragraph.length) {
      blocks.push(<p key={blocks.length}>{inline(paragraph.join(" "))}</p>);
      paragraph = [];
    }
    if (list.length) {
      blocks.push(
        <ul key={blocks.length}>
          {list.map((item, i) => <li key={i}>{inline(item)}</li>)}
        </ul>,
      );
      list = [];
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      flush();
      const level = heading[1].length;
      const content = inline(heading[2]);
      blocks.push(
        level === 1 ? <h1 key={blocks.length}>{content}</h1> : level === 2 ? <h2 key={blocks.length}>{content}</h2> : <h3 key={blocks.length}>{content}</h3>,
      );
    } else if (/^\s*[-*]\s+/.test(line)) {
      if (paragraph.length) flush();
      list.push(line.replace(/^\s*[-*]\s+/, ""));
    } else if (line.trim() === "") {
      flush();
    } else {
      if (list.length) flush();
      paragraph.push(line.trim());
    }
  }
  flush();
  return <div className="prose-legal">{blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>)}</div>;
}
