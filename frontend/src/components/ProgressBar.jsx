export default function ProgressBar({ value, status }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      className={`progress progress-${status}`}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="progress-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}
