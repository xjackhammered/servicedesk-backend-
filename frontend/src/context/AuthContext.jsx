import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchMe, login } from '../api/endpoints';
import { setAuthLostHandler, tokenStore } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while we check a saved session

  useEffect(() => {
    setAuthLostHandler(() => setUser(null)); // api client calls this when refresh fails

    if (!tokenStore.access && !tokenStore.refresh) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const signIn = useCallback(async (username, password) => {
    tokenStore.set(await login(username, password));
    const me = await fetchMe();
    setUser(me);
    return me;
  }, []);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      signIn,
      signOut,
      isSupervisor: user?.role === 'SUPERVISOR',
      isOperator: user?.role === 'OPERATOR',
    }),
    [user, loading, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
