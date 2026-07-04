export type EmotionalTextPart = {
  text: string;
  tone: "normal" | "ember" | "pine" | "muted";
};

export function parseEmotionalText(text: string): EmotionalTextPart[] {
  const parts: EmotionalTextPart[] = [];
  const pattern = /(\*[^*\n]+\*|"""|\.{3,})/g;
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push({ text: text.slice(lastIndex, index), tone: "normal" });
    }

    const token = match[0];
    if (token.startsWith("*")) {
      parts.push({ text: token, tone: "ember" });
    } else if (token === '"""') {
      parts.push({ text: token, tone: "pine" });
    } else {
      parts.push({ text: token, tone: "muted" });
    }
    lastIndex = index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push({ text: text.slice(lastIndex), tone: "normal" });
  }

  return parts.length ? parts : [{ text, tone: "normal" }];
}
