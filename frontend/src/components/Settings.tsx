import { useEffect, useId, useRef, useState } from "react";

export const APP_VERSION = "1.0";
const SAT_SITE = "https://satsuite.collegeboard.org/sat";

// 3×3 dots, the usual "apps/menu" icon.
function GridIcon() {
  const dots = [5, 12, 19].flatMap((cy) => [5, 12, 19].map((cx) => <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="2" />));
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      {dots}
    </svg>
  );
}

export function Settings({ dark, onDark, onSignOut }: { dark: boolean; onDark: (on: boolean) => void; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const panelId = useId();
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => !root.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  const row = "flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm hover:bg-slate-100";
  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-label="Settings"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100 hover:text-brand-700"
      >
        <GridIcon />
      </button>
      {open && (
        <div id={panelId} className="absolute right-0 z-30 mt-2 w-64 rounded-xl bg-white p-2 shadow-xl ring-1 ring-slate-200">
          <button type="button" role="switch" aria-checked={dark} onClick={() => onDark(!dark)} className={row}>
            Dark theme
            <span className={`relative h-5 w-9 rounded-full transition-colors ${dark ? "bg-brand-700" : "bg-slate-300"}`}>
              <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${dark ? "left-4.5" : "left-0.5"}`} />
            </span>
          </button>
          <a href={SAT_SITE} target="_blank" rel="noopener noreferrer" className={row}>
            <span>
              Official SAT website<span className="sr-only"> (opens in a new tab)</span>
            </span>
            <span aria-hidden="true" className="text-slate-500">↗</span>
          </a>
          <button type="button" onClick={onSignOut} className={`${row} text-red-700`}>
            Sign out
          </button>
          <p className="mt-1 border-t border-slate-200 px-3 pt-2 text-xs text-slate-500">Apex Prep · version {APP_VERSION}</p>
        </div>
      )}
    </div>
  );
}
