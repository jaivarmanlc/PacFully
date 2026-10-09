/**
 * AuthContext — single source of truth for the logged-in user.
 *
 * Stores in localStorage:
 *   pac_token  — JWT string
 *   pac_user   — { id, full_name, email, role }
 *
 * Exposes via useAuth():
 *   user, token, isLoggedIn, initials
 *   login(email, password)  → Promise<null|errorString>
 *   logout()
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const AuthContext = createContext(null);

function loadSession() {
  try {
    const token = localStorage.getItem('pac_token');
    const raw   = localStorage.getItem('pac_user');
    if (token && raw) return { token, user: JSON.parse(raw) };
  } catch {}
  return { token: null, user: null };
}

// ── Provider ─────────────────────────────────────────────────
// NOTE: AuthProvider does NOT call useNavigate() here.
// Navigation after login/logout is handled by the callers
// (Login.jsx and Sidebar.jsx) so this provider stays portable.
export function AuthProvider({ children }) {
  const initial = loadSession();
  const [token, setToken] = useState(initial.token);
  const [user,  setUser]  = useState(initial.user);

  const initials = user
    ? user.full_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  /**
   * login(email, password)
   * Returns null on success, or an error string on failure.
   * Does NOT navigate — caller handles that.
   */
  const login = useCallback(async (email, password) => {
    try {
      const form = new URLSearchParams();
      form.append('username', email.trim().toLowerCase());
      form.append('password', password);

      const res = await fetch(`${BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return err.detail || 'Incorrect email or password';
      }

      const data = await res.json();
      const userObj = {
        id: data.user_id,
        full_name: data.full_name,
        email: data.email,
        role: data.role,
      };

      localStorage.setItem('pac_token', data.access_token);
      localStorage.setItem('pac_user', JSON.stringify(userObj));
      localStorage.removeItem('pac_testing_session');
      setToken(data.access_token);
      setUser(userObj);
      return null;
    } catch {
      return 'Cannot reach the server. Make sure the backend is running on port 8000.';
    }
  }, []);

  const loginWithGoogle = useCallback(async (credential) => {
    try {
      const res = await fetch(`${BASE}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) return data.detail || 'Google sign-in failed';

      const userObj = {
        id: data.user_id,
        full_name: data.full_name,
        email: data.email,
        role: data.role,
      };
      localStorage.setItem('pac_token', data.access_token);
      localStorage.setItem('pac_user', JSON.stringify(userObj));
      localStorage.removeItem('pac_testing_session');
      setToken(data.access_token);
      setUser(userObj);
      return null;
    } catch {
      return 'Cannot reach the server. Make sure the backend is running on port 8000.';
    }
  }, []);

  /**
   * logout()
   * Clears storage and state. Caller handles navigation.
   */
  const logout = useCallback(() => {
    localStorage.removeItem('pac_token');
    localStorage.removeItem('pac_user');
    localStorage.removeItem('pac_testing_session');
    setToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    token,
    isLoggedIn: !!token && !!user,
    initials,
    login,
    loginWithGoogle,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
