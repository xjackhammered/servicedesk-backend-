import { STATUSES, STATUS_LABELS } from '../constants';

export default function StatsBar({ stats, active, onSelect }) {
  return (
    <div className="stats">
      <button className={`stat ${!active ? 'stat-active' : ''}`} onClick={() => onSelect('')}>
        <span className="stat-num">{stats?.total ?? '–'}</span>
        <span className="stat-label">All</span>
      </button>
      {STATUSES.map((s) => (
        <button
          key={s}
          className={`stat stat-${s} ${active === s ? 'stat-active' : ''}`}
          onClick={() => onSelect(active === s ? '' : s)}
        >
          <span className="stat-num">{stats?.[s] ?? '–'}</span>
          <span className="stat-label">{STATUS_LABELS[s]}</span>
        </button>
      ))}
    </div>
  );
}
