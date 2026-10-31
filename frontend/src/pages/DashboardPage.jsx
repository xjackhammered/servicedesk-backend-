import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { getStats, listRequests } from '../api/endpoints';
import Filters from '../components/Filters';
import Pagination from '../components/Pagination';
import RequestCard from '../components/RequestCard';
import StatsBar from '../components/StatsBar';
import { useAuth } from '../context/AuthContext';
import { useRequests } from '../context/RequestsContext';

const PAGE_SIZE = 20;
const EMPTY_FILTERS = { search: '', status: '', priority: '', category: '' };

export default function DashboardPage() {
  const { isSupervisor, isOperator } = useAuth();
  const { byId, version, dispatch } = useRequests();

  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [ids, setIds] = useState([]);
  const [count, setCount] = useState(0);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const latest = useRef(0);

  // Fetch whenever filters/page change, or the store says something structural
  // happened (new request, status change, reconnect). The short delay batches
  // bursts of events into one fetch.
  useEffect(() => {
    const seq = ++latest.current;
    const timer = setTimeout(async () => {
      try {
        const [list, summary] = await Promise.all([listRequests({ ...filters, page }), getStats()]);
        if (seq !== latest.current) return; // a newer fetch superseded this one
        dispatch({ type: 'upsert_many', requests: list.results });
        setIds(list.results.map((r) => r.id));
        setCount(list.count);
        setStats(summary);
        setError('');
      } catch (err) {
        if (seq !== latest.current) return;
        if (err.status === 404 && page > 1) setPage(1); // page vanished after a status change
        else setError(err.message);
      } finally {
        if (seq === latest.current) setLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [filters, page, version, dispatch]);

  const changeFilters = (patch) => {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const items = ids.map((id) => byId[id]).filter(Boolean);
  const filtered = Object.values(filters).some(Boolean);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{isSupervisor ? 'Assigned requests' : 'My requests'}</h1>
          <p className="muted">
            {isSupervisor ? 'Requests assigned to you. Updates appear live.' : 'Everything you have submitted. Updates appear live.'}
          </p>
        </div>
        {isOperator && <Link to="/requests/new" className="btn btn-primary">+ New request</Link>}
      </div>

      <StatsBar stats={stats} active={filters.status} onSelect={(status) => changeFilters({ status })} />
      <Filters filters={filters} onChange={changeFilters} />

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {loading && !items.length ? (
        <p className="muted">Loading requests…</p>
      ) : items.length === 0 ? (
        <div className="empty">
          <p>{filtered ? 'No requests match these filters.' : 'No requests yet.'}</p>
          {isOperator && !filtered && <Link to="/requests/new" className="btn btn-primary">Submit your first request</Link>}
        </div>
      ) : (
        <div className="grid">
          {items.map((r) => <RequestCard key={r.id} request={r} showOwner={isSupervisor} />)}
        </div>
      )}
      <Pagination page={page} totalPages={totalPages} onPage={setPage} />
    </>
  );
}
