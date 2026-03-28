import { useEffect, useMemo, useRef, useState } from "react";
import type { Prospect } from "../types";
import { ChevronDown } from "lucide-react";

export function LeadImportCombobox({
  prospects,
  value,
  onSelectName,
  disabled,
}: {
  prospects: Prospect[];
  value: string;
  onSelectName: (name: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return prospects
      .filter((p) => {
        if (!q) return true;
        return (
          p.name.toLowerCase().includes(q) || (p.category || "").toLowerCase().includes(q)
        );
      })
      .slice(0, 100);
  }, [prospects, query]);

  return (
    <div className="lead-import-combobox" ref={wrapRef}>
      <div
        className={`lead-import-combobox-trigger ${open ? "is-open" : ""}`}
        onClick={() => !disabled && setOpen((o) => !o)}
      >
        <input
          type="text"
          className="lead-import-combobox-input"
          autoComplete="off"
          placeholder="Buscar lead para importar…"
          value={open ? query : value}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            setQuery(value);
            setOpen(true);
          }}
          disabled={disabled}
        />
        <ChevronDown size={18} className="lead-import-combobox-chevron" aria-hidden />
      </div>
      {open && (
        <ul className="lead-import-combobox-list" role="listbox">
          {filtered.length === 0 ? (
            <li className="lead-import-combobox-empty">Sin coincidencias</li>
          ) : (
            filtered.map((p) => (
              <li
                key={p.id != null ? `p-${p.id}` : `${p.name}\0${p.address || ""}`}
                role="option"
                className="lead-import-combobox-option"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onSelectName(p.name);
                  setQuery("");
                  setOpen(false);
                }}
              >
                <span className="lead-import-combobox-name">{p.name}</span>
                {p.category ? (
                  <span className="lead-import-combobox-cat">{p.category}</span>
                ) : null}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
