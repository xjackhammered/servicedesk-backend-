/**
 * The real-time store.
 *
 *  - `byId` holds the latest known version of every request we've seen.
 *    REST responses and WebSocket events both write into it, so every page
 *    shows the same data.
 *  - `version` is bumped when something structural happens (a request is
 *    created, a status changes, the socket reconnects). Pages watch it and
 *    re-fetch their list from REST. Progress ticks only update `byId`.
 *  - REST is the source of truth; WebSocket events are fast hints.
 */
import { createContext, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import { WS_URL, getValidAccessToken, refreshAccessToken } from '../api/client';
import { STATUS_LABELS } from '../constants';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

const RequestsContext = createContext(null);

const initialState = { byId: {}, live: 'connecting', version: 0 };

function isNewer(incoming, existing) {
  if (!existing) return true;
  return new Date(incoming.updated_at) >= new Date(existing.updated_at); // ignore stale events
}

function reducer(state, action) {
  switch (action.type) {
    case 'upsert_many': {
      const byId = { ...state.byId };
      action.requests.forEach((r) => {
        if (isNewer(r, byId[r.id])) byId[r.id] = r;
      });
      return { ...state, byId };
    }
    case 'bump':
      return { ...state, version: state.version + 1 };
    case 'live':
      return { ...state, live: action.value };
    case 'reset':
      return initialState;
    default:
      return state;
  }
}

export function RequestsProvider({ children }) {
  const { user } = useAuth();
  const toast = useToast();
  const [state, dispatch] = useReducer(reducer, initialState);
  const userRef = useRef(user);
  userRef.current = user;

  useEffect(() => {
    if (!user) {
      dispatch({ type: 'reset' });
      return undefined;
    }

    let socket = null;
    let stopped = false;
    let attempt = 0;
    let retryTimer = null;
    let pingTimer = null;

    const handleMessage = (msg) => {
      const me = userRef.current;
      switch (msg.type) {
        case 'connection.ready':
          attempt = 0;
          dispatch({ type: 'live', value: 'live' });
          dispatch({ type: 'bump' }); // re-sync from REST after (re)connecting
          break;
        case 'request.created':
          dispatch({ type: 'upsert_many', requests: [msg.request] });
          dispatch({ type: 'bump' });
          if (me?.role === 'SUPERVISOR') toast.push(`New request #${msg.request.id}: ${msg.request.title}`, 'info');
          break;
        case 'request.status_changed':
          dispatch({ type: 'upsert_many', requests: [msg.request] });
          dispatch({ type: 'bump' });
          toast.push(
            `#${msg.request.id} ${msg.request.title}: ${STATUS_LABELS[msg.request.status]}`,
            msg.request.status === 'FAILED' ? 'error' : msg.request.status === 'COMPLETED' ? 'success' : 'info',
          );
          break;
        case 'request.progress':
          dispatch({ type: 'upsert_many', requests: [msg.request] }); // no refetch needed
          break;
        default:
          break; // pong etc.
      }
    };

    const scheduleReconnect = () => {
      if (stopped) return;
      dispatch({ type: 'live', value: 'reconnecting' });
      const delay = Math.min(15000, 1000 * 2 ** attempt);
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    };

    async function connect() {
      const token = await getValidAccessToken();
      if (stopped) return;
      if (!token) {
        dispatch({ type: 'live', value: 'offline' });
        return;
      }
      socket = new WebSocket(`${WS_URL}/ws/requests/?token=${encodeURIComponent(token)}`);
      socket.onmessage = (e) => {
        try { handleMessage(JSON.parse(e.data)); } catch { /* ignore malformed frames */ }
      };
      socket.onclose = async (e) => {
        clearInterval(pingTimer);
        if (stopped) return;
        if (e.code === 4401) {
          try { await refreshAccessToken(); } catch { dispatch({ type: 'live', value: 'offline' }); return; }
        }
        scheduleReconnect();
      };
      socket.onopen = () => {
        pingTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'ping' }));
        }, 25000);
      };
    }

    dispatch({ type: 'live', value: 'connecting' });
    connect();

    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      clearInterval(pingTimer);
      socket?.close();
    };
  }, [user, toast]);

  const value = useMemo(() => ({ ...state, dispatch }), [state]);
  return <RequestsContext.Provider value={value}>{children}</RequestsContext.Provider>;
}

export const useRequests = () => useContext(RequestsContext);
