import katex from "katex";
import { Fragment, type ReactNode } from "react";

// \$ = literal dollar sign, $$..$$ = display math, $..$ = inline math, <u>..</u> = underlined span.
const TOKEN = /\\\$|\$\$([\s\S]+?)\$\$|\$([^$]+?)\$|<u>([\s\S]*?)<\/u>/g;

function tex(src: string, displayMode: boolean) {
  return katex.renderToString(src, { throwOnError: false, displayMode });
}

export function renderMath(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(TOKEN)) {
    const i = m.index ?? 0;
    if (i > last) out.push(text.slice(last, i));
    if (m[0] === "\\$") out.push("$");
    else if (m[1] !== undefined) out.push(<span key={i} className="block py-1" dangerouslySetInnerHTML={{ __html: tex(m[1], true) }} />);
    else if (m[2] !== undefined) out.push(<span key={i} dangerouslySetInnerHTML={{ __html: tex(m[2], false) }} />);
    else out.push(<u key={i} className="decoration-2 underline-offset-4">{renderMath(m[3])}</u>);
    last = i + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function MathText({ text, className }: { text: string; className?: string }) {
  return (
    <span className={className}>
      {renderMath(text).map((n, i) => (
        <Fragment key={i}>{n}</Fragment>
      ))}
    </span>
  );
}
