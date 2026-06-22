/**
 * Composants de pagination et de recherche — CodeRoute Guinée
 *
 * Conçus pour fonctionner avec les réponses paginées du backend :
 *   { items: T[], total: number, limit: number, offset: number, search?: string }
 */
import { useEffect, useRef } from 'react';

// ── Types partagés ────────────────────────────────────────────────

export interface PagedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  search?: string | null;
}

// ── SearchBar ─────────────────────────────────────────────────────

interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  onReset?: () => void;
  placeholder?: string;
  debounceMs?: number;
  'aria-label'?: string;
}

export function SearchBar({
  value,
  onChange,
  onReset,
  placeholder = 'Rechercher…',
  debounceMs = 300,
  'aria-label': ariaLabel = 'Rechercher',
}: SearchBarProps) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      onChange(v);
      onReset?.();
    }, debounceMs);
  }

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <span style={{
        position: 'absolute', left: 10,
        color: 'var(--color-text-tertiary)', fontSize: 14, pointerEvents: 'none',
      }}>🔍</span>
      <input
        type="search"
        defaultValue={value}
        onChange={handleChange}
        placeholder={placeholder}
        aria-label={ariaLabel}
        style={{
          paddingLeft: 32,
          paddingRight: 12,
          height: 34,
          fontSize: 13,
          border: '1.5px solid var(--color-border-secondary)',
          borderRadius: 'var(--border-radius-md)',
          background: 'var(--color-background-primary)',
          color: 'var(--color-text-primary)',
          outline: 'none',
          minWidth: 200,
        }}
      />
    </div>
  );
}

// ── Pagination ────────────────────────────────────────────────────

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPage: (offset: number) => void;
  loading?: boolean;
}

export function Pagination({ total, limit, offset, onPage, loading = false }: PaginationProps) {
  if (total <= limit) return null;

  const currentPage = Math.floor(offset / limit);
  const totalPages  = Math.ceil(total / limit);
  const hasPrev     = currentPage > 0;
  const hasNext     = currentPage < totalPages - 1;
  const start       = offset + 1;
  const end         = Math.min(offset + limit, total);

  const pages: (number | '…')[] = [];
  if (totalPages <= 7) {
    for (let i = 0; i < totalPages; i++) pages.push(i);
  } else {
    pages.push(0);
    if (currentPage > 2) pages.push('…');
    for (let i = Math.max(1, currentPage - 1); i <= Math.min(totalPages - 2, currentPage + 1); i++) pages.push(i);
    if (currentPage < totalPages - 3) pages.push('…');
    pages.push(totalPages - 1);
  }

  const base: React.CSSProperties = {
    minWidth: 32, height: 32,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    border: '1px solid var(--color-border-tertiary)',
    borderRadius: 'var(--border-radius-sm)',
    background: 'var(--color-background-primary)',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer', fontSize: 13, padding: '0 8px',
  };
  const active: React.CSSProperties = {
    ...base,
    background: 'var(--color-background-info)',
    color: 'var(--color-text-info)',
    borderColor: 'var(--color-border-info)',
    fontWeight: 600,
  };
  const disabled: React.CSSProperties = { ...base, opacity: 0.35, cursor: 'not-allowed' };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 8, padding: '10px 0',
      borderTop: '1px solid var(--color-border-tertiary)', marginTop: 4,
    }} aria-label="Pagination">
      <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
        {loading ? 'Chargement…' : `${start}–${end} sur ${total.toLocaleString('fr-FR')} résultat${total > 1 ? 's' : ''}`}
      </span>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <button type="button" style={hasPrev ? base : disabled} disabled={!hasPrev || loading}
          onClick={() => onPage(Math.max(0, offset - limit))} aria-label="Page précédente">‹</button>
        {pages.map((p, i) =>
          p === '…'
            ? <span key={`ell-${i}`} style={{ ...base, cursor: 'default', border: 'none' }}>…</span>
            : <button key={p} type="button"
                style={p === currentPage ? active : base}
                onClick={() => onPage((p as number) * limit)}
                disabled={loading}
                aria-label={`Page ${(p as number) + 1}`}
                aria-current={p === currentPage ? 'page' : undefined}>
                {(p as number) + 1}
              </button>
        )}
        <button type="button" style={hasNext ? base : disabled} disabled={!hasNext || loading}
          onClick={() => onPage(offset + limit)} aria-label="Page suivante">›</button>
      </div>
    </div>
  );
}

// ── PageSizeSelector ──────────────────────────────────────────────

interface PageSizeSelectorProps {
  value: number;
  onChange: (size: number) => void;
  options?: number[];
}

export function PageSizeSelector({ value, onChange, options = [10, 20, 50, 100] }: PageSizeSelectorProps) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-text-secondary)' }}>
      Afficher
      <select value={value} onChange={e => onChange(Number(e.target.value))}
        aria-label="Éléments par page"
        style={{ height: 28, fontSize: 12, border: '1px solid var(--color-border-tertiary)',
          borderRadius: 'var(--border-radius-sm)', background: 'var(--color-background-primary)',
          color: 'var(--color-text-primary)', padding: '0 4px' }}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      par page
    </label>
  );
}

// ── PaginationBar ─────────────────────────────────────────────────

interface PaginationBarProps {
  total: number;
  limit: number;
  offset: number;
  search: string;
  onPage: (offset: number) => void;
  onSearch: (s: string) => void;
  onLimit?: (limit: number) => void;
  loading?: boolean;
  searchPlaceholder?: string;
  limitOptions?: number[];
}

export function PaginationBar({
  total, limit, offset, search,
  onPage, onSearch, onLimit,
  loading = false,
  searchPlaceholder = 'Rechercher…',
  limitOptions,
}: PaginationBarProps) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
        <SearchBar value={search} onChange={onSearch} onReset={() => onPage(0)}
          placeholder={searchPlaceholder} />
        {onLimit && (
          <PageSizeSelector value={limit} onChange={s => { onLimit(s); onPage(0); }} options={limitOptions} />
        )}
      </div>
      <Pagination total={total} limit={limit} offset={offset} onPage={onPage} loading={loading} />
    </div>
  );
}
