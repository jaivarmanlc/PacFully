import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

// Auth
import { AuthProvider, useAuth } from './context/AuthContext.jsx';

// Layout
import Sidebar from './components/Sidebar.jsx';
import Navbar  from './components/Navbar.jsx';

// Public pages
import Home  from './pages/Home.jsx';
import Login from './pages/Login.jsx';

// App pages
import Dashboard     from './pages/Dashboard.jsx';
import CostEstimator from './pages/CostEstimator.jsx';
import Estimates     from './pages/Estimates.jsx';
import Customers     from './pages/Customers.jsx';
import Reports       from './pages/Reports.jsx';
import MasterConfig  from './pages/MasterConfig.jsx';
import Quotations    from './pages/Quotations.jsx';
import Proforma      from './pages/Proforma.jsx';
import Settings      from './pages/Settings.jsx';
import Users         from './pages/Users.jsx';
import AuditLog      from './pages/AuditLog.jsx';

// ── Protected route wrapper ──────────────────────────────────
// Redirects to /login if user is not authenticated.
function RequireAuth({ children }) {
  const { isLoggedIn } = useAuth();
  const location       = useLocation();

  if (!isLoggedIn) {
    // Preserve the URL they tried to visit so we can redirect after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

// ── Public layout (no sidebar) ───────────────────────────────
function PublicLayout({ children }) {
  return <>{children}</>;
}

// ── App layout (sidebar + topbar) — only for authenticated users
function AppLayout({ children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <Navbar />
        {children}
      </div>
    </div>
  );
}

// ── Convenience wrapper: protected + app layout ──────────────
function AppPage({ children }) {
  return (
    <RequireAuth>
      <AppLayout>{children}</AppLayout>
    </RequireAuth>
  );
}

// ── Placeholder pages ─────────────────────────────────────────
function EstimateDetail() {
  const id = useLocation().pathname.split('/').pop();
  return (
    <div className="page-content">
      <span className="eyebrow">Estimates › Detail</span>
      <h1 style={{ marginTop: 4 }}>{id}</h1>
      <p style={{ color: 'var(--muted)', fontSize: 13 }}>Full immutable estimate snapshot</p>
      <div className="panel" style={{ marginTop: 16 }}>
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--muted-2)', fontSize: 13 }}>
          Estimate detail view — module costs, calculation traces and input snapshot will display here.
        </div>
      </div>
    </div>
  );
}

function CustomerDetail() {
  const id = useLocation().pathname.split('/').pop();
  return (
    <div className="page-content">
      <span className="eyebrow">Customers › Profile</span>
      <h1 style={{ marginTop: 4 }}>Customer Profile</h1>
      <div className="panel" style={{ marginTop: 16 }}>
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--muted-2)', fontSize: 13 }}>
          Customer {id} — history, contacts and estimate list.
        </div>
      </div>
    </div>
  );
}

// ── Root App ─────────────────────────────────────────────────
// AuthProvider wraps everything so Login can call login() and
// protected routes can call isLoggedIn — both need BrowserRouter
// context from main.jsx.
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* ── Public ── */}
        <Route path="/"      element={<PublicLayout><Home /></PublicLayout>} />
        <Route path="/login" element={<PublicLayout><Login /></PublicLayout>} />

        {/* ── Protected app pages ── */}
        <Route path="/dashboard"     element={<AppPage><Dashboard /></AppPage>} />
        <Route path="/estimator/*"   element={<AppPage><CostEstimator /></AppPage>} />
        <Route path="/estimates"     element={<AppPage><Estimates /></AppPage>} />
        <Route path="/estimates/:id" element={<AppPage><EstimateDetail /></AppPage>} />
        <Route path="/customers"     element={<AppPage><Customers /></AppPage>} />
        <Route path="/customers/:id" element={<AppPage><CustomerDetail /></AppPage>} />
        <Route path="/reports"       element={<AppPage><Reports /></AppPage>} />
        <Route path="/master-config" element={<AppPage><MasterConfig /></AppPage>} />
        <Route path="/quotations"    element={<AppPage><Quotations /></AppPage>} />
        <Route path="/proforma"      element={<AppPage><Proforma /></AppPage>} />
        <Route path="/settings"      element={<AppPage><Settings /></AppPage>} />
        <Route path="/users"         element={<AppPage><Users /></AppPage>} />
        <Route path="/audit-log"     element={<AppPage><AuditLog /></AppPage>} />

        {/* ── Catch-all ── */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
