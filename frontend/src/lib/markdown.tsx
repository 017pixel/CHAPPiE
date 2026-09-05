import type { ReactNode } from "react";

type MarkdownTextProps = {
  content: string;
  className?: string;
};

const INLINE_TOKEN_RE = /(\[[^\]\n]+\]\(https?:\/\/[^)\s]+\)|`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|_[^_\n]+_)/g;

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(INLINE_TOKEN_RE)) {
    const token = match[0];
    const index = match.index ?? 0;
    if (index > lastIndex) nodes.push(text.slice(lastIndex, index));

    if (token.startsWith("[") && token.includes("](")) {
      const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
      if (linkMatch) {
        nodes.push(
          <a
            key={`link-${index}`}
            href={linkMatch[2]}
            target="_blank"
            rel="noreferrer"
            className="text-terminal-green underline underline-offset-2"
          >
            {renderInline(linkMatch[1])}
          </a>,
        );
      } else {
        nodes.push(token);
      }
    } else if (token.startsWith("`") && token.endsWith("`")) {
      nodes.push(
        <code key={`code-${index}`} className="rounded bg-black/20 px-1 text-terminal-amber">
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(<strong key={`strong-${index}`}>{renderInline(token.slice(2, -2))}</strong>);
    } else if (token.startsWith("*") || token.startsWith("_")) {
      nodes.push(<em key={`em-${index}`}>{renderInline(token.slice(1, -1))}</em>);
    } else {
      nodes.push(token);
    }
    lastIndex = index + token.length;
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes.length > 0 ? nodes : [text];
}

function isBlockStart(line: string): boolean {
  return /^(#{1,6})\s+/.test(line)
    || /^\s*[-*+]\s+/.test(line)
    || /^\s*\d+[.)]\s+/.test(line)
    || /^\s*```/.test(line)
    || /^\s*(?:---+|___+|\*\s*\*\s*\*+)\s*$/.test(line);
}

function renderBlocks(content: string): ReactNode[] {
  const lines = String(content || "").replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;
  let blockKey = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^\s*```\s*([\w+-]*)\s*$/);
    if (fence) {
      const language = fence[1];
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push(
        <pre key={`block-${blockKey++}`} className="my-2 overflow-x-auto rounded border border-white/10 bg-black/25 p-2 text-[11px] leading-relaxed text-slate/80">
          {language && <span className="mb-1 block text-[9px] uppercase tracking-widest text-slate/35">{language}</span>}
          <code>{codeLines.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+?)\s*#*$/);
    if (heading) {
      const level = heading[1].length;
      const Heading = (`h${level}`) as keyof JSX.IntrinsicElements;
      blocks.push(
        <Heading key={`block-${blockKey++}`} className="mb-1 mt-3 font-semibold text-mist first:mt-0">
          {renderInline(heading[2])}
        </Heading>,
      );
      index += 1;
      continue;
    }

    if (/^\s*(?:---+|___+|\*\s*\*\s*\*+)\s*$/.test(line)) {
      blocks.push(<hr key={`block-${blockKey++}`} className="my-2 border-white/10" />);
      index += 1;
      continue;
    }

    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      const items: string[] = [];
      const orderedList = Boolean(ordered);
      while (index < lines.length) {
        const item = lines[index].match(orderedList ? /^\s*\d+[.)]\s+(.+)$/ : /^\s*[-*+]\s+(.+)$/);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      const List = orderedList ? "ol" : "ul";
      blocks.push(
        <List key={`block-${blockKey++}`} className={`${orderedList ? "list-decimal" : "list-disc"} my-2 space-y-1 pl-5`}>
          {items.map((item, itemIndex) => <li key={`${blockKey}-${itemIndex}`}>{renderInline(item)}</li>)}
        </List>,
      );
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    if (paragraph.length === 0) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(
      <p key={`block-${blockKey++}`} className="my-2 whitespace-pre-wrap leading-relaxed first:mt-0 last:mb-0">
        {renderInline(paragraph.join("\n"))}
      </p>,
    );
  }

  return blocks;
}

export function MarkdownText({ content, className = "" }: MarkdownTextProps) {
  return <div className={`chappie-markdown ${className}`}>{renderBlocks(content)}</div>;
}
