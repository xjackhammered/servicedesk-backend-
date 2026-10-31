import { useEffect, useState } from 'react';
import { CATEGORIES, PRIORITIES, STATUSES, STATUS_LABELS } from '../constants';

export default function Filters({ filters, onChange }) {
  // Keep typing snappy: update the URL/API filter 350ms after the user stops typing.
  const [search, setSearch] = useState(filters.search);
  useEffect(() => {
    const t = setTimeout(() => {
      if (search !== filters.search) onChange({ search });
    }, 350);
    return () => clearTimeout(t);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => setSearch(filters.search), [filters.search]);

  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div className="filters">
      <input
        type="search"
        placeholder="Search title or description…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        aria-label="Search requests"
      />
      <select value={filters.status} onChange={(e) => onChange({ status: e.target.value })} aria-label="Status">
        <option value="">All statuses</option>
        {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
      </select>
      <select value={filters.priority} onChange={(e) => onChange({ priority: e.target.value })} aria-label="Priority">
        <option value="">All priorities</option>
        {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
      </select>
      <select value={filters.category} onChange={(e) => onChange({ category: e.target.value })} aria-label="Category">
        <option value="">All categories</option>
        {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      {hasFilters && (
        <button className="btn btn-ghost" onClick={() => onChange({ search: '', status: '', priority: '', category: '' })}>
          Clear
        </button>
      )}
    </div>
  );
}
