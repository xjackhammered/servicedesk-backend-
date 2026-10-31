import { Link } from 'react-router-dom';
import { CATEGORIES, PRIORITIES, labelOf } from '../constants';
import { timeAgo } from '../utils/format';
import ProgressBar from './ProgressBar';
import StatusBadge from './StatusBadge';

export default function RequestCard({ request, showOwner }) {
  return (
    <Link to={`/requests/${request.id}`} className="card request-card">
      <div className="card-head">
        <span className="req-id">#{request.id}</span>
        <StatusBadge status={request.status} />
      </div>
      <h3 className="card-title">{request.title}</h3>
      <div className="meta">
        <span className={`prio prio-${request.priority}`}>{labelOf(PRIORITIES, request.priority)}</span>
        <span>{labelOf(CATEGORIES, request.category)}</span>
        <span>{showOwner ? `by ${request.created_by}` : `supervisor: ${request.assigned_supervisor ?? 'unassigned'}`}</span>
        <span>{timeAgo(request.created_at)}</span>
      </div>
      {request.status === 'PROCESSING' || request.status === 'COMPLETED' ? (
        <div className="progress-row">
          <ProgressBar value={request.progress} status={request.status} />
          <span className="progress-text">{request.stage || `${request.progress}%`}</span>
        </div>
      ) : request.status === 'FAILED' ? (
        <p className="error-text small">{request.error_message || 'Processing failed.'}</p>
      ) : null}
    </Link>
  );
}
