import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useRequests } from '../context/RequestsContext';

const LIVE_LABELS = { live: 'Live', connecting: 'Connecting…', reconnecting: 'Reconnecting…', offline: 'Offline' };

export default function Layout() {
  const { user, signOut, isOperator } = useAuth();
  const { live } = useRequests();

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">ServiceDesk</Link>
        <nav className="nav">
          <NavLink to="/" end>Dashboard</NavLink>
          {isOperator && <NavLink to="/requests/new">New request</NavLink>}
        </nav>
        <div className="topbar-right">
          <span className={`live live-${live}`} title="Real-time connection">
            <span className="dot" /> {LIVE_LABELS[live]}
          </span>
          <span className="user">
            {user.username} <span className="role">{user.role.toLowerCase()}</span>
          </span>
          <button className="btn btn-ghost" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
