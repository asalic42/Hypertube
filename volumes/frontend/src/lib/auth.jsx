import { useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext } from '@/lib/authContext';
import { auth as authApi, refreshAccessToken, setAccessToken } from '@/lib/api';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // On load, the refresh cookie is the only session we have.
    let cancelled = false;
    (async () => {
      try {
        if (await refreshAccessToken()) {
          const me = await authApi.me();
          if (!cancelled) setUser(me);
        }
      } catch {
        setAccessToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const me = await authApi.login(email, password);
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  // After the account itself changed (email) or is gone (deleted).
  const updateUser = useCallback((me) => setUser(me), []);
  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout, updateUser, clearSession }),
    [user, loading, login, logout, updateUser, clearSession],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
