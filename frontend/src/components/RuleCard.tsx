import type { ReactNode } from "react";
import { renderMath } from "./MathText";

// Rule cards use a small Markdown subset: "# " title, paragraphs, "- " and "1. " lists, **bold**, *italic*.
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/).map((part, i) =>
    part.startsWith("**") ? <strong key={i}>{renderMath(part.slice(2, -2))}</strong> : part.startsWith("*") && part.length > 2 ? <em key={i}>{renderMath(part.slice(1, -1))}</em> : <span key={i}>{renderMath(part)}</span>,
  );
}

export function RuleCard({ markdown }: { markdown: string }) {
  const out: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (!list) return;
    const Tag = list.ordered ? "ol" : "ul";
    out.push(<Tag key={out.length} className={`${list.ordered ? "list-decimal" : "list-disc"} space-y-1 pl-6`}>{list.items.map((t, i) => <li key={i}>{inline(t)}</li>)}</Tag>);
    list = null;
  };
  for (const line of markdown.split("\n")) {
    const t = line.trim();
    const m = /^(-|\d+\.)\s+(.*)$/.exec(t);
    if (m) {
      const ordered = m[1] !== "-";
      if (list && list.ordered !== ordered) flush();
      list ??= { ordered, items: [] };
      list.items.push(m[2]);
      continue;
    }
    flush();
    if (!t) continue;
    if (t.startsWith("# ")) out.push(<h2 key={out.length} className="text-xl font-bold">{inline(t.slice(2))}</h2>);
    else out.push(<p key={out.length}>{inline(t)}</p>);
  }
  flush();
  return <div className="space-y-2 leading-relaxed text-slate-800">{out}</div>;
}
