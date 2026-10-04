import { useCallback, useEffect, useState, type RefObject } from "react";

// Highlights + notes for exam questions. Painted with the CSS Custom Highlight API (no DOM changes,
// so KaTeX and React keep their nodes) and stored per question in this browser only.
export type Annotation = { start: number; end: number; text: string; note: string };

const HIGHLIGHT = "apex-annotation";
export const annotationsSupported = typeof CSS !== "undefined" && "highlights" in CSS;

function textNodes(root: Node): Text[] {
  const out: Text[] = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) out.push(n as Text);
  return out;
}

// Character offset of (node, offset) within root's text, counting every text node in order.
export function offsetIn(root: Node, node: Node, offset: number): number | null {
  let total = 0;
  for (const t of textNodes(root)) {
    if (t === node) return total + offset;
    total += t.data.length;
  }
  if (node.nodeType !== Node.TEXT_NODE && root.contains(node)) {
    // Selection boundary on an element: count the text before its offset-th child.
    const r = document.createRange();
    r.setStart(root, 0);
    r.setEnd(node, offset);
    return r.toString().length;
  }
  return null;
}

export function rangeFor(root: Node, start: number, end: number): Range | null {
  const r = document.createRange();
  let total = 0;
  let started = false;
  for (const t of textNodes(root)) {
    const len = t.data.length;
    if (!started && start <= total + len) {
      r.setStart(t, start - total);
      started = true;
    }
    if (started && end <= total + len) {
      r.setEnd(t, end - total);
      return r;
    }
    total += len;
  }
  return null;
}

function load(key: string): Annotation[] {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "[]");
  } catch {
    return [];
  }
}

export function useAnnotations(key: string, root: RefObject<HTMLElement | null>) {
  const [anns, setAnns] = useState<Annotation[]>(() => load(key));
  const save = useCallback(
    (next: Annotation[]) => {
      setAnns(next);
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* storage blocked: annotations last for this page view */
      }
    },
    [key],
  );

  // Repaint after every render: React may have replaced the text nodes the ranges point at.
  useEffect(() => {
    if (!annotationsSupported || !root.current) return;
    const ranges = anns.map((a) => rangeFor(root.current!, a.start, a.end)).filter((r): r is Range => r !== null);
    CSS.highlights.set(HIGHLIGHT, new Highlight(...ranges));
  });
  useEffect(() => () => void (annotationsSupported && CSS.highlights.delete(HIGHLIGHT)), []);

  const addFromSelection = (): boolean => {
    const sel = window.getSelection();
    const el = root.current;
    if (!sel || sel.isCollapsed || !el || sel.rangeCount === 0) return false;
    const r = sel.getRangeAt(0);
    if (!el.contains(r.commonAncestorContainer)) return false;
    const start = offsetIn(el, r.startContainer, r.startOffset);
    const end = offsetIn(el, r.endContainer, r.endOffset);
    const text = r.toString().trim();
    if (start === null || end === null || end <= start || !text) return false;
    save([...anns.filter((a) => a.end <= start || a.start >= end), { start, end, text, note: "" }].sort((a, b) => a.start - b.start));
    sel.removeAllRanges();
    return true;
  };
  return {
    anns,
    addFromSelection,
    setNote: (i: number, note: string) => save(anns.map((a, j) => (j === i ? { ...a, note } : a))),
    remove: (i: number) => save(anns.filter((_, j) => j !== i)),
  };
}

export function AnnotationList({ anns, setNote, remove }: Pick<ReturnType<typeof useAnnotations>, "anns" | "setNote" | "remove">) {
  if (!anns.length) return null;
  return (
    <section aria-label="Your annotations" className="space-y-2 rounded-lg bg-amber-50 p-3 text-sm ring-1 ring-amber-200">
      <p className="font-medium">Your annotations</p>
      <ul className="space-y-2">
        {anns.map((a, i) => (
          <li key={`${a.start}-${a.end}`} className="space-y-1">
            <p className="flex items-start justify-between gap-2">
              <span className="italic text-slate-700">“{a.text.length > 80 ? a.text.slice(0, 80) + "…" : a.text}”</span>
              <button type="button" onClick={() => remove(i)} className="shrink-0 text-xs text-slate-600 underline">Remove</button>
            </p>
            <input
              aria-label={`Note for “${a.text.slice(0, 30)}”`}
              value={a.note}
              onChange={(e) => setNote(i, e.target.value)}
              placeholder="Add a note"
              maxLength={300}
              className="w-full rounded border border-amber-200 bg-white px-2 py-1"
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
