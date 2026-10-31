import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { cancelRequest, getHistory, getRequest, retryRequest } from '../api/endpoints';
import ProgressBar from '../components/ProgressBar';
import StatusBadge from '../components/StatusBadge';
import { CATEGORIES, PRIORITIES, STATUS_LABELS, labelOf } from '../constants';
import { useAuth } from '../context/AuthContext';
import { useRequests } from '../context/RequestsContext';
import { useToast } from '../context/ToastContext';
import { formatDateTime } from '../utils/format';

// These mirror the backend rules. The backend enforces them; we only use them
// to decide which buttons to show.
function canCancel(req, user) {
  if (user.role === 'SUPERVISOR') {
    return req.assigned_supervisor === user.username && ['PENDING', 'PROCESSING'].includes(req.status);
  }
  return req.created_by === user.username && req.status === 'PENDING';
}
const canRetry = (req, user) =>
  user.role === 'SUPERVISOR' && req.assigned_supervisor === user.username && req.status === 'FAILED';

export default function RequestDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { byId, dispatch } = useRequests();
  const toast = useToast();
  const [history, setHistory] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [busy, setBusy] = useState(false);

  const request = byId[id]; // kept fresh by WebSocket events

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    getRequest(id)
      .then((r) => !cancelled && dispatch({ type: 'upsert_many', requests: [r] }))
      .catch((err) => !cancelled && setLoadError(err));
    return () => { cancelled = true; };
  }, [id, dispatch]);

  // Reload the timeline whenever the status changes (including live changes).
  useEffect(() => {
    getHistory(id).then(setHistory).catch(() => {});
  }, [id, request?.status]);

  async function act(fn, successMessage) {
    setBusy(true);
    try {
      const updated = await fn(id);
      dispatch({ type: 'upsert_many', requests: [updated] });
      toast.push(successMessage, 'success');
    } catch (err) {
      toast.push(err.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  const onCancel = () => {
    if (window.confirm('Cancel this request?')) act(cancelRequest, 'Request cancelled.');
  };

  if (loadError && !request) {
    return (
      <div className="empty">
        <p>{loadError.status === 404 ? 'Request not found, or you do not have access to it.' : loadError.message}</p>
        <Link to="/" className="btn">Back to dashboard</Link>
      </div>
    );
  }
  if (!request) return <p className="muted">Loading…</p>;

  return (
    <>
      <Link to="/" className="back">← All requests</Link>
      <div className="page-head">
        <div>
          <h1>#{request.id} {request.title}</h1>
          <div className="meta">
            <StatusBadge status={request.status} />
            <span className={`prio prio-${request.priority}`}>{labelOf(PRIORITIES, request.priority)}</span>
            <span>{labelOf(CATEGORIES, request.category)}</span>
          </div>
        </div>
        <div className="actions">
          {canCancel(request, user) && <button className="btn btn-danger" disabled={busy} onClick={onCancel}>Cancel request</button>}
          {canRetry(request, user) && (
            <button className="btn btn-primary" disabled={busy} onClick={() => act(retryRequest, 'Request re-queued.')}>
              Retry
            </button>
          )}
        </div>
      </div>

      <section className="card">
        <h2>Progress</h2>
        <ProgressBar value={request.progress} status={request.status} />
        <p className="progress-caption">
          <strong>{request.progress}%</strong>
          {request.stage && <> · {request.stage}</>}
        </p>
        {request.status === 'COMPLETED' && request.result && <div className="alert alert-success">{request.result}</div>}
        {request.status === 'FAILED' && <div className="alert alert-error">{request.error_message || 'Processing failed.'}</div>}
        {request.retry_count > 0 && <p className="muted small">Automatically recovered {request.retry_count} time(s) after a stalled worker.</p>}
      </section>

      <div className="two-col">
        <section className="card">
          <h2>Details</h2>
          <p className="description">{request.description}</p>
          <dl className="facts">
            <dt>Submitted by</dt><dd>{request.created_by}</dd>
            <dt>Supervisor</dt><dd>{request.assigned_supervisor ?? 'Unassigned'}</dd>
            <dt>Created</dt><dd>{formatDateTime(request.created_at)}</dd>
            <dt>Started</dt><dd>{formatDateTime(request.started_at)}</dd>
            <dt>Finished</dt><dd>{formatDateTime(request.completed_at)}</dd>
          </dl>
        </section>

        <section className="card">
          <h2>History</h2>
          <ol className="timeline">
            {history.map((h) => (
              <li key={h.id}>
                <span className="tl-dot" />
                <div>
                  <strong>{h.old_status ? `${STATUS_LABELS[h.old_status]} → ` : ''}{STATUS_LABELS[h.new_status]}</strong>
                  <div className="muted small">
                    {formatDateTime(h.changed_at)} · {h.changed_by ?? 'system'}
                    {h.note && <> · {h.note}</>}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </>
  );
}
