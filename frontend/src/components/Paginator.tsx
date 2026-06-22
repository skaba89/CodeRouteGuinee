/**
 * Paginator.tsx — Composants de pagination et recherche réutilisables.
 *
 * Exports :
 *   usePagination(initialLimit)  — hook gérant page, offset, limit, search
 *   Paginator                    — contrôles précédent / numéros de page / suivant
 *   SearchInput                  — champ de recherche debounced (300 ms)
 *   PaginationInfo               — "Résultats 1–20 sur 347"
 *   PageSizeSelect               — sélecteur 10 / 20 / 50 / 100 résultats par page
 */
import { useCallback, useEffect, useRef, useState } from 'react';

// ── Types ─────────────────────────────────────────────────────────

export interface PaginationState {
  page: number;           // page courante (1-indexée)
  limit: number;          // nombre de résultats par page
  offset: number;         // calculé : (page-1)*limit
  search: string;         // terme de recherche courant
  setPage: (p: number) => void;
  setLimit: (l: number) => void;
  setSearch: (s: string) => void;
  reset: () => void;      // revenir page 1 + vider recherche
}

// ── Hook central ─────────────────────────────────────────────────

export function usePagination(initialLimit = 20): PaginationState {
  const [page, setPageRaw]     = useState(1);
  const [limit, setLimitRaw]   = useState(initialLimit);
  const [search, setSearchRaw] = useState('');

  const setPage = useCallback((p: number) => setPageRaw(Math.max(1, p)), []);

  const setLimit = useCallback((l: number) => {
    setLimitRaw(l);
    setPageRaw(1); // retour page 1 au changement de taille
  }, []);

  const setSearch = useCallback((s: string) => {
    setSearchRaw(s);
    setPageRaw(1); // retour page 1 à chaque nouvelle recherche
  }, []);

  const reset = useCallback(() => {
    setPageRaw(1);
    setSearchRaw('');
  }, []);

  return {
    page,
    limit,
    offset: (page - 1) * limit,
    search,
    setPage,
    setLimit,
    setSearch,
    reset,
  };
}

// ── Styles partagés ───────────────────────────────────────────────

const BTN: React.CSSProperties = {
  padding: '4px 10px',
  border: '1.5px solid var(--border)',
  borderRadius: 'var(--r)',
  background: 'var(--bg)',
  color: 'var(--ink)',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
  minWidth: 32,
  textAlign: 'center' as const,
  lineHeight: '20px',
};

const BTN_ACTIVE: React.CSSProperties = {
  ...BTN,
  background: 'var(--blue)',
  borderColor: 'var(--blue)',
  color: '#fff',
};

const BTN_DISABLED: React.CSSProperties = {
  ...BTN,
  opacity: 0.35,
  cursor: 'not-allowed',
};

// ── Paginator ─────────────────────────────────────────────────────

interface PaginatorProps {
  page: number;
  limit: number;
  total: number;
  onPage: (p: number) => void;
}

export function Paginator({ page, limit, total, onPage }: PaginatorProps) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  if (totalPages <= 1 && total <= limit) return null;

  // Calculer la fenêtre de pages à afficher (max 7 boutons)
  const pages: (number | '…')[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push('…');
    const start = Math.max(2, page - 1);
    const end   = Math.min(totalPages - 1, page + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (page < totalPages - 2) pages.push('…');
    pages.push(totalPages);
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        justifyContent: 'center',
        padding: '10px 0 4px',
        flexWrap: 'wrap',
      }}
      role="navigation"
      aria-label="Pagination"
    >
      {/* Précédent */}
      <button
        type="button"
        style={page <= 1 ? BTN_DISABLED : BTN}
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        aria-label="Page précédente"
      >
        ‹
      </button>

      {pages.map((p, i) =>
        p === '…' ? (
          <span key={`ellipsis-${i}`} style={{ ...BTN, border: 'none', background: 'transparent', cursor: 'default' }}>
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            style={p === page ? BTN_ACTIVE : BTN}
            onClick={() => onPage(p as number)}
            aria-label={`Page ${p}`}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}

      {/* Suivant */}
      <button
        type="button"
        style={page >= totalPages ? BTN_DISABLED : BTN}
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
        aria-label="Page suivante"
      >
        ›
      </button>
    </div>
  );
}

// ── SearchInput ───────────────────────────────────────────────────

interface SearchInputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  debounceMs?: number;
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Rechercher…',
  debounceMs = 300,
}: SearchInputProps) {
  const [local, setLocal]   = useState(value);
  const timerRef            = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync si value change de l'extérieur (ex: reset)
  useEffect(() => { setLocal(value); }, [value]);

  function handleChange(v: string) {
    setLocal(v);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onChange(v), debounceMs);
  }

  function handleClear() {
    setLocal('');
    if (timerRef.current) clearTimeout(timerRef.current);
    onChange('');
  }

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <span style={{
        position: 'absolute', left: 9, color: 'var(--muted)', fontSize: 14,
        pointerEvents: 'none', lineHeight: 1,
      }}>
        🔍
      </span>
      <input
        type="search"
        value={local}
        onChange={e => handleChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        style={{
          paddingLeft: 30,
          paddingRight: local ? 28 : 10,
          height: 34,
          border: '1.5px solid var(--border)',
          borderRadius: 'var(--r)',
          background: 'var(--bg)',
          color: 'var(--ink)',
          fontSize: 13,
          minWidth: 200,
          outline: 'none',
        }}
      />
      {local && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Effacer la recherche"
          style={{
            position: 'absolute', right: 6,
            background: 'none', border: 'none',
            color: 'var(--muted)', cursor: 'pointer',
            fontSize: 14, lineHeight: 1, padding: 2,
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}

// ── PaginationInfo ────────────────────────────────────────────────

interface PaginationInfoProps {
  page: number;
  limit: number;
  total: number;
  loading?: boolean;
}

export function PaginationInfo({ page, limit, total, loading }: PaginationInfoProps) {
  if (loading) {
    return <span style={{ fontSize: 12, color: 'var(--muted)' }}>Chargement…</span>;
  }
  if (total === 0) {
    return <span style={{ fontSize: 12, color: 'var(--muted)' }}>Aucun résultat</span>;
  }
  const from = (page - 1) * limit + 1;
  const to   = Math.min(page * limit, total);
  return (
    <span style={{ fontSize: 12, color: 'var(--muted)' }}>
      {from}–{to} sur <strong style={{ color: 'var(--ink2)' }}>{total}</strong>
    </span>
  );
}

// ── PageSizeSelect ────────────────────────────────────────────────

const PAGE_SIZES = [10, 20, 50, 100];

interface PageSizeSelectProps {
  value: number;
  onChange: (v: number) => void;
  options?: number[];
}

export function PageSizeSelect({ value, onChange, options = PAGE_SIZES }: PageSizeSelectProps) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--muted)' }}>
      Afficher
      <select
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        aria-label="Résultats par page"
        style={{
          border: '1.5px solid var(--border)',
          borderRadius: 'var(--r)',
          background: 'var(--bg)',
          color: 'var(--ink)',
          fontSize: 12,
          padding: '2px 6px',
          cursor: 'pointer',
        }}
      >
        {options.map(n => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>
      par page
    </label>
  );
}

// ── PaginationBar — barre complète combinée ───────────────────────

interface PaginationBarProps {
  page: number;
  limit: number;
  total: number;
  onPage: (p: number) => void;
  onLimit: (l: number) => void;
  loading?: boolean;
}

export function PaginationBar({ page, limit, total, onPage, onLimit, loading }: PaginationBarProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: 8,
      padding: '8px 0',
      borderTop: '0.5px solid var(--border)',
      marginTop: 4,
    }}>
      <PaginationInfo page={page} limit={limit} total={total} loading={loading} />
      <Paginator page={page} limit={limit} total={total} onPage={onPage} />
      <PageSizeSelect value={limit} onChange={l => { onLimit(l); onPage(1); }} />
    </div>
  );
}
